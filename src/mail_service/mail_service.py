import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class SMTPService:
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, from_name: str, use_tls: bool = True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_name = from_name
        self.use_tls = use_tls

    def send_email(self, to_email: str, subject: str, body: str):
        msg = MIMEMultipart()
        msg["From"] = f"{self.from_name} <{self.username}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.username, to_email, msg.as_string())
                print(f"Email sent to {to_email}")

        except smtplib.SMTPException as e:
            raise RuntimeError(f"Failed to send email: {str(e)}")
