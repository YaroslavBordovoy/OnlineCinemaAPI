from fastapi import APIRouter, Depends, status

from schemas.accounts import UserRegistrationRequestSchema, UserRegistrationResponseSchema
from sqlalchemy.orm import Session
from database import get_db
from services.user_service import create_user


router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED
)
def register(user_data: UserRegistrationRequestSchema, db: Session = Depends(get_db)):
    return create_user(user_data=user_data, db=db)
