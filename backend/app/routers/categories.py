from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("")
def list_categories(db: Session = Depends(get_db)):
    categories = db.query(models.Category).filter_by(active=True).all()
    return [
        {"id": c.id, "name": c.name, "slug": c.slug}
        for c in categories
    ]
