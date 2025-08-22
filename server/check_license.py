import sqlite3
import os

# Абсолютный путь к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "database.db")


def check_license(license_key: str, machine_name: str) -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Проверим, существует ли лицензия с таким ключом
        cursor.execute("SELECT id FROM license WHERE key = ?", (license_key,))
        license_row = cursor.fetchone()

        if not license_row:
            return False, "❌ Лицензия не найдена"

        license_id = license_row[0]

        # Проверим, привязана ли к этой лицензии нужная машина
        cursor.execute("""
            SELECT name FROM machine 
            WHERE license_id = ? AND name = ?
        """, (license_id, machine_name))

        machine_row = cursor.fetchone()

        if not machine_row:
            return False, "❌ Машина не привязана к лицензии"

        return True, "✅ Лицензия и машина совпадают"

    except Exception as e:
        return False, f"⚠️ Ошибка при проверке: {str(e)}"
    finally:
        conn.close()
