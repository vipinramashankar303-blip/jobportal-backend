
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import get_connection
import os
from datetime import datetime

app = FastAPI(title="SimpleJobs Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Backend running - Apply to DB ready"}

# 1. APPLY KO POSTGRESQL ME SAVE KARNA
class ApplyRequest(BaseModel):
    job_id: int
    worker_name: str = "Guest"
    worker_phone: str
    worker_city: str = ""

@app.post("/apply")
def apply_job(data: ApplyRequest):
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Table banao agar nahi hai
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id SERIAL PRIMARY KEY,
                job_id INT,
                worker_name VARCHAR(100),
                worker_phone VARCHAR(20),
                worker_city VARCHAR(100),
                applied_at TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute(
            "INSERT INTO applications (job_id, worker_name, worker_phone, worker_city) VALUES (%s,%s,%s,%s) RETURNING id",
            (data.job_id, data.worker_name, data.worker_phone, data.worker_city)
        )
        app_id = cur.fetchone()[0]
        conn.commit()
        return {"message": "Applied successfully - Saved in PostgreSQL", "application_id": app_id}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

# 2. SAARE APPLICATIONS DEKHNE KE LIYE (Admin ke liye)
@app.get("/applications")
def get_applications():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, job_id, worker_name, worker_phone, worker_city, applied_at FROM applications ORDER BY applied_at DESC LIMIT 100")
        rows = cur.fetchall()
        return [{"id": r[0], "job_id": r[1], "worker_name": r[2], "worker_phone": r[3], "worker_city": r[4], "applied_at": str(r[5])} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()

# 3. TERA PURANA JOBS WALA CODE (same rahega)
@app.get("/jobs")
def get_jobs():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT job_id, job_title, location, city FROM jobs WHERE status='approved' ORDER BY posted_at DESC LIMIT 50")
        rows = cur.fetchall()
        # Agar jobs table khali hai to dummy bhejo
        if not rows:
            return [
                {"job_id": 1, "job_title": "Helper - Delhi", "location": "Delhi", "salary": "₹12000", "contact": "9876543210", "company": "Sharma Co"},
                {"job_id": 2, "job_title": "Driver - Mumbai", "location": "Mumbai", "salary": "₹18000", "contact": "9876543211", "company": "Mumbai Trans"}
            ]
        return [{"job_id": r[0], "job_title": r[1], "location": r[2], "city": r[3]} for r in rows]
    except Exception as e:
        return [{"job_id": 1, "job_title": "Helper - Delhi", "location": "Delhi", "salary": "₹12000"}]
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.get("/health")
def health():
    return {"status": "OK", "db": "PostgreSQL - Apply Ready"}
