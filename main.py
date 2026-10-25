# AgriGuru AI - FastAPI backend with JWT authentication.
# Run: python -m uvicorn main:app --reload

import io
import logging
import os
import re
 
import joblib
import pandas as pd
import requests
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
 
from auth import (
    create_access_token, create_user, get_current_user, get_db,
    get_user_by_email, hash_password, verify_password,
)
from database import Base, History, User, engine
from fertilizer import BAG_KG, DOSES, fertilizer_plan
 
log = logging.getLogger("agriguru")
app = FastAPI(title="AgriGuru AI")
 
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
crop_model = joblib.load("crop_model.joblib") if os.path.exists("crop_model.joblib") else None
DISEASE_MODEL = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
DISEASE_MIN_CONFIDENCE = 0.60     # below this the app says "not sure"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
classifier = None
 
Base.metadata.create_all(bind=engine)
 
 
@app.get("/")
def home():
    return FileResponse("index.html")
 
 
# ---------- request models ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit
 
 
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
            image_processor="google/mobilenet_v2_1.0_224",
        )
    return classifier
 
 
def save_history(db: Session, user: User, feature: str, inputs: str, result: str):
    db.add(History(user_id=user.id, feature=feature, inputs=inputs[:200], result=result[:200]))
    db.commit()
 
 
# ---------- auth ----------
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if len(body.password.encode()) > 72:
        raise HTTPException(400, "Password must be at most 72 bytes long.")
    email = str(body.email).strip().lower()
    if get_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    try:
        user = create_user(db, body.name, email, hash_password(body.password))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return {"id": user.id, "name": user.name, "email": user.email}
 
 
@app.post("/api/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_email(db, form.username)
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.",
                            headers={"WWW-Authenticate": "Bearer"})
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
    # Public metadata so the UI can fill the crop selector and show what is ready.
    return {
        "crops": list(DOSES.keys()),
        "crop_model_ready": crop_model is not None,
        "fertilizer_ready": bool(DOSES),
    }
 
 
# ---------- crop recommendation ----------
@app.post("/api/crop")
def crop(body: CropIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if crop_model is None:
        raise HTTPException(503, "Crop model file (crop_model.joblib) not found.")
    row = pd.DataFrame([[getattr(body, f) for f in FEATURES]], columns=FEATURES)
    chances = crop_model.predict_proba(row)[0]
    order = chances.argsort()[::-1][:3]
    top = [{"crop": str(crop_model.classes_[i]).title(), "chance": round(float(chances[i]) * 100, 1)}
           for i in order]
    save_history(db, user, "Crop recommendation",
                 f"N{body.N:g} P{body.P:g} K{body.K:g}, {body.temperature:g}°C, {body.humidity:g}%, "
                 f"pH {body.ph:g}, {body.rainfall:g} mm",
                 f"{top[0]['crop']} ({top[0]['chance']}%)")
    return {"top": top}
 
 
# ---------- fertilizer (rule-based arithmetic, no ML) ----------
@app.post("/api/fertilizer")
def fertilizer(body: FertIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not DOSES:
        raise HTTPException(503, "Fertilizer doses are not configured yet. Add sourced crop doses in fertilizer.py.")
    dose = DOSES.get(body.crop)
    if dose is None:
        raise HTTPException(404, "No fertilizer dose is available for that crop.")
    plan = fertilizer_plan(dose, {"N": body.N, "P": body.P, "K": body.K})
    items = []
    for name, kg_per_acre in plan["per_acre"].items():
        kg = kg_per_acre * body.acres
        items.append({"name": name, "kg": round(kg, 1), "bags": round(kg / BAG_KG, 1)})
    save_history(db, user, "Fertilizer plan",
                 f"{body.crop}, {body.acres:g} acre, soil N{body.N:g} P{body.P:g} K{body.K:g}",
                 ", ".join(f"{i['name']} {i['kg']} kg" for i in items))
    return {"ratings": plan["ratings"], "acres": body.acres, "items": items, "source": dose.get("source")}
 
 
# ---------- plant disease (pretrained Hugging Face model) ----------
@app.post("/api/disease")
def disease(file: UploadFile = File(...), user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image is larger than 5 MB.")
    try:
        image = Image.open(io.BytesIO(data)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "That file is not a readable image.")
    try:
        results = get_classifier()(image, top_k=3)
    except Exception:
        log.exception("Disease model failed")
        raise HTTPException(503, "Disease model is unavailable. The first run needs internet to download it.")
    best = results[0]
    sure = best["score"] >= DISEASE_MIN_CONFIDENCE
    clean = lambda s: re.sub(r"_+", " ", str(s)).strip()
    save_history(db, user, "Disease detection", (file.filename or "leaf photo")[:80],
                 f"{clean(best['label'])} ({best['score'] * 100:.1f}%)" if sure else "Not sure")
    return {
        "sure": sure,
        "label": clean(best["label"]),
        "confidence": round(best["score"] * 100, 1),
        "others": [{"label": clean(r["label"]), "confidence": round(r["score"] * 100, 1)} for r in results[1:]],
    }
 
 
# ---------- weather (Open-Meteo, no API key) ----------
WMO = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 61: "Light rain", 63: "Rain",
       65: "Heavy rain", 80: "Showers", 81: "Showers", 82: "Heavy showers", 95: "Thunderstorm",
       96: "Thunderstorm", 99: "Thunderstorm"}
 
 
def weather_alerts(current, forecast):
    """Simple rules on forecast numbers. Not expert advice."""
    alerts = []
    wet = [f for f in forecast if f["rain_prob"] >= 60]
    if wet:
        alerts.append("Rain likely on " + ", ".join(f["date"] for f in wet)
                      + ". Keep harvested produce and fertilizer in dry storage.")
    windy = [f for f in forecast if f["wind_max"] >= 25]
    if windy:
        alerts.append("Strong winds (up to %d km/h) on %s. Support young plants and irrigation structures."
                      % (max(f["wind_max"] for f in windy), ", ".join(f["date"] for f in windy)))
    if current["humidity"] >= 80:
        alerts.append("High humidity right now. Check crops for fungal disease.")
    return alerts
 
 
@app.get("/api/weather")
def weather(city: str = "Jalgaon", user: User = Depends(get_current_user)):
    city = city.strip()
    if not city or len(city) > 80:
        raise HTTPException(400, "Enter a town or city name.")
    try:
        g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": city, "count": 5, "language": "en"}, timeout=10)
        g.raise_for_status()
        places = g.json().get("results") or []
        if not places:
            raise HTTPException(404, f"Could not find '{city}'.")
        place = next((p for p in places if p.get("country_code") == "IN"), places[0])
        w = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": place["latitude"], "longitude": place["longitude"],
            "timezone": "auto", "forecast_days": 5,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,surface_pressure,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max",
        }, timeout=10)
        w.raise_for_status()
        w = w.json()
    except requests.RequestException:
        raise HTTPException(502, "Weather service is unreachable. Check the internet connection.")
    cur, day = w["current"], w["daily"]
    forecast = [{
        "date": day["time"][i],
        "max": day["temperature_2m_max"][i],
        "min": day["temperature_2m_min"][i],
        "rain_prob": day["precipitation_probability_max"][i] or 0,
        "rain_mm": day["precipitation_sum"][i] or 0,
        "wind_max": day["wind_speed_10m_max"][i] or 0,
    } for i in range(len(day["time"]))]
    current = {
        "temp": cur["temperature_2m"], "feels_like": cur["apparent_temperature"],
        "humidity": cur["relative_humidity_2m"], "wind": cur["wind_speed_10m"],
        "pressure": cur["surface_pressure"], "condition": WMO.get(cur["weather_code"], "Unknown"),
    }
    return {"city": place["name"], "region": place.get("admin1"), **current,
            "forecast": forecast, "alerts": weather_alerts(current, forecast)}
 
 
# ---------- history ----------
@app.get("/api/history")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(History).filter(History.user_id == user.id)
            .order_by(History.id.desc()).limit(50).all())
    return [{"date": r.created_at.isoformat() + "Z", "feature": r.feature,
             "inputs": r.inputs, "result": r.result} for r in rows]