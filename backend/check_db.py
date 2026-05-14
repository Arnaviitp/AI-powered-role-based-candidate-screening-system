
import sqlite3
import os

db_path = "screening.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, candidate_name, role, created_at FROM sessions ORDER BY created_at DESC LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    conn.close()
else:
    print("Database not found")
