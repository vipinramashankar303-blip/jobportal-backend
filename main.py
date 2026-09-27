from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import get_connection, init_database
import os
from datetime import datetime
from typing import List, Optional

app = FastAPI(title="SimpleJobs Backend - Rozgar Setu")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        print("🚀 Creating tables...")
        init_database()
        print("✅ Tables ready!")
    except Exception as e:
        print(f"⚠️ DB init warning: {e}")
        pass

# ===== MODELS =====
class JobCreate(BaseModel):
    job_title: str
    company: str = "General Employer"
    location: str
    city: str = "Mumbai"
    area: Optional[str] = None
    salary: str = "15000"
    contact: str
    job_description: Optional[str] = None

class JobResponse(BaseModel):
    job_id: int
    job_title: str
    company: str
    location: str
    city: str
    salary: str
    contact: str
    job_description: Optional[str] = None
    created_at: Optional[str] = None

class ApplicationCreate(BaseModel):
    job_id: int
    worker_name: str
    worker_phone: str
    worker_city: str = "Mumbai"

# ===== ROUTES =====
@app.get("/")
def home():
    return {"message": "Backend running - SimpleJobs Ready", "status": "live", "jobs_endpoint": "/jobs"}

@app.get("/jobs", response_model=List[JobResponse])
def get_jobs():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT job_id, job_title, company, location, city, salary, contact, job_description, created_at 
            FROM simple_jobs 
            ORDER BY created_at DESC 
            LIMIT 100
        """)
        rows = cur.fetchall()
        jobs = []
        for r in rows:
            jobs.append({
                "job_id": r[0],
                "job_title": r[1],
                "company": r[2] or "General",
                "location": r[3] or "",
                "city": r[4] or "Mumbai",
                "salary": r[5] or "15000",
                "contact": r[6] or "",
                "job_description": r[7] or "",
                "created_at": str(r[8]) if r[8] else None
            })
        return jobs
    except Exception as e:
        print(f"Error in get_jobs: {e}")
        # Try fallback to jobs table if simple_jobs doesn't exist
        try:
            if cur:
                cur.execute("SELECT job_id, job_title, business_name, location, city, salary, contact, job_description, created_at FROM jobs ORDER BY created_at DESC LIMIT 100")
                rows = cur.fetchall()
                jobs = []
                for r in rows:
                    jobs.append({
                        "job_id": r[0],
                        "job_title": r[1],
                        "company": r[2] or "General",
                        "location": r[3] or "",
                        "city": r[4] or "Mumbai",
                        "salary": r[5] or "15000",
                        "contact": r[6] or "",
                        "job_description": r[7] or "",
                        "created_at": str(r[8]) if r[8] else None
                    })
                return jobs
        except:
            pass
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.post("/jobs", response_model=JobResponse)
def create_job(job: JobCreate):
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO simple_jobs (job_title, company, location, city, salary, contact, job_description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING job_id, created_at
        """, (job.job_title, job.company, job.location, job.city, job.salary, job.contact, job.job_description))
        result = cur.fetchone()
        job_id = result[0]
        created_at = result[1]
        conn.commit()
        return {
            "job_id": job_id,
            "job_title": job.job_title,
            "company": job.company,
            "location": job.location,
            "city": job.city,
            "salary": job.salary,
            "contact": job.contact,
            "job_description": job.job_description,
            "created_at": str(created_at)
        }
    except Exception as e:
        print(f"Error creating job: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.post("/apply")
def apply_job(application: ApplicationCreate):
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO applications (job_id, worker_name, worker_phone, worker_city)
            VALUES (%s, %s, %s, %s)
            RETURNING application_id, applied_at
        """, (application.job_id, application.worker_name, application.worker_phone, application.worker_city))
        result = cur.fetchone()
        conn.commit()
        return {"message": "Application submitted successfully!", "application_id": result[0], "applied_at": str(result[1])}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.get("/applications")
def get_applications():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT application_id, job_id, worker_name, worker_phone, worker_city, applied_at FROM applications ORDER BY applied_at DESC LIMIT 100")
        rows = cur.fetchall()
        apps = []
        for r in rows:
            apps.append({
                "application_id": r[0],
                "job_id": r[1],
                "worker_name": r[2],
                "worker_phone": r[3],
                "worker_city": r[4],
                "applied_at": str(r[5])
            })
        return apps
    except Exception as e:
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
