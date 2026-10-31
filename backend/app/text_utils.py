"""Comparaison des réponses : partagée par le mode solo et le multijoueur.

Règles (volontairement sans tolérance de fautes de frappe : en géographie,
« Irlande »/« Islande » ou « Zambie »/« Gambie » ne diffèrent que d'une lettre) :
  - casse, accents, espaces, tirets et ponctuation sont ignorés
    (« Etats Unis » = « États-Unis », « appstore » = « App Store ») ;
  - « œ » / « æ » sont développés (« coeur » = « cœur ») ;
  - l'article initial est facultatif, dans la réponse attendue comme dans celle
    du joueur (« Sahara » = « Le Sahara », « le senegal » = « Sénégal ») ;
  - le texte entre parenthèses est facultatif : « ADN (acide
    désoxyribonucléique) » accepte « ADN » ;
  - un sigle entre parenthèses est accepté seul : « Organisation mondiale
    de la santé (OMS) » accepte « OMS » ;
  - les abréviations et variantes usuelles listées dans ANSWER_ALIASES sont
    acceptées (« USA » = « États-Unis », « RDC » = « RD Congo »).
"""
import re
import unicodedata

# On garde « + » et « # » pour ne pas confondre « C++ » et « C# » avec « C ».
_NON_ALNUM_RE = re.compile(r"[^a-z0-9+#]+")
_PARENTHESES_RE = re.compile(r"\(([^)]*)\)")
_LEADING_ARTICLE_RE = re.compile(r"^\s*(?:l['’]\s*|(?:le|la|les|un|une|the)\s+)", re.IGNORECASE)
_MAX_ACRONYM_LEN = 6

# Abréviations et variantes acceptées, par réponse attendue (telle qu'écrite dans
# app/data). La clé est comparée sans casse, accents ni ponctuation.
#
# ATTENTION : n'ajouter AUCUN alias qui figure dans l'énoncé de la question.
# Ex. « Que signifie le sigle USB ? » (réponse « Universal Serial Bus ») : l'alias
# « USB » ferait gagner le joueur en recopiant la question. Pour la même raison,
# pas d'alias « IA » ni « LLM » pour les questions « Que signifie le sigle… ».
ANSWER_ALIASES: dict[str, list[str]] = {
    # Pays
    "États-Unis": ["USA", "US", "États-Unis d'Amérique"],
    "Royaume-Uni": ["UK", "Grande-Bretagne"],
    "Émirats Arabes Unis": ["EAU", "UAE"],
    "RD Congo": ["RDC", "République démocratique du Congo", "Congo Kinshasa"],
    "Congo": ["République du Congo", "Congo Brazzaville"],
    "Arabie Saoudite": ["KSA"],
    "Nouvelle-Zélande": ["NZ"],
    "Pays-Bas": ["Hollande"],
    "République Tchèque": ["Tchéquie"],
    "Myanmar": ["Birmanie"],
    "Eswatini": ["Swaziland"],
    "Cap-Vert": ["Cabo Verde"],
    "Timor Oriental": ["Timor-Leste"],
    "Macédoine du Nord": ["Macédoine"],
    "Papouasie-Nouvelle-Guinée": ["PNG"],
    "Bosnie-Herzégovine": ["Bosnie"],
    "Biélorussie": ["Belarus", "Bélarus"],
    "Palaos": ["Palau"],
    "Îles Salomon": ["Salomon"],
    # Culture générale
    "Franc CFA": ["CFA"],
    # Technologie
    "Processeur": ["CPU"],
    "Gigaoctet": ["Go", "GB"],
    "Hertz": ["Hz"],
    "JavaScript": ["JS"],
    "Machine learning": ["ML", "Apprentissage automatique"],
}


def normalize_answer(text: str) -> str:
    """Forme canonique d'une réponse : minuscules, sans accents ni séparateurs."""
    text = (text or "").strip().lower()
    text = text.replace("œ", "oe").replace("æ", "ae")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _NON_ALNUM_RE.sub("", text)


def strip_leading_article(text: str) -> str:
    """Retire l'article initial (« Le Caire » -> « Caire »). Texte inchangé s'il n'en reste rien."""
    stripped = _LEADING_ARTICLE_RE.sub("", text or "", count=1).strip()
    return stripped or (text or "")


_ALIASES_BY_ANSWER = {normalize_answer(k): tuple(v) for k, v in ANSWER_ALIASES.items()}


def accepted_answers(expected: str) -> set[str]:
    """Toutes les formes normalisées acceptées pour la réponse attendue."""
    without_parentheses = _PARENTHESES_RE.sub(" ", expected)

    forms: set[str] = set()
    base_keys: set[str] = set()
    for base in (expected, without_parentheses):
        for variant in (base, strip_leading_article(base)):
            normalized = normalize_answer(variant)
            if normalized:
                forms.add(normalized)
                base_keys.add(normalized)

    for inner in _PARENTHESES_RE.findall(expected):
        inner = inner.strip()
        if 2 <= len(inner) <= _MAX_ACRONYM_LEN and inner.isupper():
            forms.add(normalize_answer(inner))

    for key in base_keys:
        for alias in _ALIASES_BY_ANSWER.get(key, ()):
            forms.add(normalize_answer(alias))

    forms.discard("")
    return forms


def is_correct_answer(submitted: str, expected: str) -> bool:
    candidates = {
        normalize_answer(submitted),
        normalize_answer(strip_leading_article(submitted)),
    }
    candidates.discard("")
    return not candidates.isdisjoint(accepted_answers(expected))


def hint_letters(answer: str, count: int = 2) -> str:
    """Premières lettres affichées par le joker « indice », sans l'article initial :
    pour « Le cœur », l'indice « LE » n'aiderait pas, « CŒ » oui."""
    return strip_leading_article((answer or "").strip())[:count].upper()
