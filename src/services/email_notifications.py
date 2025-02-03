from database.models.accounts import UserModel
from fastapi import BackgroundTasks

from mail_service.mail_service import SMTPService


def register_notification(
        user: UserModel,
        bg: BackgroundTasks,
        email_sender: SMTPService,
) -> None:

    activation_link = f"http://127.0.0.1/api/v1/accounts/activate/?token={user.activation_token.token}"

    bg.add_task(
        email_sender.send_email,
        to_email=user.email,
        subject="Registration",
        body=f"Click the link to activate your account: {activation_link}",
    )

    print(f"📩 Email sending task added for {user.email}")
