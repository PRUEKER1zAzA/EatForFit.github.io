import sqlite3

def get_db():
    conn = sqlite3.connect("EatForFit.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    connect = get_db()
    c = connect.cursor()

    try:
        c.execute("""
            CREATE TABLE IF NOT EXISTS data_test (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gender TEXT,
            age INTEGER,
            weight REAL,
            height REAL,
            activity TEXT,
            bodyfat REAL,
            bmr REAL,
            tdee REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS guest_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            gender TEXT,
            age INTEGER,
            weight REAL,
            height REAL,
            activity TEXT,
            bodyfat REAL,
            picture TEXT DEFAULT '/img/users_profile/default_profile.png',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        c.execute("""
            CREATE TABLE google_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            picture TEXT,
            gender TEXT,
            age INTEGER,
            weight REAL,
            height REAL,
            activity TEXT,
            bodyfat REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        c.execute("""
            CREATE TABLE user_calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            bmr REAL,
            tdee REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        c.execute("""
            CREATE TABLE food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_type TEXT NOT NULL,
            food_name TEXT NOT NULL,
            calories REAL NOT NULL,
            carb REAL DEFAULT 0,
            protein REAL DEFAULT 0,
            fat REAL DEFAULT 0,
            log_date DATE DEFAULT CURRENT_DATE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        c.execute("""   
            CREATE TABLE workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            type TEXT,
            description TEXT
        );
        """)

        c.execute("""   
            CREATE TABLE base_food (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT NOT NULL,
            category TEXT,
            base_cal REAL NOT NULL,
            base_carb REAL DEFAULT 0,
            base_protein REAL DEFAULT 0,
            base_fat REAL DEFAULT 0,
            fiber REAL DEFAULT 0,
            sugar REAL DEFAULT 0,
            sodium REAL DEFAULT 0,
            unit TEXT DEFAULT '100g',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        connect.commit()
        print("OK")
    except sqlite3.Error as er:
        print(f"Error: {er}")
    finally:
        connect.close()

if __name__ == "__main__":
    init_db()