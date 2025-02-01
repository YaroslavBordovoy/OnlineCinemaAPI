from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.models.accounts import UserModel, UserGroupModel, UserGroupEnum, ActivationTokenModel
from schemas.accounts import UserRegistrationRequestSchema


def create_user(user_data: UserRegistrationRequestSchema, db: Session) -> UserModel:
    user = db.query(UserModel).filter_by(email=user_data.email).first()

    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists."
        )

    user_group = db.query(UserGroupModel).filter_by(name=UserGroupEnum.USER).first()

    if not user_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User group not found."
        )

    try:
        new_user = UserModel.create(
            email=user_data.email,
            raw_password=user_data.password,
            group_id=user_group.id,
        )
        db.add(new_user)
        db.flush()

        activation_token = ActivationTokenModel(user_id=new_user.id)
        db.add(activation_token)
        db.commit()
        db.refresh(new_user)

        return new_user
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation.",
        )
