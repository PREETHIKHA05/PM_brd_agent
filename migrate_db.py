
import sqlite3
import os

DB_PATH = "pm_agent.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Starting database migration...")
    
    try:
        
        cursor.execute("PRAGMA table_info(brds)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print("Adding user_id column to brds table...")
            cursor.execute("ALTER TABLE brds ADD COLUMN user_id INTEGER")
            print("Added user_id column")
        else:
            print("user_id column already exists")
        
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_reviews (
                id INTEGER PRIMARY KEY,
                brd_id INTEGER NOT NULL,
                original_brd TEXT NOT NULL,
                suggestions TEXT,
                updated_brd TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (brd_id) REFERENCES brds(id)
            )
        """)
        print("Created/verified risk_reviews table")
        
        
        cursor.execute("PRAGMA table_info(runs)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'risk_review_id' not in columns:
            print("Adding risk_review_id column to runs table...")
            cursor.execute("ALTER TABLE runs ADD COLUMN risk_review_id INTEGER")
            print("Added risk_review_id column")
        else:
            print("risk_review_id column already exists")
        
        conn.commit()
        print("\n Migration completed successfully!")
        
    except Exception as e:
        print(f" Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        migrate()
    else:
        print(f"Database {DB_PATH} not found. It will be created when you run the app.")
