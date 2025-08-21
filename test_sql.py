import sqlite3

print("🔍 Подключаюсь к БД...")

conn = sqlite3.connect("server/db/database.db")
cursor = conn.cursor()

print("🔎 Выполняю SQL-запрос...")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("📋 Таблицы:", tables)
