from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import get_connection, init_database
import os
from datetime import datetime

# STEP 1: Pehle app banao - Line 7-8
app = FastAPI(title="SimpleJobs Backend")

# STEP 2: Fir CORS middleware - Line 10-17
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# STEP 3: Fir startup event - Line 19-26 (app banne KE BAAD)
@app.on_event("startup")
def startup_event():
    try:
        print("Creating tables...")
        init_database()
        print("Tables created successfully!")
    except Exception as e:
        print(f"DB init warning (non-critical): {e}")
        pass

# STEP 4: Fir routes - Line 28 onwards
@app.get("/")
def home():
    return {"message": "Backend running - Apply to DB ready"}

# Add your other routes below...
@app.get("/jobs")
def get_jobs():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT job_id, job_title, company, location, city, salary, contact, job_description FROM simple_jobs ORDER BY created_at DESC LIMIT 50")
        rows = cur.fetchall()
        jobs = []
        for r in rows:
            jobs.append({
                "job_id": r[0],
                "job_title": r[1],
                "company": r[2],
                "location": r[3],
                "city": r[4],
                "salary": r[5],
                "contact": r[6],
                "job_description": r[7]
            })
        return jobs
    except Exception as e:
        return []
    finally:
        if cur: cur.close()
        if conn: conn.close()
