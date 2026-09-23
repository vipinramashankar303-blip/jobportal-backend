
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from database import get_connection
import jwt # PyJWT
from datetime import datetime, timedelta
import os

app = FastAPI(title="Job Portal API", description="Secure Job Finder Backend - College Demo", version="2.0.0")

# --- 1. CORS CONFIGURATION (Frontend Connection) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. SECURITY & AUTHENTICATION SETUP ---
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "rozgar_setu_college_project_super_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 Day token expiry

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Middleware: Verify JWT Token (Isse hum endpoints ko lock/protect karenge)
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid Authentication Token")
        return {"user_id": user_id, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please login again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


# --- 3. API ROUTES ---

@app.get("/")
def home():
    return {"message": "Job Portal Backend is running successfully - College Demo Ready", "version": "2.0"}

@app.get("/database-test")
def database_test():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT current_database();")
        database_name = cursor.fetchone()[0]
        return {"message": "Database connected successfully", "database": database_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Hamesha connection close karna chahiye taaki server hang na ho
        if cursor: cursor.close()
        if connection: connection.close()

class UserCreate(BaseModel):
    full_name: str
    phone: str
    email: str | None = None
    password: str
    role: str
    preferred_language: str = "Hindi"

@app.post("/register")
def register_user(user: UserCreate):
    allowed_roles = ["worker", "employer", "admin"]
    if user.role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must contain at least 6 characters")
    
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        cursor.execute("SELECT user_id FROM users WHERE phone = %s OR (%s IS NOT NULL AND email = %s)", (user.phone, user.email, user.email))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Phone or email already registered")
        
        password_hash = hash_password(user.password)
        cursor.execute(
            "INSERT INTO users (full_name, phone, email, password_hash, role, preferred_language) VALUES (%s, %s, %s, %s, %s, %s) RETURNING user_id",
            (user.full_name, user.phone, user.email, password_hash, user.role, user.preferred_language)
        )
        user_id = cursor.fetchone()[0]
        connection.commit()
        return {"message": "Registration successful", "user_id": user_id, "role": user.role}
    except HTTPException:
        raise
    except Exception as e:
        if connection: connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

class LoginRequest(BaseModel):
    phone: str
    password: str

@app.post("/login")
def login_user(data: LoginRequest):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, full_name, phone, email, password_hash, role, preferred_language, is_active FROM users WHERE phone = %s", (data.phone,))
        user = cursor.fetchone()
        
        if not user or not verify_password(data.password, user[4]):
            raise HTTPException(status_code=401, detail="Invalid phone number or password")
        if not user[7]:
            raise HTTPException(status_code=403, detail="Your account is inactive")
        
        # Ye Token Generate karega jo frontend mein localStorage mein save hoga
        access_token = create_access_token(data={"user_id": user[0], "role": user[5]})
        
        return {
            "message": "Login successful",
            "access_token": access_token, 
            "token_type": "bearer",
            "user_data": {
                "user_id": user[0], "full_name": user[1], "phone": user[2], "email": user[3], "role": user[5], "preferred_language": user[6]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

class WorkerProfileCreate(BaseModel):
    user_id: int
    education_level: str | None = None
    experience_years: float = 0
    current_location: str | None = None
    preferred_distance_km: float = 5
    expected_salary: float | None = None
    salary_period: str | None = None
    preferred_job_type: str | None = None
    bio: str | None = None

# PROTECTED ROUTE: Depends(get_current_user) check karega ki token valid hai ya nahi
@app.post("/worker-profile")
def create_worker_profile(data: WorkerProfileCreate, current_user: dict = Depends(get_current_user)):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO worker_profiles (user_id, education_level, experience_years, current_location, preferred_distance_km, expected_salary, salary_period, preferred_job_type, bio) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING worker_id", (data.user_id, data.education_level, data.experience_years, data.current_location, data.preferred_distance_km, data.expected_salary, data.salary_period, data.preferred_job_type, data.bio))
        worker_id = cursor.fetchone()[0]
        connection.commit()
        return {"message": "Worker profile created", "worker_id": worker_id}
    except Exception as e:
        if connection: connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.get("/worker-profile/{user_id}")
def get_worker_profile(user_id: int, current_user: dict = Depends(get_current_user)):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT worker_id, user_id, education_level, experience_years, current_location, preferred_distance_km, expected_salary, salary_period, preferred_job_type, bio FROM worker_profiles WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Worker profile not found")
        return {"worker_id": row[0], "user_id": row[1], "education_level": row[2], "experience_years": float(row[3]), "current_location": row[4], "preferred_distance_km": float(row[5]), "expected_salary": float(row[6]) if row[6] is not None else None, "salary_period": row[7], "preferred_job_type": row[8], "bio": row[9]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

class EmployerProfileCreate(BaseModel):
    user_id: int
    business_name: str
    business_type: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    area: str | None = None
    pincode: str | None = None

@app.post("/employer-profile")
def create_employer_profile(data: EmployerProfileCreate, current_user: dict = Depends(get_current_user)):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO employers (user_id, business_name, business_type, phone, address, city, area, pincode) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING employer_id", (data.user_id, data.business_name, data.business_type, data.phone, data.address, data.city, data.area, data.pincode))
        employer_id = cursor.fetchone()[0]
        connection.commit()
        return {"message": "Employer profile created", "employer_id": employer_id}
    except Exception as e:
        if connection: connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.get("/categories")
def get_categories():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT category_id, category_name, icon_name FROM job_categories ORDER BY category_id")
        rows = cursor.fetchall()
        return [{"category_id": row[0], "category_name": row[1], "icon_name": row[2]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

class JobCreate(BaseModel):
    employer_id: int
    category_id: int
    job_title: str
    job_description: str
    required_education: str | None = None
    minimum_experience: float = 0
    salary_min: float | None = None
    salary_max: float | None = None
    salary_period: str
    job_type: str
    working_hours: str | None = None
    shift_type: str | None = None
    location: str
    area: str | None = None
    city: str | None = None
    pincode: str | None = None

# PROTECTED: Sirf logged in employers hi job daal sakte hain
@app.post("/jobs")
def create_job(job: JobCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "employer":
        raise HTTPException(status_code=403, detail="Only employers can post jobs")
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO jobs (employer_id, category_id, job_title, job_description, required_education, minimum_experience, salary_min, salary_max, salary_period, job_type, working_hours, shift_type, location, area, city, pincode) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING job_id", (job.employer_id, job.category_id, job.job_title, job.job_description, job.required_education, job.minimum_experience, job.salary_min, job.salary_max, job.salary_period, job.job_type, job.working_hours, job.shift_type, job.location, job.area, job.city, job.pincode))
        job_id = cursor.fetchone()[0]
        connection.commit()
        return {"message": "Job created successfully", "job_id": job_id, "status": "pending"}
    except Exception as e:
        if connection: connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

# PUBLIC: Job list koi bhi dekh sakta hai
@app.get("/jobs")
def get_jobs():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT j.job_id, j.job_title, j.job_description, j.required_education, j.minimum_experience, j.salary_min, j.salary_max, j.salary_period, j.job_type, j.working_hours, j.shift_type, j.location, j.area, j.city, j.pincode, e.business_name, jc.category_name, e.verification_status, j.is_verified, j.posted_at
            FROM jobs j
            JOIN employers e ON j.employer_id = e.employer_id
            JOIN job_categories jc ON j.category_id = jc.category_id
            WHERE j.status = 'approved'
            ORDER BY j.posted_at DESC
        """)
        rows = cursor.fetchall()
        jobs = []
        for row in rows:
            jobs.append({
                "job_id": row[0], "job_title": row[1], "job_description": row[2], "required_education": row[3], "minimum_experience": float(row[4]), "salary_min": float(row[5]) if row[5] is not None else None, "salary_max": float(row[6]) if row[6] is not None else None, "salary_period": row[7], "job_type": row[8], "working_hours": row[9], "shift_type": row[10], "location": row[11], "area": row[12], "city": row[13], "pincode": row[14], "business_name": row[15], "category_name": row[16], "employer_verified": row[17] == "verified", "job_verified": row[18], "posted_at": row[19]
            })
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

class ApplicationCreate(BaseModel):
    job_id: int
    worker_id: int

@app.post("/applications")
def apply_for_job(data: ApplicationCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "worker":
        raise HTTPException(status_code=403, detail="Only workers can apply for jobs")
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT application_id FROM applications WHERE job_id = %s AND worker_id = %s", (data.job_id, data.worker_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="You have already applied for this job")
        
        cursor.execute("INSERT INTO applications (job_id, worker_id) VALUES (%s, %s) RETURNING application_id", (data.job_id, data.worker_id))
        application_id = cursor.fetchone()[0]
        connection.commit()
        return {"message": "Job application submitted successfully", "application_id": application_id, "status": "applied"}
    except HTTPException:
        raise
    except Exception as e:
        if connection: connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.get("/applications/worker/{worker_id}")
def get_worker_applications(worker_id: int, current_user: dict = Depends(get_current_user)):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT a.application_id, a.job_id, j.job_title, e.business_name, a.application_status, a.applied_at FROM applications a JOIN jobs j ON a.job_id = j.job_id JOIN employers e ON j.employer_id = e.employer_id WHERE a.worker_id = %s ORDER BY a.applied_at DESC", (worker_id,))
        rows = cursor.fetchall()
        return [{"application_id": row[0], "job_id": row[1], "job_title": row[2], "business_name": row[3], "application_status": row[4], "applied_at": row[5]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

class SavedJobCreate(BaseModel):
    worker_id: int
    job_id: int

@app.post("/saved-jobs")
def save_job(data: SavedJobCreate, current_user: dict = Depends(get_current_user)):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO saved_jobs (worker_id, job_id) VALUES (%s, %s) RETURNING saved_job_id", (data.worker_id, data.job_id))
        saved_job_id = cursor.fetchone()[0]
        connection.commit()
        return {"message": "Job saved successfully", "saved_job_id": saved_job_id}
    except Exception as e:
        if connection: connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

# --- 4. NEW FEATURES FOR LOW-EDUCATED USERS (Added without deleting old code) ---
# Ye sab naya add kiya hai - purana kuch delete nahi kiya

from typing import Optional, List

# Simple Hindi/English dictionary for frontend buttons
HINDI_TRANSLATIONS = {
    "Driver": "ड्राइवर", "Cook": "रसोइया", "Maid": "नौकरानी", "Security Guard": "सुरक्षा गार्ड",
    "Labour": "मजदूर", "Electrician": "इलेक्ट्रीशियन", "Plumber": "प्लंबर", "Delivery Boy": "डिलीवरी बॉय",
    "search_jobs": "नौकरी खोजें", "post_job": "नौकरी डालें", "call_now": "अभी कॉल करें",
    "whatsapp": "व्हाट्सएप करें", "apply": "अप्लाई करें", "near_me": "मेरे पास की नौकरी"
}

# Trending category list for big buttons
BIG_BUTTON_CATEGORIES = [
    {"id": 1, "en": "Driver", "hi": "ड्राइवर", "icon": "🚗", "color": "#3b82f6"},
    {"id": 2, "en": "Cook", "hi": "रसोइया", "icon": "🍳", "color": "#f59e0b"},
    {"id": 3, "en": "Maid", "hi": "नौकरानी", "icon": "🧹", "color": "#10b981"},
    {"id": 4, "en": "Security Guard", "hi": "सुरक्षा गार्ड", "icon": "🛡️", "color": "#6366f1"},
    {"id": 5, "en": "Labour", "hi": "मजदूर", "icon": "👷", "color": "#ef4444"},
    {"id": 6, "en": "Delivery Boy", "hi": "डिलीवरी बॉय", "icon": "🛵", "color": "#8b5cf6"},
    {"id": 7, "en": "Electrician", "hi": "इलेक्ट्रीशियन", "icon": "💡", "color": "#f97316"},
    {"id": 8, "en": "Plumber", "hi": "प्लंबर", "icon": "🔧", "color": "#06b6d4"},
]

@app.get("/big-buttons")
def get_big_buttons(lang: str = "both"):
    # Frontend ke liye bade buttons ka data
    return {"buttons": BIG_BUTTON_CATEGORIES, "translations": HINDI_TRANSLATIONS}

@app.get("/translate")
def get_translations():
    return HINDI_TRANSLATIONS

@app.get("/jobs/category/{category_name}")
def get_jobs_by_category_name(category_name: str):
    # Example: /jobs/category/Driver -> easy filter
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        # case-insensitive search
        cursor.execute("""
            SELECT j.job_id, j.job_title, j.job_description, j.salary_min, j.salary_max, j.salary_period, j.location, j.city, e.business_name, jc.category_name, j.posted_at
            FROM jobs j
            JOIN employers e ON j.employer_id = e.employer_id
            JOIN job_categories jc ON j.category_id = jc.category_id
            WHERE j.status = 'approved' AND LOWER(jc.category_name) LIKE LOWER(%s)
            ORDER BY j.posted_at DESC
        """, (f"%{category_name}%",))
        rows = cursor.fetchall()
        return [{"job_id": r[0], "job_title": r[1], "job_description": r[2], "salary_min": float(r[3]) if r[3] else None, "salary_max": float(r[4]) if r[4] else None, "salary_period": r[5], "location": r[6], "city": r[7], "business_name": r[8], "category_name": r[9], "posted_at": r[10]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

class SimpleJobCreate(BaseModel):
    employer_id: int
    category_name: str  # User can send "Driver" instead of category_id
    job_title: str
    salary: float
    location: str
    phone: str  # simple contact
    city: str | None = None

@app.post("/jobs/simple-create")
def create_simple_job(data: SimpleJobCreate, current_user: dict = Depends(get_current_user)):
    # Low-educated employer ke liye simple job post - sirf 5 field
    if current_user["role"] != "employer":
        raise HTTPException(status_code=403, detail="Only employers can post jobs")
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        # find category_id by name
        cursor.execute("SELECT category_id FROM job_categories WHERE LOWER(category_name) LIKE LOWER(%s) LIMIT 1", (f"%{data.category_name}%",))
        cat = cursor.fetchone()
        if not cat:
            # agar category nahi mili to first category le lo
            cursor.execute("SELECT category_id FROM job_categories LIMIT 1")
            cat = cursor.fetchone()
        category_id = cat[0]
        cursor.execute(
            "INSERT INTO jobs (employer_id, category_id, job_title, job_description, salary_min, salary_period, job_type, location, city) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING job_id",
            (data.employer_id, category_id, data.job_title, f"Contact: {data.phone} - Simple job for {data.category_name}", data.salary, "monthly", "full-time", data.location, data.city)
        )
        job_id = cursor.fetchone()[0]
        connection.commit()
        return {"message": "Job posted! SimpleJobs par dikhegi", "job_id": job_id, "status": "pending", "hindi_message": "नौकरी सफलतापूर्वक डाली गई!"}
    except Exception as e:
        if connection: connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.get("/jobs/nearby")
def nearby_jobs(city: str = None, area: str = None, pincode: str = None):
    # Aas-paas ki naukri
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        query = """
            SELECT j.job_id, j.job_title, j.location, j.city, j.area, e.business_name, jc.category_name
            FROM jobs j
            JOIN employers e ON j.employer_id = e.employer_id
            JOIN job_categories jc ON j.category_id = jc.category_id
            WHERE j.status = 'approved'
        """
        params = []
        if city:
            query += " AND LOWER(j.city) LIKE LOWER(%s)"
            params.append(f"%{city}%")
        if area:
            query += " AND LOWER(j.area) LIKE LOWER(%s)"
            params.append(f"%{area}%")
        if pincode:
            query += " AND j.pincode = %s"
            params.append(pincode)
        query += " ORDER BY j.posted_at DESC LIMIT 20"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [{"job_id": r[0], "job_title": r[1], "location": r[2], "city": r[3], "area": r[4], "business_name": r[5], "category_name": r[6]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

class VoiceSearchRequest(BaseModel):
    voice_text: str  # e.g., "driver ki naukri chahiye mumbai me"
    language: str = "Hindi"

@app.post("/voice-search")
def voice_search(data: VoiceSearchRequest):
    # Simple keyword extraction from voice text
    text_lower = data.voice_text.lower()
    detected_category = None
    for cat in BIG_BUTTON_CATEGORIES:
        if cat["en"].lower() in text_lower or cat["hi"] in text_lower:
            detected_category = cat["en"]
            break
    return {
        "original_text": data.voice_text,
        "detected_category": detected_category,
        "search_keywords": text_lower.split(),
        "suggested_endpoint": f"/jobs/category/{detected_category}" if detected_category else "/jobs",
        "hindi_response": f"{detected_category or 'सभी'} नौकरियां दिखाई जा रही हैं"
    }

@app.get("/jobs/{job_id}/contact")
def get_job_contact(job_id: int):
    # 1-click call ke liye
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT e.business_name, e.phone, u.phone, j.job_title
            FROM jobs j
            JOIN employers e ON j.employer_id = e.employer_id
            JOIN users u ON e.user_id = u.user_id
            WHERE j.job_id = %s
        """, (job_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        business_name, emp_phone, user_phone, job_title = row
        contact_phone = emp_phone or user_phone
        return {
            "job_id": job_id,
            "job_title": job_title,
            "business_name": business_name,
            "call_number": contact_phone,
            "whatsapp_link": f"https://wa.me/91{contact_phone}?text=Namaste,%20mujhe%20{job_title}%20ke%20liye%20apply%20karna%20hai",
            "call_link": f"tel:{contact_phone}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.get("/jobs/easy-search")
def easy_search(q: str = "", city: str = "", salary_min: float = 0):
    # Sabse easy search - sirf ek word likho
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT j.job_id, j.job_title, j.job_description, j.location, j.city, j.salary_min, e.business_name
            FROM jobs j
            JOIN employers e ON j.employer_id = e.employer_id
            WHERE j.status = 'approved'
            AND (LOWER(j.job_title) LIKE LOWER(%s) OR LOWER(j.job_description) LIKE LOWER(%s))
            AND (LOWER(j.city) LIKE LOWER(%s) OR %s = '')
            AND (j.salary_min >= %s OR %s = 0)
            ORDER BY j.posted_at DESC LIMIT 30
        """, (f"%{q}%", f"%{q}%", f"%{city}%", city, salary_min, salary_min))
        rows = cursor.fetchall()
        return [{"job_id": r[0], "job_title": r[1], "job_description": r[2][:100]+"...", "location": r[3], "city": r[4], "salary": r[5], "business_name": r[6]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.get("/faqs/easy")
def easy_faqs(lang: str = "Hindi"):
    faqs = [
        {"q": "Job kaise dhoondu?", "a": "Bade button pe click karo - Driver, Cook, etc.", "en_q": "How to find job?", "en_a": "Click on big buttons"},
        {"q": "Apply kaise karu?", "a": "Job pe click karo, fir Call ya WhatsApp button dabao", "en_q": "How to apply?", "en_a": "Click job, then Call or WhatsApp"},
        {"q": "Naukri kaise daalu?", "a": "+ Naukri Daalo button dabao, sirf 5 cheez bharo", "en_q": "How to post job?", "en_a": "Click + Post Job, fill only 5 fields"},
    ]
    return {"faqs": faqs, "lang": lang}

@app.get("/health")
def health():
    return {"status": "OK", "backend": "running & secured with JWT", "database": "PostgreSQL", "college_demo": "ready", "new_features": ["big-buttons", "translate", "category-filter", "simple-create", "nearby", "voice-search", "contact", "easy-search", "faqs"], "message": "Low-educated friendly features added"}

