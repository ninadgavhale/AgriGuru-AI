# AgriGuru AI - FastAPI backend with JWT authentication.
# Run: python -m uvicorn main:app --reload
import io
import os

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from PIL import Image
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from database import Base, engine, User


from auth import (
    User, create_access_token, create_user, get_current_user, get_db,
    get_user_by_email, verify_password,
)
from fertilizer import BAG_KG, DOSES, fertilizer_plan

app = FastAPI(title="AgriGuru AI")
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
crop_model = joblib.load("crop_model.joblib") if os.path.exists("crop_model.joblib") else None
DISEASE_MODEL = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
classifier = None

Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return FileResponse("index.html")


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class CropIn(BaseModel):
    N: float = Field(ge=0)
    P: float = Field(ge=0)
    K: float = Field(ge=0)
    temperature: float = Field(ge=-10, le=60)
    humidity: float = Field(ge=0, le=100)
    ph: float = Field(ge=0, le=14)
    rainfall: float = Field(ge=0)

class FertIn(BaseModel):
    crop: str
    N: float = Field(ge=0)
    P: float = Field(ge=0)
    K: float = Field(ge=0)
    acres: float = Field(gt=0, default=1)

def get_classifier():
    global classifier
    if classifier is None:
        from transformers import pipeline
        classifier = pipeline(
            "image-classification", model=DISEASE_MODEL,
            image_processor="google/mobilenet_v2_1.0_224"
        )
    return classifier

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = str(body.email).strip().lower()
    if get_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    try:
        user = create_user(db, body.name, email, body.password)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return {"id": user.id, "name": user.name, "email": user.email}

@app.post("/api/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_email(db, form.username)
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.", headers={"WWW-Authenticate": "Bearer"})
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "expires_in": int(os.getenv("ACCESS_TOKEN_MINUTES", "60")) * 60,
    }

@app.get("/api/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email}

@app.get("/api/meta")
def meta():
    # Public metadata is needed to populate the crop selector before login.
    return {"crops": list(DOSES.keys()), "crop_model_ready": crop_model is not None}

@app.post("/api/crop")
def crop(body: CropIn, user: User = Depends(get_current_user)):
    if crop_model is None:
        raise HTTPException(503, "Crop model file (crop_model.joblib) not found.")
    row = pd.DataFrame([[getattr(body, f) for f in FEATURES]], columns=FEATURES)
    chances = crop_model.predict_proba(row)[0]