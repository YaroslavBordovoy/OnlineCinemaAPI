import requests


class MailgunService:
    def __init__(self, api_key: str, domain: str):
        self.api_key = api_key
        self.domain = domain
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}/messages"

    def send_email(self, to: str, subject: str, text: str, html: str = None):
        data = {
            "from": f"Support <support@{self.domain}>",
            "to": to,
            "subject": subject,
            "text": text,
        }

        if html:
            data["html"] = html

        response = requests.post(
            self.base_url,
            auth=("api", self.api_key),
            data=data
        )

        if response.status_code != 200:
            raise Exception(f"Error sending email: {response.json()}")

        return response.json()
