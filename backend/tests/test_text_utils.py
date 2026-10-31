import pytest

import re
import unicodedata

from app.data.countries import COUNTRIES
from app.data.culture_questions import CULTURE_QUESTIONS
from app.data.sport_questions import SPORT_QUESTIONS
from app.data.tech_questions import TECH_QUESTIONS
from app.text_utils import (
    ANSWER_ALIASES,
    accepted_answers,
    hint_letters,
    is_correct_answer,
    normalize_answer,
)


@pytest.mark.parametrize("submitted,expected", [
    ("etats unis", "États-Unis"),
    ("ÉTATS-UNIS", "États-Unis"),
    ("  france  ", "France"),
    ("appstore", "App Store"),
    ("pays bas", "Pays-Bas"),
    ("coeur", "Cœur"),
    ("ADN", "ADN (acide désoxyribonucléique)"),
    ("adn (acide désoxyribonucléique)", "ADN (acide désoxyribonucléique)"),
    ("OMS", "Organisation mondiale de la santé (OMS)"),
    ("organisation mondiale de la sante", "Organisation mondiale de la santé (OMS)"),
    ("cote d'ivoire", "Côte d'Ivoire"),
    ("cote divoire", "Côte d'Ivoire"),
    ("c++", "C++"),
    # article initial facultatif (réponse attendue ou réponse du joueur)
    ("sahara", "Le Sahara"),
    ("coeur", "Le cœur"),
    ("le caire", "Le Caire"),
    ("caire", "Le Caire"),
    ("fang", "Les Fang"),
    ("ogooue", "L'Ogooué"),
    ("l'ogooue", "L'Ogooué"),
    ("le senegal", "Sénégal"),
    ("panthères", "Les Panthères"),
    # abréviations et variantes
    ("usa", "États-Unis"),
    ("U.S.A.", "États-Unis"),
    ("US", "États-Unis"),
    ("uk", "Royaume-Uni"),
    ("RDC", "RD Congo"),
    ("republique democratique du congo", "RD Congo"),
    ("EAU", "Émirats Arabes Unis"),
    ("cfa", "Franc CFA"),
    ("cpu", "Processeur"),
    ("Hz", "Hertz"),
    ("go", "Gigaoctet"),
    ("js", "JavaScript"),
    ("ml", "Machine learning"),
    ("hollande", "Pays-Bas"),
])
def test_accepts_equivalent_answers(submitted, expected):
    assert is_correct_answer(submitted, expected)


@pytest.mark.parametrize("submitted,expected", [
    ("", "France"),
    ("   ", "France"),
    ("!!!", "France"),
    ("islande", "Irlande"),  # pas de tolérance de fautes : une lettre change le pays
    ("zambie", "Gambie"),
    ("c", "C++"),
    ("c#", "C++"),
    ("richter", "L'échelle de Richter (magnitude)"),
    ("le", "France"),
    ("l'", "France"),
    ("congo", "RD Congo"),  # deux pays distincts
    ("rdc", "Congo"),
    ("us", "Suède"),
    ("usb", "Universal Serial Bus"),  # le sigle est dans la question : pas d'alias
    ("ia", "Intelligence artificielle"),
    ("llm", "Large Language Model"),
])
def test_rejects_different_answers(submitted, expected):
    assert not is_correct_answer(submitted, expected)


def test_normalize_is_idempotent():
    once = normalize_answer("Côte d'Ivoire")
    assert normalize_answer(once) == once


def test_hint_skips_leading_article():
    assert hint_letters("Le cœur") == "CŒ"
    assert hint_letters("L'Ogooué") == "OG"
    assert hint_letters("Les Fang") == "FA"
    assert hint_letters("  France ") == "FR"
    assert hint_letters("Le") == "LE"


# --- Garde-fous sur les données : protègent les futures questions et alias ---
def _all_questions():
    flags = [(f"Quel est ce pays ? (drapeau {name})", name) for name, _code, _d in COUNTRIES]
    mixed = [(q[0], q[1]) for q in SPORT_QUESTIONS + CULTURE_QUESTIONS + TECH_QUESTIONS]
    return flags + mixed


def _words(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9+#]+", text))


def test_every_seeded_answer_accepts_itself_unaccented_and_uppercase():
    for prompt, answer in _all_questions():
        assert is_correct_answer(answer, answer)
        assert is_correct_answer(answer.upper(), answer)
        stripped = "".join(
            c for c in unicodedata.normalize("NFD", answer) if not unicodedata.combining(c)
        )
        assert is_correct_answer(stripped.lower(), answer)


def test_question_text_is_never_a_valid_answer():
    """Aucun alias ne doit figurer dans l'énoncé (sinon on gagne en recopiant la question)."""
    for prompt, answer in _all_questions():
        if prompt.startswith("Quel est ce pays ? (drapeau"):
            continue  # libellé interne des drapeaux, non affiché
        assert not is_correct_answer(prompt, answer), prompt
        alias_words = {
            normalize_answer(a) for a in ANSWER_ALIASES.get(answer, [])
        }
        assert not (alias_words & {normalize_answer(w) for w in _words(prompt)}), (prompt, answer)


def test_distinct_answers_never_share_an_accepted_form():
    # « Nigéria » (géographie) et « Nigeria » (sport) : même réponse écrite deux
    # fois, on les regroupe par forme normalisée.
    answers = sorted({answer for _prompt, answer in _all_questions()})
    seen = {}
    for answer in answers:
        owner = normalize_answer(answer)
        for form in accepted_answers(answer):
            assert form not in seen or seen[form] == owner, (form, answer, seen.get(form))
            seen[form] = owner
