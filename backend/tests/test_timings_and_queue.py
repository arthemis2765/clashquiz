import asyncio
import time

from app.websocket.manager import (
    EXTRA_TIME_BONUS_SECONDS,
    MATCHMAKING_FALLBACK_SECONDS,
    TURN_DURATION_SECONDS,
    ConnectionManager,
    QueuedPlayer,
)


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_json(self, data):
        self.sent.append(data)


def test_turn_and_joker_durations():
    assert TURN_DURATION_SECONDS == 15
    assert EXTRA_TIME_BONUS_SECONDS == 10


def test_queue_update_sends_seconds_left_computed_on_server_clock():
    """Le client ne doit jamais comparer un timestamp serveur à sa propre horloge
    (PC décalé d'une heure => « duel va commencer 3737 s ») : le serveur envoie
    directement la durée restante."""
    manager = ConnectionManager()
    first = FakeWebSocket()
    manager.queues["geo"] = [
        QueuedPlayer("p1", "A", "geo", 1, first),
        QueuedPlayer("p2", "B", "geo", 1, FakeWebSocket()),
    ]
    manager.queue_fallback_started_at["geo"] = time.time() - 3  # 3 s déjà écoulées

    asyncio.run(manager._broadcast_queue_state("geo"))

    payload = first.sent[0]["payload"]
    assert payload["waiting"] == 2
    assert MATCHMAKING_FALLBACK_SECONDS - 4 <= payload["seconds_left"] <= MATCHMAKING_FALLBACK_SECONDS - 3
    assert payload["deadline"] is not None  # conservé pour compatibilité


def test_queue_update_without_timer_has_no_seconds_left():
    manager = ConnectionManager()
    alone = FakeWebSocket()
    manager.queues["geo"] = [QueuedPlayer("p1", "A", "geo", 1, alone)]

    asyncio.run(manager._broadcast_queue_state("geo"))

    payload = alone.sent[0]["payload"]
    assert payload["seconds_left"] is None and payload["deadline"] is None
