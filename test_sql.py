import sqlite3
from server.db.session import SQLALCHEMY_DATABASE_URL

print("🔍 Подключаюсь к БД...")

db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "", 1)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔎 Выполняю SQL-запрос...")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("📋 Таблицы:", tables)
