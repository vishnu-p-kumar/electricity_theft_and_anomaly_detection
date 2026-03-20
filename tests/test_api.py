from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from api import main as api_main


async def _idle_loop() -> None:
    while True:
        await asyncio.sleep(60)


def test_health_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(api_main.runtime, "bootstrap", lambda: None)
    monkeypatch.setattr(api_main.runtime, "simulation_loop", _idle_loop)
    monkeypatch.setattr(
        api_main.runtime,
        "health_payload",
        lambda: {
            "status": "ok",
            "timestamp": "2026-03-12T18:00:00",
            "current_tick": None,
            "websocket_clients": 0,
            "artifacts": {"dataset": False},
        },
    )

    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
