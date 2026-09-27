import os
import psycopg2

def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Render internal URL uses postgres://, psycopg2 needs postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432")
    )

def init_database():
    """Safe init - won't crash if already exists"""
    conn = None
    cur = None
    try:
        print("🔧 init_database() called - trying to create tables...")
        conn = get_connection()
        cur = conn.cursor()
        
        # Create tables one by one - safe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                full_name VARCHAR(200),
                phone VARCHAR(20) UNIQUE,
                email VARCHAR(200),
                password_hash TEXT,
                role VARCHAR(20),
                preferred_language VARCHAR(20) DEFAULT 'Hindi',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS job_categories (
                category_id SERIAL PRIMARY KEY,
                category_name VARCHAR(100) UNIQUE,
                hindi_name VARCHAR(100)
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employers (
                employer_id SERIAL PRIMARY KEY,
                user_id INT,
                business_name VARCHAR(200),
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id SERIAL PRIMARY KEY,
                employer_id INT,
                category_id INT,
                job_title VARCHAR(200),
                job_description TEXT,
                location VARCHAR(200),
                city VARCHAR(100),
                area VARCHAR(100),
                pincode VARCHAR(10),
                salary VARCHAR(100),
                contact VARCHAR(20),
                status VARCHAR(20) DEFAULT 'approved',
                posted_at TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS simple_jobs (
                job_id SERIAL PRIMARY KEY,
                job_title VARCHAR(200),
                company VARCHAR(200),
                location VARCHAR(200),
                city VARCHAR(100),
                salary VARCHAR(100),
                contact VARCHAR(20),
                job_description TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                application_id SERIAL PRIMARY KEY,
                job_id INT,
                worker_name VARCHAR(100),
                worker_phone VARCHAR(20),
                worker_city VARCHAR(100),
                applied_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Insert categories safely - ignore if exists
        cur.execute("SELECT COUNT(*) FROM job_categories")
        count = cur.fetchone()[0]
        if count == 0:
            cur.execute("""
                INSERT INTO job_categories (category_name, hindi_name) VALUES
                ('Helper','हेल्पर'),('Driver','ड्राइवर'),('Cook','कुक'),
                ('Guard','गार्ड'),('Delivery','डिलीवरी'),('Electrician','इलेक्ट्रीशियन'),
                ('Plumber','प्लंबर'),('Cleaning','सफाई'),('Mason','मिस्त्री'),('Tailor','टेलर');
            """)
            print(f"Inserted {cur.rowcount} categories")
        
        conn.commit()
        print("✅ Database tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error in init_database: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
