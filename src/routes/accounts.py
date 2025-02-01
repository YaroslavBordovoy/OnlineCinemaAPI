from fastapi import APIRouter, Depends, status

from schemas.accounts import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    UserActivationTokenRequestSchema,
)
from sqlalchemy.orm import Session
from database import get_db
from services.user_service import create_user, activate_user


router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="Register a new user",
    description="Register a new user with an email and password.",
    responses={
        409: {
            "description": "Conflict - User with this email already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A user with this email test@example.com already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred during user creation.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred during user creation."
                    }
                }
            },
        },
    },
    status_code=status.HTTP_201_CREATED
)
def register(user_data: UserRegistrationRequestSchema, db: Session = Depends(get_db)):
    return create_user(user_data=user_data, db=db)


@router.post("/activate/", status_code=status.HTTP_200_OK)
def activate(user_data: UserActivationTokenRequestSchema, db: Session = Depends(get_db)):
    return activate_user(user_data=user_data, db=db)
