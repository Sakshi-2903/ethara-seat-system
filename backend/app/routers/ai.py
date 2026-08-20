from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas, ai_assistant, auth

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post("/query", response_model=schemas.AIQueryResponse)
def ai_query(
    payload: schemas.AIQueryRequest,
    db: Session = Depends(get_db),
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
):
    result = ai_assistant.answer_query_with_llm(
        db, payload.query, email=payload.email, employee_id=payload.employee_id, current_user=current_user
    )
    return schemas.AIQueryResponse(**result)
