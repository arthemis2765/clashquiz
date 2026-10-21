import uuid


def post(client, path, auth, **extra):
    return client.post(f"/api/solo/{path}", json={**auth, **extra})


# --------------------------------------------------------------------------
# Déroulement de base
# --------------------------------------------------------------------------
def test_start_returns_first_question_without_answer(solo, make_player):
    game = solo(make_player("Alice"))
    assert game.question["number"] == 1
    assert game.question["difficulty"] == 1
    assert "answer" not in game.question
    assert game.state["lives"] == 3 and game.state["score"] == 0


def test_correct_answer_scores_and_advances(solo, make_player):
    game = solo(make_player("Alice"))
    res = game.right()
    body = res.json()
    assert res.status_code == 200
    assert body["result"] == "correct"
    assert body["state"]["score"] == 1
    assert body["question"]["number"] == 2


def test_wrong_answer_costs_a_life_and_three_lives_end_the_run(solo, make_player):
    game = solo(make_player("Alice"))
    game.right()
    for _ in range(2):
        assert game.wrong().json()["state"]["lives"] >= 1
    last = game.wrong().json()
    assert last["finished"] is True
    assert last["state"]["score"] == 1
    assert last["state"]["new_record"] is True
    assert last["question"] is None


def test_blank_answer_at_deadline_is_a_timeout_not_a_wrong_answer(solo, make_player):
    game = solo(make_player("Alice"))
    game.expire()
    body = game.answer("").json()
    assert body["result"] == "timeout"
    assert body["state"]["lives"] == 2


def test_late_typed_answer_is_a_timeout(solo, make_player):
    game = solo(make_player("Alice"))
    correct = game.current_answer()
    game.expire()
    body = game.answer(correct).json()
    assert body["result"] == "timeout"
    assert body["state"]["score"] == 0


def test_accents_and_case_are_ignored(solo, make_player):
    game = solo(make_player("Alice"))
    assert game.answer(game.current_answer().upper()).json()["result"] == "correct"


# --------------------------------------------------------------------------
# Requêtes rejouées / resynchronisation
# --------------------------------------------------------------------------
def test_replayed_answer_is_refused_and_costs_nothing(client, solo, make_player):
    game = solo(make_player("Alice"))
    first_number = game.question["number"]
    assert game.right().status_code == 200
    lives_before = game.state["lives"]

    replay = game.answer("n'importe quoi", number=first_number)
    assert replay.status_code == 409
    assert replay.json()["detail"]["code"] == "stale_question"

    current = post(client, "current", game.auth, run_id=game.run_id).json()
    assert current["state"]["lives"] == lives_before
    assert current["question"]["number"] == first_number + 1


def test_future_question_number_is_refused(solo, make_player):
    game = solo(make_player("Alice"))
    res = game.answer("x", number=game.question["number"] + 5)
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "stale_question"


def test_replay_after_the_run_ended_resyncs_to_the_summary(client, solo, make_player):
    game = solo(make_player("Alice"))
    for _ in range(3):
        game.wrong()
    assert game.state["lives"] == 0
    replay = game.answer("x", number=1)
    assert replay.status_code == 409 and replay.json()["detail"]["code"] == "stale_question"
    current = post(client, "current", game.auth, run_id=game.run_id).json()
    assert current["finished"] is True and current["state"]["score"] == 0


def test_missing_question_number_is_rejected(client, solo, make_player):
    game = solo(make_player("Alice"))
    res = post(client, "answer", game.auth, run_id=game.run_id, answer="x")
    assert res.status_code == 422


# --------------------------------------------------------------------------
# Jokers
# --------------------------------------------------------------------------
def test_hint_gives_two_letters_and_can_only_be_used_once(client, solo, make_player):
    game = solo(make_player("Alice"))
    res = post(client, "joker", game.auth, run_id=game.run_id, joker_type="hint")
    assert res.status_code == 200
    assert res.json()["hint"] == game.current_answer()[:2].upper()
    again = post(client, "joker", game.auth, run_id=game.run_id, joker_type="hint")
    assert again.status_code == 409


def test_skip_keeps_lives_and_score_but_changes_question(client, solo, make_player):
    game = solo(make_player("Alice"))
    res = post(client, "joker", game.auth, run_id=game.run_id, joker_type="skip").json()
    assert res["finished"] is False
    assert res["state"]["lives"] == 3 and res["state"]["score"] == 0
    assert res["question"]["number"] == 2


def test_extra_time_adds_ten_seconds(client, solo, make_player):
    game = solo(make_player("Alice"))
    base = game.question["seconds_left"]
    res = post(client, "joker", game.auth, run_id=game.run_id, joker_type="extra_time").json()
    assert res["bonus_seconds"] == 10
    assert base + 9 < res["seconds_left"] <= base + 10


def test_unknown_joker_is_rejected(client, solo, make_player):
    game = solo(make_player("Alice"))
    res = post(client, "joker", game.auth, run_id=game.run_id, joker_type="cheat")
    assert res.status_code == 400


# --------------------------------------------------------------------------
# Sécurité
# --------------------------------------------------------------------------
def test_wrong_token_is_rejected(client, make_player):
    auth = make_player("Alice")
    res = post(client, "start", {**auth, "device_token": "faux"}, category_slug="geo")
    assert res.status_code == 401


def test_cannot_play_someone_elses_run(client, solo, make_player):
    alice = solo(make_player("Alice"))
    mallory = make_player("Mallory")
    res = post(client, "answer", mallory, run_id=alice.run_id, question_number=1, answer="x")
    assert res.status_code == 404
    res = post(client, "abandon", mallory, run_id=alice.run_id)
    assert res.status_code == 404


def test_unknown_category_and_malformed_ids(client, make_player):
    auth = make_player("Alice")
    assert post(client, "start", auth, category_slug="nope").status_code == 404
    bad = post(client, "answer", auth, run_id="pas-un-uuid", question_number=1, answer="x")
    assert bad.status_code == 404


def test_start_is_rate_limited(client, make_player):
    auth = make_player("Alice")
    codes = [post(client, "start", auth, category_slug="geo").status_code for _ in range(31)]
    assert codes[:30] == [200] * 30
    assert codes[30] == 429


def test_oversized_fields_are_rejected(client, make_player):
    auth = make_player("Alice")
    res = post(client, "start", {**auth, "device_token": "x" * 500}, category_slug="geo")
    assert res.status_code == 422


# --------------------------------------------------------------------------
# Abandon et parties multiples
# --------------------------------------------------------------------------
def test_abandon_records_the_score_and_is_idempotent(client, solo, make_player):
    auth = make_player("Alice")
    game = solo(auth)
    game.right()
    game.right()
    first = post(client, "abandon", auth, run_id=game.run_id).json()
    assert first["finished"] and first["state"]["score"] == 2 and first["state"]["new_record"]
    second = post(client, "abandon", auth, run_id=game.run_id)
    assert second.status_code == 200 and second.json()["state"]["score"] == 2

    board = client.get("/api/solo/leaderboard", params={"category_slug": "geo"}).json()
    assert [(e["pseudo"], e["score"]) for e in board["entries"]] == [("Alice", 2)]


def test_starting_a_new_run_closes_the_previous_one(client, solo, make_player):
    auth = make_player("Alice")
    first = solo(auth)
    first.right()
    second = solo(auth)
    res = first.answer("x")
    assert res.status_code == 409
    assert second.state["record"] == 1  # le score de la partie abandonnée compte


def test_record_is_tracked_per_category(client, solo, make_player):
    auth = make_player("Alice")
    game = solo(auth, "geo")
    game.right()
    post(client, "abandon", auth, run_id=game.run_id)
    other = solo(auth, "tech")
    assert other.state["record"] == 0


# --------------------------------------------------------------------------
# Classement
# --------------------------------------------------------------------------
def play(solo, post_fn, auth, category, good):
    game = solo(auth, category)
    for _ in range(good):
        game.right()
    post_fn(auth, game.run_id)


def test_leaderboard_per_category_global_and_me(client, solo, make_player):
    def abandon(auth, run_id):
        post(client, "abandon", auth, run_id=run_id)

    alice, bob, carol = make_player("Alice"), make_player("Bob"), make_player("Carol")
    play(solo, abandon, alice, "geo", 3)
    play(solo, abandon, alice, "tech", 2)
    play(solo, abandon, bob, "geo", 5)
    play(solo, abandon, carol, "geo", 3)  # ex æquo avec Alice en géo

    geo = client.get("/api/solo/leaderboard", params={"category_slug": "geo", "player_id": alice["player_id"]}).json()
    assert [(e["rank"], e["pseudo"], e["score"]) for e in geo["entries"]] == [
        (1, "Bob", 5), (2, "Alice", 3), (2, "Carol", 3),
    ]
    assert [e["is_me"] for e in geo["entries"]] == [False, True, False]
    assert geo["me"] == {"rank": 2, "score": 3}

    tech = client.get("/api/solo/leaderboard", params={"category_slug": "tech"}).json()
    assert [(e["pseudo"], e["score"]) for e in tech["entries"]] == [("Alice", 2)]
    assert tech["me"] is None

    overall = client.get("/api/solo/leaderboard", params={"player_id": alice["player_id"]}).json()
    assert [(e["rank"], e["pseudo"], e["score"], e["themes"]) for e in overall["entries"]] == [
        (1, "Alice", 5, 2), (1, "Bob", 5, 1), (3, "Carol", 3, 1),
    ]
    assert overall["me"] == {"rank": 1, "score": 5}


def test_leaderboard_hides_ids_ignores_zero_scores_and_validates_input(client, solo, make_player):
    alice = make_player("Alice")
    game = solo(alice)  # score 0 : ne doit pas apparaître
    board = client.get("/api/solo/leaderboard").json()
    assert board["entries"] == []

    game.right()
    post(client, "abandon", alice, run_id=game.run_id)
    entry = client.get("/api/solo/leaderboard").json()["entries"][0]
    assert set(entry) == {"rank", "pseudo", "score", "themes", "is_me"}

    assert client.get("/api/solo/leaderboard", params={"category_slug": "nope"}).status_code == 404
    assert client.get("/api/solo/leaderboard", params={"limit": 0}).status_code == 422
    assert client.get("/api/solo/leaderboard", params={"limit": 101}).status_code == 422
    ok = client.get("/api/solo/leaderboard", params={"player_id": "pas-un-uuid"})
    assert ok.status_code == 200 and ok.json()["me"] is None


def test_leaderboard_ignores_deactivated_categories(client, solo, make_player):
    from app import models
    from app.database import SessionLocal

    alice = make_player("Alice")
    game = solo(alice, "geo")
    game.right()
    post(client, "abandon", alice, run_id=game.run_id)

    db = SessionLocal()
    try:
        db.query(models.Category).filter_by(slug="geo").update({"active": False})
        db.commit()
    finally:
        db.close()
    assert client.get("/api/solo/leaderboard").json()["entries"] == []
    assert client.get("/api/solo/leaderboard", params={"category_slug": "geo"}).status_code == 404


def test_run_uuid_helper_sanity():
    assert uuid.UUID(str(uuid.uuid4()))
