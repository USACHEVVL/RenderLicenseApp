import sqlite3
import os

# Абсолютный путь к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "database.db")


def check_license(license_key: str) -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Проверим, существует ли лицензия с таким ключом
        cursor.execute("SELECT id FROM license WHERE key = ?", (license_key,))
        license_row = cursor.fetchone()

        if not license_row:
            return False, "❌ Лицензия не найдена"

        return True, "✅ Лицензия найдена"

    except Exception as e:
        return False, f"⚠️ Ошибка при проверке: {str(e)}"
    finally:
        conn.close()
