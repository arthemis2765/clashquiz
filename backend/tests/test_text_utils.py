import pytest

from app.text_utils import is_correct_answer, normalize_answer


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
])
def test_rejects_different_answers(submitted, expected):
    assert not is_correct_answer(submitted, expected)


def test_normalize_is_idempotent():
    once = normalize_answer("Côte d'Ivoire")
    assert normalize_answer(once) == once
