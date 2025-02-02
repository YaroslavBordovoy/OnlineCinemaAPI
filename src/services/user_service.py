from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    RefreshTokenModel,
    PasswordResetTokenModel,
)
from schemas.accounts import (
    UserRegistrationRequestSchema,
    UserActivationTokenRequestSchema,
    LoginRequestSchema, LoginResponseSchema, PasswordResetRequestSchema, MessageResponseSchema,
)
from security.jwt_interface import JWTAuthManagerInterface


def create_user(user_data: UserRegistrationRequestSchema, db: Session) -> UserModel | HTTPException:
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


def activate_user(user_data: UserActivationTokenRequestSchema, db: Session) -> MessageResponseSchema | HTTPException:
    user = db.query(UserModel).filter_by(email=user_data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user with email {user_data.email} was found.",
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )

    activation_token = db.query(ActivationTokenModel).filter_by(token=user_data.token).first()

    if (not activation_token or
            activation_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token."
        )

    try:
        user.is_active = True
        db.delete(activation_token)
        db.commit()

        return MessageResponseSchema(message="User account activated successfully.")
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during account activation.",
        )


def login_user(
        user_data: LoginRequestSchema,
        db: Session,
        jwt_auth_manager: JWTAuthManagerInterface,
) -> LoginResponseSchema:
    user = db.query(UserModel).filter_by(email=user_data.email).first()

    if not user or not user.verify_password(raw_password=user_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated."
        )

    try:
        access_token = jwt_auth_manager.create_access_token({"user_id": user.id})
        refresh_token = jwt_auth_manager.create_refresh_token({"user_id": user.id})
        db_refresh_token = RefreshTokenModel(user_id=user.id, token=refresh_token)
        db.add(db_refresh_token)
        db.commit()

        return LoginResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login.",
        )


def password_reset_request(user_data: PasswordResetRequestSchema, db: Session) -> MessageResponseSchema:
    user = db.query(UserModel).filter_by(email=user_data.email).first()

    if not user or not user.is_active:
        return MessageResponseSchema(message="If you are registered, you will receive an email with instructions.")

    db.query(PasswordResetTokenModel).filter_by(user_id=user.id).delete()

    try:
        new_reset_token = PasswordResetTokenModel(user_id=user.id)
        db.add(new_reset_token)
        db.commit()

        return MessageResponseSchema(message="If you are registered, you will receive an email with instructions.")
    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during request reset the password.",
        )


