"""Matchs de bout en bout par WebSocket (vrai serveur FastAPI, base SQLite jetable).

On rejoue de vraies parties : création/rejoindre une partie privée, file publique
à 3 joueurs, repli en duel à 2 joueurs, tours, jokers, éliminations par timeout,
fin de match et écriture en base. Les joueurs répondent avec des variantes
tolérées (« usa », « sahara », « cfa »...) pour prouver que le duel applique les
mêmes règles que le solo.

Les délais du serveur sont raccourcis (tour de 0,4 s au lieu de 15 s, etc.).
"""
import queue
import threading
import time

import pytest
from starlette.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from app.websocket import game as game_mod
from app.websocket import manager as manager_mod

# (énoncé, réponse enregistrée en base, variante tolérée tapée par les joueurs)
QUESTIONS = [
    ("Quelle est la monnaie utilisée au Gabon ?", "Franc CFA", "cfa"),
    ("Quel composant est considéré comme le « cerveau » de l'ordinateur ?", "Processeur", "LE PROCESSEUR"),
    ("Quelle unité mesure la fréquence d'un processeur (en GHz) ?", "Hertz", "hz"),
    ("Que signifie le sigle USB ? (en anglais)", "Universal Serial Bus", "universal-serial-bus"),
    ("Quel pays a pour capitale Washington D.C. ?", "États-Unis", "usa"),
    ("Quel est le plus grand désert chaud du monde ?", "Le Sahara", "sahara"),
    ("Quel organe pompe le sang dans le corps ?", "Le cœur", "coeur"),
]
TOLERANT = {prompt: variant for prompt, _answer, variant in QUESTIONS}
ANSWER_OF = {prompt: answer for prompt, answer, _variant in QUESTIONS}
USB_PROMPT = QUESTIONS[3][0]
HEART_PROMPT = QUESTIONS[6][0]
CATEGORY = "tolerance"


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def fast_server(monkeypatch):
    monkeypatch.setattr(game_mod, "TURN_DURATION_SECONDS", 0.4)
    monkeypatch.setattr(game_mod, "ANSWER_ATTEMPT_COOLDOWN_SECONDS", 0.0)
    monkeypatch.setattr(manager_mod, "MATCHMAKING_GRACE_SECONDS", 0.3)
    monkeypatch.setattr(manager_mod, "MATCHMAKING_FALLBACK_SECONDS", 0.4)
    _reset_manager()
    yield
    _reset_manager()


def _reset_manager():
    m = manager_mod.manager
    for task in list(getattr(m, "private_expiry_tasks", {}).values()):
        try:
            task.cancel()
        except RuntimeError:  # la boucle d'événements du test précédent est déjà fermée
            pass
    for name in ("queues", "pending_groups", "private_matches", "matches", "player_to_match",
                 "queue_fallback_timers", "queue_fallback_started_at",
                 "private_suspended", "private_expiry_tasks", "finished_results"):
        container = getattr(m, name, None)
        if hasattr(container, "clear"):
            container.clear()


@pytest.fixture(autouse=True)
def seed_category(fresh_database):
    db = SessionLocal()
    try:
        category = models.Category(name="Tolérance", slug=CATEGORY, active=True)
        db.add(category)
        db.flush()
        for prompt, answer, _variant in QUESTIONS:
            db.add(models.Question(
                category_id=category.id, prompt_label=prompt, answer=answer,
                hint_type=models.HintType.text, difficulty=2,
            ))
        db.commit()
    finally:
        db.close()
    manager_mod.question_cache.invalidate()


# --------------------------------------------------------------------------
# Petit pilote de joueurs WebSocket
# --------------------------------------------------------------------------
class Gamer:
    def __init__(self, name, ws, auth):
        self.name, self.ws, self.auth = name, ws, auth
        self.id = auth["player_id"]
        self.inbox = queue.Queue()
        self.events = []  # (event, payload) dans l'ordre de réception
        self.prompt = None
        self.end = None
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        try:
            while True:
                self.inbox.put(self.ws.receive_json())
        except Exception:
            self.inbox.put({"event": "__closed__", "payload": {}})

    def send(self, event, **fields):
        self.ws.send_json({"event": event, **fields})

    def payloads(self, event):
        return [p for e, p in self.events if e == event]

    def wait_for(self, event, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self.inbox.get(timeout=0.05)
            except queue.Empty:
                continue
            self.events.append((msg["event"], msg["payload"]))
            if msg["event"] == event:
                return msg["payload"]
        raise AssertionError(f"{self.name} : événement « {event} » jamais reçu ; reçus : {[e for e, _ in self.events]}")


def play(gamers, policy, timeout=20):
    """Fait jouer tous les joueurs jusqu'au `match_end`.

    policy(gamer, prompt) -> liste d'actions : ("answer", texte) ou ("joker", type).
    Elle est appelée à chaque tour du joueur ; liste vide = ne rien envoyer (timeout).
    """
    deadline = time.time() + timeout
    while any(g.end is None for g in gamers):
        if time.time() > deadline:
            raise AssertionError("Match non terminé à temps. Derniers événements : " + str(
                {g.name: [e for e, _ in g.events][-6:] for g in gamers}))
        for g in gamers:
            try:
                msg = g.inbox.get(timeout=0.02)
            except queue.Empty:
                continue
            event, payload = msg["event"], msg["payload"]
            g.events.append((event, payload))
            if event == "round_start":
                g.prompt = payload["prompt_label"]
            elif event == "turn_start" and payload["is_your_turn"]:
                for kind, value in policy(g, g.prompt):
                    if kind == "answer":
                        g.send("submit_answer", answer=value)
                    else:
                        g.send("use_joker", joker_type=value)
            elif event == "match_end":
                g.end = payload
            elif event == "error":
                assert not payload.get("fatal"), payload


def answer_tolerantly(gamer, prompt):
    return [("answer", TOLERANT[prompt])]


def stay_silent(gamer, prompt):
    return []


@pytest.fixture()
def server():
    with TestClient(app) as client:
        yield client


def register(client, pseudo):
    res = client.post("/api/players/register", json={"pseudo": pseudo})
    assert res.status_code == 200, res.text
    data = res.json()
    return {"player_id": data["id"], "device_token": data["device_token"]}


class Connections:
    """Ouvre un WebSocket par joueur et les ferme à la fin."""

    def __init__(self, client, pseudos):
        self.client, self.pseudos = client, pseudos

    def __enter__(self):
        self._contexts, gamers = [], []
        for pseudo in self.pseudos:
            ctx = self.client.websocket_connect("/ws/game")
            ws = ctx.__enter__()
            self._contexts.append(ctx)
            gamers.append(Gamer(pseudo, ws, register(self.client, pseudo)))
        return gamers

    def __exit__(self, *exc):
        for ctx in reversed(self._contexts):
            try:
                ctx.__exit__(None, None, None)
            except Exception:
                pass


def start_private_match(alice, bob):
    alice.send("create_private_match", category_slug=CATEGORY, **alice.auth)
    code = alice.wait_for("private_match_created")["code"]
    bob.send("join_private_match", code=code, **bob.auth)
    return code


# --------------------------------------------------------------------------
# Scénarios
# --------------------------------------------------------------------------
def test_private_duel_full_match_with_tolerant_answers(server):
    """Duel privé de bout en bout : toutes les manches sont gagnées avec des variantes tolérées."""
    with Connections(server, ["Alice", "Bob"]) as (alice, bob):
        start_private_match(alice, bob)
        play([alice, bob], answer_tolerantly)

    end = alice.end
    assert len(alice.payloads("match_found")) == 1 and len(bob.payloads("match_found")) == 1
    assert end["scores"] == {alice.id: len(QUESTIONS), bob.id: len(QUESTIONS)}
    assert end["lives"] == {alice.id: 3, bob.id: 3}  # personne n'a perdu de vie
    assert end["winner_id"] is None  # égalité parfaite

    log = end["rounds_log"]
    assert len(log) == len(QUESTIONS)
    for entry in log:
        for pid in (alice.id, bob.id):
            recap = entry["players"][pid]
            assert recap["status"] == "correct", entry
            assert recap["submitted"] == TOLERANT[entry["prompt_label"]]
        assert entry["correct_answer"] == ANSWER_OF[entry["prompt_label"]]
    assert alice.payloads("wrong_answer") == [] and bob.payloads("wrong_answer") == []
    assert bob.end == end


def test_private_duel_winner_by_elimination_and_database(server):
    """Bob ne répond jamais : il perd ses 3 vies par timeout, Alice gagne et la base est mise à jour."""
    with Connections(server, ["Alice", "Bob"]) as (alice, bob):
        start_private_match(alice, bob)

        def policy(gamer, prompt):
            return answer_tolerantly(gamer, prompt) if gamer is alice else stay_silent(gamer, prompt)

        play([alice, bob], policy)

    end = alice.end
    assert end["winner_id"] == alice.id
    assert end["lives"][bob.id] == 0 and end["lives"][alice.id] == 3
    assert end["scores"][alice.id] == 3 and end["scores"][bob.id] == 0
    assert len(bob.payloads("turn_timeout")) == 3

    db = SessionLocal()
    try:
        import uuid
        winner = db.get(models.Player, uuid.UUID(alice.id))
        loser = db.get(models.Player, uuid.UUID(bob.id))
        assert winner.elo_score > 0 and loser.elo_score == 0
        match = db.query(models.Match).one()
        assert match.status == models.MatchStatus.finished
        assert str(match.winner_id) == alice.id
        assert db.query(models.MatchParticipant).filter_by(match_id=match.id).count() == 2
    finally:
        db.close()


def test_duel_refuses_sigle_from_question_then_accepts_full_answer_and_hint_skips_article(server):
    """« usb » est refusé (le sigle est dans l'énoncé), « universal-serial-bus » accepté ;
    l'indice de « Le cœur » ne commence pas par l'article."""
    with Connections(server, ["Alice", "Bob"]) as (alice, bob):
        start_private_match(alice, bob)

        def policy(gamer, prompt):
            if gamer is alice and prompt == USB_PROMPT:
                return [("answer", "usb"), ("answer", "Universal-Serial-Bus")]
            if gamer is alice and prompt == HEART_PROMPT:
                return [("joker", "hint"), ("answer", "COEUR")]
            return answer_tolerantly(gamer, prompt)

        play([alice, bob], policy)

    wrong = alice.payloads("wrong_answer")
    assert [w["submitted"] for w in wrong] == ["usb"]
    assert [h["hint"] for h in alice.payloads("joker_hint")] == ["CŒ"]
    by_prompt = {e["prompt_label"]: e for e in alice.end["rounds_log"]}
    assert by_prompt[USB_PROMPT]["players"][alice.id]["status"] == "correct"
    assert by_prompt[HEART_PROMPT]["players"][alice.id]["status"] == "correct"
    assert alice.end["scores"][alice.id] == len(QUESTIONS)


def test_public_matchmaking_group_of_three(server):
    """File publique : 3 joueurs sont réunis, la partie démarre et ils jouent tous avec des variantes tolérées."""
    with Connections(server, ["Alice", "Bob", "Chloé"]) as gamers:
        for g in gamers:
            g.send("join_queue", category_slug=CATEGORY, **g.auth)
            g.wait_for("queue_joined")
        play(gamers, answer_tolerantly)

    for g in gamers:
        found = g.payloads("match_found")
        assert len(found) == 1 and len(found[0]["opponents"]) == 2
        assert g.end["scores"] == {x.id: len(QUESTIONS) for x in gamers}
        assert g.end["lives"] == {x.id: 3 for x in gamers}
    assert gamers[0].end["rounds_log"][0]["players"].keys() == {x.id for x in gamers}


def test_public_matchmaking_falls_back_to_a_duel_with_two_players(server):
    """Deux joueurs seuls en file : le repli lance un duel, avec les mêmes règles de réponse."""
    with Connections(server, ["Alice", "Bob"]) as (alice, bob):
        for g in (alice, bob):
            g.send("join_queue", category_slug=CATEGORY, **g.auth)
            g.wait_for("queue_joined")
        play([alice, bob], answer_tolerantly, timeout=25)

    assert len(alice.payloads("match_found")[0]["opponents"]) == 1
    assert alice.end["scores"] == {alice.id: len(QUESTIONS), bob.id: len(QUESTIONS)}
    assert alice.payloads("wrong_answer") == []


# --------------------------------------------------------------------------
# Partie privée : le créateur quitte l'appli pour partager son code
# --------------------------------------------------------------------------
def wait_until(condition, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return
        time.sleep(0.02)
    raise AssertionError("condition jamais remplie à temps")


def create_code_then_drop_socket(alice):
    """Alice crée sa partie puis perd sa connexion (appli passée en arrière-plan)."""
    alice.send("create_private_match", category_slug=CATEGORY, **alice.auth)
    code = alice.wait_for("private_match_created")["code"]
    alice.ws.close()
    wait_until(lambda: code in manager_mod.manager.private_suspended)
    return code


def test_private_code_survives_host_leaving_and_returning(server):
    """Régression : partager son code obligeait à quitter l'appli, ce qui détruisait le code."""
    with Connections(server, ["Alice", "Bob"]) as (alice, bob):
        code = create_code_then_drop_socket(alice)

        # Bob arrive pendant l'absence d'Alice : refus NON fatal, le code reste valable.
        bob.send("join_private_match", code=code, **bob.auth)
        error = bob.wait_for("error")
        assert error.get("fatal") is False
        assert code in manager_mod.manager.private_matches

        # Alice revient avec un nouveau socket et reprend sa partie en attente.
        with server.websocket_connect("/ws/game") as ws2:
            alice2 = Gamer("Alice", ws2, alice.auth)
            alice2.send("resume_private_match", code=code, **alice2.auth)
            assert alice2.wait_for("private_match_created")["code"] == code

            bob.send("join_private_match", code=code, **bob.auth)
            alice2.wait_for("match_found")
            bob.wait_for("match_found")
            play([alice2, bob], answer_tolerantly)

        assert alice2.end is not None and bob.end is not None


def test_private_code_expires_when_host_never_returns(server, monkeypatch):
    monkeypatch.setattr(manager_mod, "PRIVATE_RECONNECT_GRACE_SECONDS", 0.3)
    with Connections(server, ["Alice", "Bob"]) as (alice, bob):
        code = create_code_then_drop_socket(alice)
        wait_until(lambda: code not in manager_mod.manager.private_matches)

        bob.send("join_private_match", code=code, **bob.auth)
        assert "n'existe pas" in bob.wait_for("error")["message"]

        with server.websocket_connect("/ws/game") as ws2:
            alice2 = Gamer("Alice", ws2, alice.auth)
            alice2.send("resume_private_match", code=code, **alice2.auth)
            assert "expiré" in alice2.wait_for("error")["message"]


def test_cancel_private_match_removes_code_immediately(server):
    with Connections(server, ["Alice"]) as (alice,):
        alice.send("create_private_match", category_slug=CATEGORY, **alice.auth)
        code = alice.wait_for("private_match_created")["code"]
        alice.send("cancel_private_match")
        wait_until(lambda: code not in manager_mod.manager.private_matches)
        assert code not in manager_mod.manager.private_suspended


def test_bad_token_cannot_borrow_another_players_identity(server):
    """Un faux token ne doit pas lier l'identité d'Alice au socket de Mallory
    (sinon Mallory pouvait annuler la partie d'Alice ou l'éliminer en se déconnectant)."""
    with Connections(server, ["Alice", "Mallory"]) as (alice, mallory):
        alice.send("create_private_match", category_slug=CATEGORY, **alice.auth)
        code = alice.wait_for("private_match_created")["code"]

        mallory.send("join_queue", player_id=alice.id, device_token="faux-token",
                     category_slug=CATEGORY, pseudo="Mallory")
        mallory.wait_for("error")
        mallory.send("cancel_private_match")
        mallory.ws.close()
        time.sleep(0.3)

        assert code in manager_mod.manager.private_matches
        assert code not in manager_mod.manager.private_suspended


# --------------------------------------------------------------------------
# Reprise en pleine partie : une coupure de connexion n'élimine plus personne
# --------------------------------------------------------------------------
def start_match_and_reach_first_turn(alice, bob):
    start_private_match(alice, bob)
    alice.wait_for("turn_start")
    bob.wait_for("turn_start")


def test_disconnect_in_match_keeps_player_and_resume_restores_state(server):
    with Connections(server, ["Alice", "Bob"]) as (alice, bob):
        start_match_and_reach_first_turn(alice, bob)
        alice.ws.close()

        notice = bob.wait_for("player_disconnected")
        assert notice == {"player_id": alice.id, "temporary": True}
        match = manager_mod.manager.get_match(alice.id)
        assert match is not None and match.lives[alice.id] == 3  # personne n'est éliminé

        with server.websocket_connect("/ws/game") as ws2:
            alice2 = Gamer("Alice", ws2, alice.auth)
            alice2.send("resume_session", **alice2.auth)
            assert alice2.wait_for("match_found")["resumed"] is True
            alice2.wait_for("round_start")
            assert alice2.wait_for("turn_start")["timer_seconds"] > 0
            assert bob.wait_for("player_reconnected") == {"player_id": alice.id}

            # `play` retient la question à partir des événements round_start qu'elle lit
            # elle-même ; ceux de la 1re manche ont déjà été consommés plus haut.
            for gamer in (alice2, bob):
                gamer.prompt = gamer.payloads("round_start")[-1]["prompt_label"]
            play([alice2, bob], answer_tolerantly)
        assert alice2.end is not None and bob.end is not None


def test_leave_match_eliminates_immediately(server):
    with Connections(server, ["Alice", "Bob"]) as (alice, bob):
        start_match_and_reach_first_turn(alice, bob)
        bob.send("leave_match")
        assert alice.wait_for("match_end")["winner_id"] == alice.id


def test_result_is_kept_for_a_player_who_was_away_at_the_end(server):
    with Connections(server, ["Alice", "Bob"]) as (alice, bob):
        start_match_and_reach_first_turn(alice, bob)
        alice.ws.close()
        bob.wait_for("player_disconnected")
        bob.send("leave_match")  # Alice gagne pendant qu'elle est absente
        wait_until(lambda: alice.id in manager_mod.manager.finished_results)

        with server.websocket_connect("/ws/game") as ws2:
            alice2 = Gamer("Alice", ws2, alice.auth)
            alice2.send("resume_session", **alice2.auth)
            assert alice2.wait_for("match_end")["winner_id"] == alice.id


def test_resume_with_nothing_to_resume_answers_resume_none(server):
    with Connections(server, ["Alice"]) as (alice,):
        alice.send("resume_session", **alice.auth)
        alice.wait_for("resume_none")
        alice.send("ping")
        alice.wait_for("pong")
