"""
Script de seed de la base de données.

Crée les tables si besoin, puis insère les catégories et les questions
(drapeaux pour Géographie, football pour Sport, mix pour Culture générale)
si elles n'existent pas déjà.

Usage :
    python -m app.seed
"""
from app.database import Base, engine, SessionLocal
from app import models
from app.data.countries import COUNTRIES, flag_url
from app.data.sport_questions import SPORT_QUESTIONS
from app.data.culture_questions import CULTURE_QUESTIONS
from app.data.cuisine_questions import CUISINE_QUESTIONS

CATEGORIES = [
    {"name": "Géographie", "slug": "geographie"},
    {"name": "Sport", "slug": "sport"},
    {"name": "Culture générale", "slug": "culture-generale"},
    {"name": "Cuisine & Gastronomie", "slug": "cuisine-gastronomie"},
]

# Catégories retirées : on les désactive (active=False) plutôt que de les
# supprimer, pour ne pas casser l'historique des matchs déjà joués dessus.
DEPRECATED_CATEGORY_SLUGS = ["mode-beaute"]


def get_or_create_category(db, name: str, slug: str) -> models.Category:
    category = db.query(models.Category).filter_by(slug=slug).first()
    if category:
        return category
    category = models.Category(name=name, slug=slug, active=True)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def seed_flag_questions(db, category: models.Category):
    existing_answers = {
        row.answer
        for row in db.query(models.Question.answer).filter_by(
            category_id=category.id, hint_type=models.HintType.flag
        )
    }

    created = 0
    for name, code, difficulty in COUNTRIES:
        if name in existing_answers:
            continue
        question = models.Question(
            category_id=category.id,
            prompt_label=f"Quel est ce pays ? (drapeau {name})",
            answer=name,
            hint_type=models.HintType.flag,
            hint_url=flag_url(code),
            difficulty=difficulty,
        )
        db.add(question)
        created += 1

    db.commit()
    return created


def seed_mixed_questions(db, category: models.Category, questions: list):
    """Insère des questions au format (prompt_label, answer, hint_type, hint_code, difficulty).
    hint_type="flag" -> hint_code est un code pays (transformé en URL de drapeau).
    hint_type="text" -> hint_code est ignoré (pas d'image, la question suffit)."""
    existing_prompts = {
        row.prompt_label
        for row in db.query(models.Question.prompt_label).filter_by(category_id=category.id)
    }

    created = 0
    for prompt_label, answer, hint_type, hint_code, difficulty in questions:
        if prompt_label in existing_prompts:
            continue
        hint_url = flag_url(hint_code) if hint_type == "flag" and hint_code else None
        question = models.Question(
            category_id=category.id,
            prompt_label=prompt_label,
            answer=answer,
            hint_type=models.HintType(hint_type),
            hint_url=hint_url,
            difficulty=difficulty,
        )
        db.add(question)
        created += 1

    db.commit()
    return created


def deactivate_categories(db, slugs: list):
    count = 0
    for slug in slugs:
        category = db.query(models.Category).filter_by(slug=slug).first()
        if category and category.active:
            category.active = False
            count += 1
    db.commit()
    return count


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        categories = {
            c["slug"]: get_or_create_category(db, c["name"], c["slug"])
            for c in CATEGORIES
        }
        created_geo = seed_flag_questions(db, categories["geographie"])
        created_sport = seed_mixed_questions(db, categories["sport"], SPORT_QUESTIONS)
        created_culture = seed_mixed_questions(db, categories["culture-generale"], CULTURE_QUESTIONS)
        created_cuisine = seed_mixed_questions(db, categories["cuisine-gastronomie"], CUISINE_QUESTIONS)
        deactivated = deactivate_categories(db, DEPRECATED_CATEGORY_SLUGS)

        print(f"Seed terminé. Géographie : {created_geo} nouvelles questions drapeau. "
              f"Sport : {created_sport} nouvelles questions. "
              f"Culture générale : {created_culture} nouvelles questions. "
              f"Cuisine & Gastronomie : {created_cuisine} nouvelles questions. "
              f"Catégories désactivées : {deactivated}.")
    finally:
        db.close()


if __name__ == "__main__":
    run()

