from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import smtplib
from email.message import EmailMessage
from typing import Any

import pandas as pd
import requests

from login import ensure_users_file

TELEGRAM_ALERT_COOLDOWN = timedelta(seconds=30)
_telegram_last_sent_at: dict[str, datetime] = {}
_telegram_last_message: dict[str, str] = {}
POLE_TAMPER_ALERT_THRESHOLD = 0.7


def _validate_telegram_response(response: requests.Response) -> None:
    response.raise_for_status()
    payload = response.json()
    if payload.get("ok", False):
        return
    description = str(payload.get("description") or "Telegram API rejected the message.")
    raise RuntimeError(description)


def _send_telegram_text(chat_id: str, text: str, *, token: str | None = None) -> None:
    active_token = str(token or os.getenv("SMARTGRID_TELEGRAM_BOT_TOKEN") or "").strip()
    if not active_token:
        raise RuntimeError("SMARTGRID_TELEGRAM_BOT_TOKEN is not configured in the running API process.")
    clean_chat_id = str(chat_id or "").strip()
    clean_text = str(text or "").strip()
    if not clean_chat_id:
        raise RuntimeError("Telegram chat ID is missing for the target recipient.")
    if not clean_text:
        raise RuntimeError("Telegram message text cannot be empty.")
    response = requests.post(
        f"https://api.telegram.org/bot{active_token}/sendMessage",
        json={"chat_id": clean_chat_id, "text": clean_text},
        timeout=10,
    )
    _validate_telegram_response(response)


def build_alert_messages(dataframe: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if dataframe.empty:
        return []
    theft_frame = dataframe.loc[dataframe.get("status", pd.Series(index=dataframe.index, dtype=object)) == "Electricity Theft"].copy()
    pole_frame = dataframe.loc[
        pd.to_numeric(dataframe.get("tamper_probability", 0.0), errors="coerce").fillna(0.0) > POLE_TAMPER_ALERT_THRESHOLD
    ].copy()
    combined = pd.concat([theft_frame, pole_frame], ignore_index=True, sort=False).drop_duplicates().reset_index(drop=True)
    if combined.empty:
        return []
    sort_columns = [column for column in ["risk_score", "theft_probability", "tamper_probability"] if column in combined.columns]
    ranked = combined.sort_values(sort_columns, ascending=False) if sort_columns else combined.copy()
    if limit is not None:
        ranked = ranked.head(limit)
    alerts: list[dict[str, Any]] = []
    for _, row in ranked.iterrows():
        if pd.notna(row.get("tamper_probability")) and float(row.get("tamper_probability") or 0.0) > 0.0 and str(row.get("status") or "").strip() != "Electricity Theft":
            alerts.append(
                {
                    "title": "Pole Tamper Detected",
                    "category": "Pole Tamper",
                    "area": row.get("area"),
                    "tamper_probability": round(float(row.get("tamper_probability", 0.0)), 4),
                    "message": (
                        f"Pole Tamper | Area: {row.get('area')} | "
                        f"Pole: {row.get('pole_id') or '-'} | "
                        f"Tamper probability: {float(row.get('tamper_probability', 0.0)):.4f}"
                    ),
                }
            )
            continue
        alerts.append(
            {
                "title": "Electricity Theft Detected",
                "category": "Electricity Theft",
                "area": row.get("area"),
                "risk_score": round(float(row.get("risk_score", 0.0)), 2),
                "theft_probability": round(float(row.get("theft_probability", 0.0)), 4),
                "message": (
                    f"Electricity Theft | Area: {row.get('area')} | "
                    f"Risk score: {float(row.get('risk_score', 0.0)):.2f} | "
                    f"Theft probability: {float(row.get('theft_probability', 0.0)):.4f}"
                ),
            }
        )
    return alerts


def _send_email(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    host = os.getenv("SMARTGRID_SMTP_HOST")
    username = os.getenv("SMARTGRID_SMTP_USER")
    password = os.getenv("SMARTGRID_SMTP_PASSWORD")
    sender = os.getenv("SMARTGRID_ALERT_EMAIL_FROM")
    recipient = os.getenv("SMARTGRID_ALERT_EMAIL_TO")
    port = int(os.getenv("SMARTGRID_SMTP_PORT", "587"))
    if not all([host, username, password, sender, recipient]):
        return {"provider": "email", "status": "skipped"}

    message = EmailMessage()
    message["Subject"] = "Smart Grid Alert"
    message["From"] = sender
    message["To"] = recipient
    message.set_content("\n".join(alert["message"] for alert in alerts))

    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)
    return {"provider": "email", "status": "sent", "count": len(alerts)}


def _send_slack(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    webhook = os.getenv("SMARTGRID_SLACK_WEBHOOK")
    if not webhook:
        return {"provider": "slack", "status": "skipped"}
    payload = {"text": "\n".join(alert["message"] for alert in alerts)}
    response = requests.post(webhook, json=payload, timeout=10)
    response.raise_for_status()
    return {"provider": "slack", "status": "sent", "count": len(alerts)}


def _send_telegram(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    token = os.getenv("SMARTGRID_TELEGRAM_BOT_TOKEN")
    if not token:
        return {
            "provider": "telegram",
            "status": "skipped",
            "detail": "SMARTGRID_TELEGRAM_BOT_TOKEN is not configured in the running API process.",
        }

    users_payload = ensure_users_file()
    inspectors = users_payload.get("inspectors", [])
    fallback_chat_id = str(os.getenv("SMARTGRID_TELEGRAM_CHAT_ID") or "").strip()
    delivered = 0
    recipients = 0
    throttled = 0
    now = datetime.now(timezone.utc)
    messages_by_chat: dict[str, list[str]] = {}
    chat_recipient_labels: dict[str, str] = {}
    message_by_inspector: dict[str, str] = {}

    def _queue_message(chat_id: str, text: str, *, recipient_label: str) -> None:
        clean_chat_id = str(chat_id or "").strip()
        clean_text = str(text or "").strip()
        if not clean_chat_id or not clean_text:
            return
        messages = messages_by_chat.setdefault(clean_chat_id, [])
        if clean_text not in messages:
            messages.append(clean_text)
        chat_recipient_labels.setdefault(clean_chat_id, recipient_label)

    for inspector in inspectors:
        inspector_key = str(inspector.get("username") or inspector.get("id") or inspector.get("chat_id") or "").strip().lower()
        assigned_area = str(inspector.get("assigned_area") or "").strip()
        chat_id = str(inspector.get("chat_id") or "").strip()
        if not inspector_key or not assigned_area or not chat_id:
            continue
        scoped_alerts = [
            alert
            for alert in alerts
            if str(alert.get("area") or "").strip().lower() == assigned_area.lower()
        ]
        if not scoped_alerts:
            continue
        message = "\n".join(str(alert.get("message") or "") for alert in scoped_alerts if str(alert.get("message") or "").strip())
        if not message:
            continue
        last_sent_at = _telegram_last_sent_at.get(inspector_key)
        last_message = _telegram_last_message.get(inspector_key)
        if last_sent_at is not None and now - last_sent_at < TELEGRAM_ALERT_COOLDOWN and last_message == message:
            throttled += 1
            continue
        _queue_message(chat_id, message, recipient_label=inspector_key)
        message_by_inspector[inspector_key] = message

    if fallback_chat_id:
        for alert in alerts:
            _queue_message(fallback_chat_id, str(alert.get("message") or ""), recipient_label=f"fallback:{fallback_chat_id}")

    if not messages_by_chat:
        if throttled > 0:
            return {
                "provider": "telegram",
                "status": "throttled",
                "recipients": 0,
                "throttled": throttled,
                "detail": "Matching inspector alerts were throttled within the 5 minute cooldown window.",
            }
        return {
            "provider": "telegram",
            "status": "skipped",
            "detail": "No inspector chat_id matched the alert areas, and SMARTGRID_TELEGRAM_CHAT_ID fallback is empty.",
        }

    for chat_id, queued_messages in messages_by_chat.items():
        _send_telegram_text(chat_id, "\n".join(queued_messages), token=token)
        recipients += 1
        delivered += len(queued_messages)

    for inspector_key, message in message_by_inspector.items():
        _telegram_last_sent_at[inspector_key] = now
        _telegram_last_message[inspector_key] = message

    result: dict[str, Any] = {"provider": "telegram", "status": "sent", "count": delivered, "recipients": recipients}
    if throttled > 0:
        result["throttled"] = throttled
    return result


def send_inspector_welcome_message(inspector: dict[str, Any]) -> dict[str, Any]:
    token = str(os.getenv("SMARTGRID_TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        return {
            "provider": "telegram",
            "status": "skipped",
            "detail": "SMARTGRID_TELEGRAM_BOT_TOKEN is not configured in the running API process.",
        }

    chat_id = str(inspector.get("chat_id") or "").strip()
    if not chat_id:
        return {
            "provider": "telegram",
            "status": "skipped",
            "detail": "New inspector record does not include a Telegram chat ID.",
        }

    name = str(inspector.get("name") or inspector.get("username") or "Inspector").strip()
    username = str(inspector.get("username") or "").strip()
    assigned_area = str(inspector.get("assigned_area") or "Unassigned").strip()
    lines = [
        f"Welcome {name}.",
        "Your Smart Grid inspector account has been created successfully.",
        f"Username: {username or '-'}",
        f"Assigned area: {assigned_area}",
        "You will receive field alerts here when activity is detected in your assigned area.",
    ]
    _send_telegram_text(chat_id, "\n".join(lines), token=token)
    return {"provider": "telegram", "status": "sent", "recipients": 1, "count": 1}


def dispatch_alerts(dataframe: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    alerts = build_alert_messages(dataframe, limit=limit)
    if not alerts:
        return []

    results: list[dict[str, Any]] = []
    for sender in (_send_email, _send_slack, _send_telegram):
        try:
            results.append(sender(alerts))
        except Exception as error:
            provider = sender.__name__.replace("_send_", "")
            results.append({"provider": provider, "status": "error", "detail": str(error)})
    return results
