import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_FILE = "engagement.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            student_count INTEGER,
            cei_score REAL
        )
    ''')
    conn.commit()
    conn.close()

def log_engagement(student_count, cei_score):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO session_logs (timestamp, student_count, cei_score) VALUES (?, ?, ?)",
        (timestamp, student_count, cei_score)
    )
    conn.commit()
    conn.close()

def get_recent_data(minutes=5):
    conn = sqlite3.connect(DB_FILE)
    time_threshold = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    
    query = "SELECT timestamp, student_count, cei_score FROM session_logs WHERE timestamp >= ? ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn, params=(time_threshold,))
    conn.close()
    
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def get_all_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM session_logs ORDER BY timestamp ASC", conn)
    conn.close()
    return df
