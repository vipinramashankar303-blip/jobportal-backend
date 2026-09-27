import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./jobs.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Connecting to DB: {DATABASE_URL[:30]}...")

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    
    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String, nullable=False)
        phone = Column(String, unique=True, nullable=False, index=True)
        password = Column(String, nullable=False)
        role = Column(String, default="Worker")
        created_at = Column(DateTime, default=datetime.utcnow)

    class Job(Base):
        __tablename__ = "jobs"
        job_id = Column(Integer, primary_key=True, index=True)
        job_title = Column(String, nullable=False)
        company = Column(String, nullable=False)
        location = Column(String)
        city = Column(String, default="Mumbai")
        salary = Column(String)
        contact = Column(String)
        job_description = Column(Text)
        created_at = Column(DateTime, default=datetime.utcnow)

    class Application(Base):
        __tablename__ = "applications"
        id = Column(Integer, primary_key=True, index=True)
        job_id = Column(Integer, ForeignKey("jobs.job_id"))
        worker_name = Column(String)
        worker_phone = Column(String)
        worker_city = Column(String)
        created_at = Column(DateTime, default=datetime.utcnow)

    Base.metadata.create_all(bind=engine)
    print("Tables created successfully")
except Exception as e:
    print(f"DB Error but continuing: {e}")
    engine = create_engine("sqlite:///./jobs.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    
    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String, nullable=False)
        phone = Column(String, unique=True, nullable=False, index=True)
        password = Column(String, nullable=False)
        role = Column(String, default="Worker")
        created_at = Column(DateTime, default=datetime.utcnow)

    class Job(Base):
        __tablename__ = "jobs"
        job_id = Column(Integer, primary_key=True, index=True)
        job_title = Column(String, nullable=False)
        company = Column(String, nullable=False)
        location = Column(String)
        city = Column(String, default="Mumbai")
        salary = Column(String)
        contact = Column(String)
        job_description = Column(Text)
        created_at = Column(DateTime, default=datetime.utcnow)

    class Application(Base):
        __tablename__ = "applications"
        id = Column(Integer, primary_key=True, index=True)
        job_id = Column(Integer, ForeignKey("jobs.job_id"))
        worker_name = Column(String)
        worker_phone = Column(String)
        worker_city = Column(String)
        created_at = Column(DateTime, default=datetime.utcnow)
    
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="SimpleJobs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RegisterRequest(BaseModel):
    name: str
    phone: str
    password: str
    role: str = "Worker"
    full_name: str = None
    fullName: str = None

class LoginRequest(BaseModel):
    phone: str
    password: str

class JobCreate(BaseModel):
    job_title: str
    company: str
    location: str
    city: str = "Mumbai"
    salary: str
    contact: str = ""
    job_description: str = ""

class ApplyRequest(BaseModel):
    job_id: int
    worker_name: str
    worker_phone: str
    worker_city: str = "Mumbai"

@app.get("/")
def root():
    return {"message": "SimpleJobs Live!", "docs": "/docs"}

@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    # Accept full_name, fullName, or name - all work
    actual_name = data.full_name or data.fullName or data.name
    if not actual_name:
        raise HTTPException(status_code=400, detail="Name required")
    
    existing = db.query(User).filter(User.phone == data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone already registered")
    
    user = User(name=actual_name, phone=data.phone, password=data.password, role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # FIX: Return ALL variants so frontend never crashes on full_name
    return {
        "message": "Account created!", 
        "user_id": user.id,
        "id": user.id,
        "name": user.name,
        "full_name": user.name,
        "fullName": user.name,
        "full name": user.name,
        "role": user.role,
        "phone": user.phone
    }

@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == data.phone, User.password == data.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid phone or password")
    
    # FIX: Return ALL variants
    return {
        "message": "Login success", 
        "user_id": user.id,
        "id": user.id,
        "name": user.name,
        "full_name": user.name,
        "fullName": user.name,
        "full name": user.name,
        "role": user.role,
        "phone": user.phone
    }

@app.get("/jobs")
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.job_id.desc()).all()
    return [{"job_id": j.job_id, "job_title": j.job_title, "title": j.job_title, "company": j.company, "location": j.location, "city": j.city, "salary": j.salary, "contact": j.contact, "job_description": j.job_description, "created_at": str(j.created_at)} for j in jobs] if jobs else []

@app.post("/jobs")
def create_job(data: JobCreate, db: Session = Depends(get_db)):
    job = Job(job_title=data.job_title, company=data.company, location=data.location, city=data.city, salary=data.salary, contact=data.contact, job_description=data.job_description)
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"message": "Job created", "job_id": job.job_id}

@app.post("/apply")
def apply_job(data: ApplyRequest, db: Session = Depends(get_db)):
    app_rec = Application(job_id=data.job_id, worker_name=data.worker_name, worker_phone=data.worker_phone, worker_city=data.worker_city)
    db.add(app_rec)
    db.commit()
    return {"message": "Applied!"}
