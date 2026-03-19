import sqlite3

def check():
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    
    print("--- Tables ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(cursor.fetchall())
    
    print("\n--- Last 5 Bot Logs ---")
    try:
        cursor.execute("SELECT * FROM bot_logs ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error reading bot_logs: {e}")
        
    conn.close()

if __name__ == "__main__":
    check()
