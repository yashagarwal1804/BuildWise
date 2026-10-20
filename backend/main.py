from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

APP_NAME = "BuildWise AI"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

app = FastAPI(title="BuildWise AI Construction Intelligence API", version="1.0.0")
origins = [x.strip() for x in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    project_type: str = "Residential building"


class ValuationRequest(BaseModel):
    city: str = Field(min_length=2, max_length=100)
    area_sqft: float = Field(gt=0, le=10_000_000)
    property_type: Literal["Apartment", "Independent house", "Commercial", "Plot"] = "Apartment"
    rate_per_sqft: float = Field(gt=0, le=10_000_000)
    age_years: float = Field(default=0, ge=0, le=200)
    condition: Literal["Excellent", "Good", "Average", "Needs repair"] = "Good"


class PlanRequest(BaseModel):
    project_name: str = Field(default="New construction project", max_length=120)
    building_type: str = "Residential building"
    built_up_area_sqft: float = Field(gt=0, le=2_000_000)
    floors: int = Field(default=2, ge=1, le=100)
    finish_level: Literal["Basic", "Standard", "Premium"] = "Standard"
    city: str = "Bhopal"
    budget_inr: float | None = Field(default=None, gt=0)


class VisualizationRequest(BaseModel):
    building_type: Literal["Residential", "Commercial", "Mixed use"] = "Residential"
    floors: int = Field(default=3, ge=1, le=12)
    facade: Literal["Modern", "Minimal", "Traditional", "Industrial"] = "Modern"
    plot_width_ft: float = Field(default=30, ge=10, le=1000)
    plot_depth_ft: float = Field(default=50, ge=10, le=1000)


class WeatherRequest(BaseModel):
    city: str = Field(min_length=2, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


def demo_mode() -> bool:
    return not bool(GEMINI_API_KEY)


async def gemini_json(prompt: str, image_bytes: bytes | None = None, mime_type: str | None = None) -> dict[str, Any] | None:
    """Call Gemini when configured. Return None for demo fallback; never expose secrets."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        contents: list[Any] = [prompt]
        if image_bytes is not None:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type or "image/jpeg"))
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        text = (response.text or "").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
        return json.loads(text)
    except Exception as exc:
        # Keep the service usable and do not leak provider details or credentials to the UI.
        print(f"AI provider request failed: {type(exc).__name__}")
        return None


def clean_text(value: Any, default: str = "Not available") -> str:
    return str(value).strip() if value is not None and str(value).strip() else default


@app.get("/")
def root():
    return {"name": APP_NAME, "status": "ok", "docs": "/docs", "mode": "demo" if demo_mode() else "ai"}


@app.get("/api/health")
def health():
    return {"status": "healthy", "service": APP_NAME, "ai_configured": not demo_mode(), "mode": "demo" if demo_mode() else "ai"}


@app.post("/api/analyze/safety")
async def analyze_safety(image: UploadFile = File(...), notes: str = Form(default="")):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload a JPG, PNG, or another supported image file.")
    data = await image.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller.")
    if len(data) < 16:
        raise HTTPException(status_code=400, detail="The uploaded image appears to be empty or incomplete.")
    prompt = f'''Analyze this construction site image for visible safety concerns. Context from user: {notes or 'No extra context'}. Return JSON only with this schema: {{"overall_risk":"Low|Medium|High|Critical","summary":"string","hazards":[{{"title":"string","severity":"Low|Medium|High|Critical","observation":"string","recommendation":"string"}}],"ppe_observations":["string"],"immediate_actions":["string"],"limitations":"string"}} Be conservative. Mention only visible evidence, do not claim unseen conditions, and state that this is decision support, not a certified inspection.'''
    result = await gemini_json(prompt, data, image.content_type)
    if result is None:
        result = {
            "overall_risk": "Medium",
            "summary": "Demo analysis only: AI is not configured, so this is a sample result rather than an assessment of the uploaded image.",
            "hazards": [{"title": "Manual safety inspection required", "severity": "Medium", "observation": "The demo cannot interpret the image without a configured multimodal AI key.", "recommendation": "Have a qualified site supervisor inspect fall protection, access routes, housekeeping, electrical hazards, and equipment separation."}],
            "ppe_observations": ["PPE compliance cannot be verified in demo mode."],
            "immediate_actions": ["Do not use this sample result to approve work; complete a competent-person inspection."],
            "limitations": "Demo fallback. Configure GEMINI_API_KEY for image-based analysis. AI output is not a substitute for a legally required safety inspection."
        }
    result.setdefault("limitations", "AI results can miss hazards and must be verified by a qualified site professional.")
    return {"mode": "demo" if demo_mode() else "ai", "result": result}


@app.post("/api/analyze/cracks")
async def analyze_cracks(image: UploadFile = File(...), notes: str = Form(default="")):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload an image file.")
    data = await image.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller.")
    if len(data) < 16:
        raise HTTPException(status_code=400, detail="The uploaded image appears to be empty or incomplete.")
    prompt = f'''Inspect the supplied construction image for visible cracks or surface defects. Context: {notes or 'No additional context'}. Return JSON only: {{"visible_defect":"Yes|No|Unclear","likely_pattern":"string","visual_severity":"Low|Moderate|High|Unclear","possible_causes":["string"],"recommended_next_steps":["string"],"urgent_warning_signs":["string"],"limitations":"string"}} Do not diagnose structural safety from an image alone. If scale, location, width, depth or context is unavailable, say so. Recommend an engineer for significant, growing, diagonal, wide, leaking or load-bearing cracks.'''
    result = await gemini_json(prompt, data, image.content_type)
    if result is None:
        result = {"visible_defect": "Unclear", "likely_pattern": "Image interpretation is unavailable in demo mode.", "visual_severity": "Unclear", "possible_causes": ["Cause cannot be inferred without image-capable AI and an on-site assessment."], "recommended_next_steps": ["Photograph the defect with a ruler for scale.", "Record location, length, width, whether it is growing, and whether water is present.", "Ask a qualified structural engineer to assess concerning cracks."], "urgent_warning_signs": ["Rapidly widening cracks, sagging, displacement, falling concrete, or sudden new cracks need urgent professional assessment."], "limitations": "Demo fallback. This tool cannot certify structural integrity. Configure GEMINI_API_KEY for image analysis."}
    result.setdefault("limitations", "Image-based crack assessment is preliminary and cannot certify structural safety.")
    return {"mode": "demo" if demo_mode() else "ai", "result": result}


@app.post("/api/valuation")
async def valuation(req: ValuationRequest):
    condition_factor = {"Excellent": 1.04, "Good": 1.0, "Average": 0.92, "Needs repair": 0.78}[req.condition]
    age_factor = max(0.65, 1 - max(req.age_years, 0) * 0.006)
    estimated = req.area_sqft * req.rate_per_sqft * condition_factor * age_factor
    prompt = f'''Give a short property valuation commentary for a {req.property_type} in {req.city}, area {req.area_sqft} sqft, age {req.age_years} years, condition {req.condition}. User-supplied base rate is INR {req.rate_per_sqft}/sqft. An illustrative formula estimate is INR {estimated:.0f}. Return JSON only: {{"market_factors":["string"],"caveats":["string"],"documents_to_check":["string"]}} Do not claim current market research or professional appraisal.'''
    extra = await gemini_json(prompt)
    return {"mode": "demo" if demo_mode() else "ai", "city": req.city, "property_type": req.property_type, "area_sqft": req.area_sqft, "base_rate_inr_per_sqft": req.rate_per_sqft, "adjustment_factors": {"condition": condition_factor, "age": round(age_factor, 3)}, "estimated_value_inr": round(estimated), "estimated_value_lakh": round(estimated / 100000, 2), "range_inr": {"low": round(estimated * 0.85), "high": round(estimated * 1.15)}, "commentary": extra or {"market_factors": ["Locality, road access, title, floor, amenities and comparable recent transactions can materially change value."], "caveats": ["Illustrative estimate only; the entered rate is user-provided, not live market data.", "Not a registered valuer's appraisal."], "documents_to_check": ["Title and encumbrance records", "Approved building plan and completion/occupancy certificate", "Recent comparable transactions"]}}


@app.post("/api/plan")
async def create_plan(req: PlanRequest):
    area = req.built_up_area_sqft
    rates = {"Basic": 1650, "Standard": 2100, "Premium": 2850}
    rate = rates[req.finish_level]
    estimated_cost = area * rate
    phase_names = ["Site survey & approvals", "Foundation and plinth", "Structural frame", "Masonry and roofing", "Electrical & plumbing rough-in", "Plastering and waterproofing", "Flooring, doors and finishes", "Testing and handover"]
    durations = [10, 18, 28, 20, 14, 15, 25, 7]
    start = date.today()
    tasks = []
    current = start
    for idx, (name, duration) in enumerate(zip(phase_names, durations)):
        tasks.append({"id": idx + 1, "task": name, "duration_days": duration, "start_date": current.isoformat(), "end_date": (current + timedelta(days=duration - 1)).isoformat(), "dependency": None if idx == 0 else idx, "status": "Planned"})
        current += timedelta(days=duration)
    # Coarse thumb rules only; final quantities require drawings, specifications and engineer review.
    cement_bags = round(area * (0.38 if req.finish_level == "Basic" else 0.42 if req.finish_level == "Standard" else 0.46))
    steel_kg = round(area * 3.5)
    bricks = round(area * 8.0)
    sand_cft = round(area * 1.8)
    prompt = f'''For a {req.building_type}, {area} sqft built-up area, {req.floors} floors, {req.finish_level} finish in {req.city}, provide a short planning checklist. Return JSON only: {{"key_assumptions":["string"],"risks":["string"],"professional_reviews_required":["string"]}} Mention local codes, soil report, structural drawings, approvals, quantities and prices must be validated.'''
    extra = await gemini_json(prompt)
    return {"mode": "demo" if demo_mode() else "ai", "project_name": req.project_name, "inputs": req.model_dump(), "cost_estimate": {"currency": "INR", "unit_rate_inr_per_sqft": rate, "estimated_total_inr": round(estimated_cost), "estimated_total_lakh": round(estimated_cost / 100000, 2), "contingency_10_percent_inr": round(estimated_cost * 0.1), "budget_inr": req.budget_inr, "within_budget": None if req.budget_inr is None else estimated_cost * 1.1 <= req.budget_inr, "note": "Indicative thumb-rule estimate only; not a bill of quantities or contractor quote."}, "material_estimate": [{"material": "Cement", "quantity": cement_bags, "unit": "bags", "basis": "Approximate thumb rule"}, {"material": "Reinforcement steel", "quantity": steel_kg, "unit": "kg", "basis": "Approximate thumb rule"}, {"material": "Bricks", "quantity": bricks, "unit": "pieces", "basis": "Approximate thumb rule"}, {"material": "Sand", "quantity": sand_cft, "unit": "cubic feet", "basis": "Approximate thumb rule"}], "schedule": {"estimated_duration_days": sum(durations), "target_handover": current.isoformat(), "tasks": tasks}, "advisory": extra or {"key_assumptions": ["Single project area and sequential high-level phases are assumed.", "Weather, curing, procurement, labor and approval delays can change the schedule."], "risks": ["Soil conditions and structural design can materially alter cost and timeline.", "Rates vary by city, date, material grade and contractor."], "professional_reviews_required": ["Architectural and structural drawings", "Geotechnical/soil report", "Local approvals and building codes", "Quantity take-off and contractor quotations"]}}


@app.post("/api/assistant")
async def assistant(req: ChatRequest):
    prompt = f'''You are a careful construction project assistant. Project type: {req.project_type}. User asks: {req.question}. Return JSON only: {{"answer":"string","action_items":["string"],"safety_note":"string","sources_or_checks":["string"]}} Give practical general guidance. Do not invent code clauses, prices, weather or site facts. For structural, legal, electrical or safety-critical questions, advise qualified local professionals.'''
    result = await gemini_json(prompt)
    if result is None:
        q = req.question.lower()
        if any(word in q for word in ["crack", "structural", "beam", "column", "foundation"]):
            answer = "For structural concerns, document the location, width, length, pattern and changes over time. Avoid covering or repairing a potentially structural crack before it is assessed. Have a qualified structural engineer inspect it, especially if it is widening, diagonal, accompanied by sagging or water ingress, or appears suddenly."
        elif any(word in q for word in ["safety", "helmet", "ppe", "fall", "scaffold"]):
            answer = "Use a documented site walk-through: check fall protection, scaffold tags and access, PPE, electrical protection, housekeeping, lifting zones, and equipment/pedestrian separation. Stop work and escalate any imminent danger to the site safety lead."
        else:
            answer = "Break the task into a written scope, responsible owner, materials and lead times, dependencies, inspection hold-points, and a daily progress record. Confirm local codes, approved drawings, quantities and current supplier quotations before committing cost or schedule."
        result = {"answer": answer, "action_items": ["Record the site condition and date.", "Assign an accountable owner and target date.", "Verify the next step against approved drawings and local requirements."], "safety_note": "General decision support only. Do not use this response as engineering approval or as a substitute for a competent site professional.", "sources_or_checks": ["Approved project drawings and specifications", "Applicable local building rules and safety procedures", "Qualified site engineer or safety officer"]}
    return {"mode": "demo" if demo_mode() else "ai", "result": result}


@app.post("/api/visualization")
async def create_visualization(req: VisualizationRequest):
    descriptions = {
        "Modern": "Clean horizontal lines, generous glazing, and a restrained contemporary palette.",
        "Minimal": "Simple massing, limited ornament, and a calm, uncluttered facade.",
        "Traditional": "Balanced openings, familiar proportions, and a more classic street-facing composition.",
        "Industrial": "Expressed structural rhythm, practical materials, and a robust utilitarian character.",
    }
    return {"mode": "demo" if demo_mode() else "ai", "visualization": {"building_type": req.building_type, "floors": req.floors, "style": req.facade, "plot_width_ft": req.plot_width_ft, "plot_depth_ft": req.plot_depth_ft, "description": descriptions[req.facade], "concept_status": "schematic", "limitations": "Conceptual facade only. Not to scale and not suitable for construction, permitting or structural decisions."}, "design_checks": ["Confirm setbacks, FAR/FSI, height and parking rules for the local authority.", "Validate daylight, ventilation, accessibility and fire egress with an architect.", "Coordinate facade openings with structural, plumbing and electrical drawings."]}


@app.post("/api/weather-advice")
async def weather_advice(req: WeatherRequest):
    # Open-Meteo forecast is public and does not require an API key.
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get("https://api.open-meteo.com/v1/forecast", params={"latitude": req.latitude, "longitude": req.longitude, "daily": "precipitation_probability_max,precipitation_sum,temperature_2m_max,wind_speed_10m_max", "forecast_days": 3, "timezone": "auto"})
            response.raise_for_status()
            weather = response.json()
        daily = weather.get("daily", {})
        forecast = []
        for i, day in enumerate(daily.get("time", [])):
            rain_prob = (daily.get("precipitation_probability_max") or [None] * len(daily.get("time", [])))[i]
            rain_mm = (daily.get("precipitation_sum") or [None] * len(daily.get("time", [])))[i]
            wind = (daily.get("wind_speed_10m_max") or [None] * len(daily.get("time", [])))[i]
            temp = (daily.get("temperature_2m_max") or [None] * len(daily.get("time", [])))[i]
            actions = []
            if rain_prob is not None and rain_prob >= 50 or rain_mm is not None and rain_mm >= 5:
                actions.append("Protect cement and other moisture-sensitive materials; review excavation, concrete pour and waterproofing plans.")
            if wind is not None and wind >= 35:
                actions.append("Check local wind limits for lifting, scaffolds and work at height; postpone if site rules require it.")
            if temp is not None and temp >= 38:
                actions.append("Plan shade, hydration, rest breaks and heat-stress monitoring.")
            if not actions:
                actions.append("Check the latest hourly forecast and site-specific safety thresholds before scheduling critical work.")
            forecast.append({"date": day, "precipitation_probability_max_percent": rain_prob, "precipitation_sum_mm": rain_mm, "max_temperature_c": temp, "max_wind_speed_kmh": wind, "construction_advice": actions})
        return {"city": req.city, "source": "Open-Meteo forecast API", "forecast": forecast, "note": "Forecasts are uncertain; follow official warnings and site-specific safety procedures."}
    except Exception:
        return {"city": req.city, "source": "fallback", "forecast": [], "error": "Live weather could not be retrieved. Check your internet connection or try again later.", "construction_advice": ["Check an official local forecast before concrete pours, lifting, excavation, waterproofing or work at height."]}


@app.get("/api/knowledge")
def knowledge():
    return {"topics": [
        {"title": "Site safety", "description": "Daily inspections, PPE, fall protection, scaffold access, electrical safety and housekeeping.", "checklist": ["Conduct toolbox talk", "Inspect access and edge protection", "Confirm PPE and equipment checks", "Log hazards, owners and close-out dates"]},
        {"title": "Concrete and curing", "description": "Concrete quality depends on mix design, placement, compaction, curing, temperature and approved specifications.", "checklist": ["Verify approved mix and delivery ticket", "Inspect formwork and reinforcement before pour", "Record sampling and test results", "Follow engineer-approved curing plan"]},
        {"title": "Crack documentation", "description": "Photographs alone cannot establish structural safety; width, pattern, location, movement and context matter.", "checklist": ["Photograph with scale", "Record date and location", "Track width and changes", "Escalate concerning or changing cracks to a structural engineer"]},
        {"title": "Project controls", "description": "Reliable project controls connect scope, quantities, procurement, schedule, cost and quality checks.", "checklist": ["Use approved drawings", "Track planned vs actual quantities", "Update dependencies and blockers", "Document changes and approvals"]}
    ]}
