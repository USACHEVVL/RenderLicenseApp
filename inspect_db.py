import sqlite3
from server.db.session import DATABASE_URL

db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "", 1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Таблицы в базе данных:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

for table in tables:
    print(f"\n=== {table[0]} ===")
    cursor.execute(f"PRAGMA table_info({table[0]});")
    columns = cursor.fetchall()
    for col in columns:
        print(f"{col[1]} ({col[2]})")

conn.close()
