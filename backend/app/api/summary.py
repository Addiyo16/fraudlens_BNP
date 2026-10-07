from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import crud
from app.schemas.schemas import SummaryResponse


router = APIRouter()


@router.get(
    "/summary",
    response_model=SummaryResponse
)
def get_summary(
    db: Session = Depends(get_db),
):
    return crud.get_summary_data(db)