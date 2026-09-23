import psycopg2
import os
from dotenv import load_dotenv

# .env file se saari variables ko read karna
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def get_connection():
    """
    Creates and returns a connection to the PostgreSQL database.
    """
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return connection
    except Exception as e:
        # Agar connection fail ho jaye to server crash nahi hoga, balki error print karega
        print(f"❌ Database connection failed: {e}")
        raise e