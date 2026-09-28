import os
from pathlib import Path

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DB_PATH", Path(__file__).resolve().parent.parent / "db.sqlite3"),
    }
}
