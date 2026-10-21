"""Comparaison des réponses : partagée par le mode solo et le multijoueur.

Règles (volontairement sans tolérance de fautes de frappe : en géographie,
« Irlande »/« Islande » ou « Zambie »/« Gambie » ne diffèrent que d'une lettre) :
  - casse, accents, espaces, tirets et ponctuation sont ignorés
    (« Etats Unis » = « États-Unis », « appstore » = « App Store ») ;
  - « œ » / « æ » sont développés (« coeur » = « cœur ») ;
  - le texte entre parenthèses est facultatif : « ADN (acide
    désoxyribonucléique) » accepte « ADN » ;
  - un sigle entre parenthèses est accepté seul : « Organisation mondiale
    de la santé (OMS) » accepte « OMS ».
"""
import re
import unicodedata

# On garde « + » et « # » pour ne pas confondre « C++ » et « C# » avec « C ».
_NON_ALNUM_RE = re.compile(r"[^a-z0-9+#]+")
_PARENTHESES_RE = re.compile(r"\(([^)]*)\)")
_MAX_ACRONYM_LEN = 6


def normalize_answer(text: str) -> str:
    """Forme canonique d'une réponse : minuscules, sans accents ni séparateurs."""
    text = (text or "").strip().lower()
    text = text.replace("œ", "oe").replace("æ", "ae")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _NON_ALNUM_RE.sub("", text)


def accepted_answers(expected: str) -> set[str]:
    """Toutes les formes normalisées acceptées pour la réponse attendue."""
    forms = {normalize_answer(expected)}

    without_parentheses = normalize_answer(_PARENTHESES_RE.sub(" ", expected))
    if without_parentheses:
        forms.add(without_parentheses)

    for inner in _PARENTHESES_RE.findall(expected):
        inner = inner.strip()
        if 2 <= len(inner) <= _MAX_ACRONYM_LEN and inner.isupper():
            forms.add(normalize_answer(inner))

    forms.discard("")
    return forms


def is_correct_answer(submitted: str, expected: str) -> bool:
    normalized = normalize_answer(submitted)
    return bool(normalized) and normalized in accepted_answers(expected)
