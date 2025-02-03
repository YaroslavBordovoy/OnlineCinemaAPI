import os

from database.validators import accounts as account_validators

environment = os.getenv("ENVIRONMENT", "developing")

if environment == "testing":
    from database.session_sqlite import get_sqlite_db as get_db
else:
    from database.session_postgresql import get_postgresql_db as get_db
