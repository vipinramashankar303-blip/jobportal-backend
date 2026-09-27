import os
import psycopg2

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432")
    )

def init_database():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                full_name VARCHAR(200),
                phone VARCHAR(20) UNIQUE,
                email VARCHAR(200),
                password_hash TEXT,
                role VARCHAR(20),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS job_categories (
                category_id SERIAL PRIMARY KEY,
                category_name VARCHAR(100),
                hindi_name VARCHAR(100)
            );
            CREATE TABLE IF NOT EXISTS employers (
                employer_id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(user_id),
                business_name VARCHAR(200),
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS jobs (
                job_id SERIAL PRIMARY KEY,
                employer_id INT REFERENCES employers(employer_id),
                category_id INT REFERENCES job_categories(category_id),
                job_title VARCHAR(200),
                job_description TEXT,
                location VARCHAR(200),
                city VARCHAR(100),
                salary VARCHAR(100),
                contact VARCHAR(20),
                status VARCHAR(20) DEFAULT 'approved',
                posted_at TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            );
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
            CREATE TABLE IF NOT EXISTS applications (
                application_id SERIAL PRIMARY KEY,
                job_id INT,
                worker_name VARCHAR(100),
                worker_phone VARCHAR(20),
                worker_city VARCHAR(100),
                applied_at TIMESTAMP DEFAULT NOW()
            );
            INSERT INTO job_categories (category_name, hindi_name) VALUES
            ('Helper','हेल्पर'),('Driver','ड्राइवर'),('Cook','कुक'),('Guard','गार्ड'),
            ('Delivery','डिलीवरी'),('Electrician','इलेक्ट्रीशियन'),('Plumber','प्लंबर'),
            ('Cleaning','सफाई'),('Mason','मिस्त्री'),('Tailor','टेलर')
            ON CONFLICT DO NOTHING;
        """)
        conn.commit()
        print("Tables created!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
