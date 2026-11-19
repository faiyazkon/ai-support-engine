"""Run by hand or by a daily scheduler:  python -m app.database.cleanup
Erases message texts older than RETENTION_DAYS. (The server also does this once each time it starts.)
"""
from app.core.config import get_settings
from app.database.connection import init_db
from app.database.storage import purge_old_texts

if __name__ == "__main__":
    init_db()
    days = get_settings().retention_days
    print(f"Erased the text of {purge_old_texts(days)} messages older than {days} days.")
