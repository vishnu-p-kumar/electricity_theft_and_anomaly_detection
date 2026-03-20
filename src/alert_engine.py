from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any

import pandas as pd
import requests


def build_alert_messages(dataframe: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
    if dataframe.empty:
        return []
    sort_columns = [column for column in ["risk_score", "theft_probability"] if column in dataframe.columns]
    ranked = dataframe.sort_values(sort_columns, ascending=False).head(limit) if sort_columns else dataframe.head(limit)
    alerts: list[dict[str, Any]] = []
    for _, row in ranked.iterrows():
        alerts.append(
            {
                "title": "Electricity Theft Detected" if row.get("status") == "Electricity Theft" else "Smart Grid Risk Alert",
                "meter_id": row.get("meter_id"),
                "area": row.get("area"),
                "risk_score": round(float(row.get("risk_score", 0.0)), 2),
                "message": f"Meter {row.get('meter_id')} in {row.get('area')} scored {float(row.get('risk_score', 0.0)):.1f} with status {row.get('status', 'Unknown')}.",
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
    chat_id = os.getenv("SMARTGRID_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"provider": "telegram", "status": "skipped"}
    message = "\n".join(alert["message"] for alert in alerts)
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=10,
    )
    response.raise_for_status()
    return {"provider": "telegram", "status": "sent", "count": len(alerts)}


def dispatch_alerts(dataframe: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
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
