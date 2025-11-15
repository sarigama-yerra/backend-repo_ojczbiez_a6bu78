import os
import random
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents

app = FastAPI(title="Snap Learn API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProgressUpdate(BaseModel):
    device_id: str
    category: str
    correct: int = 0
    attempts: int = 0
    points: int = 0
    badge: Optional[str] = None


def ensure_seed_content():
    """Seed minimal content if database is empty."""
    if db is None:
        return
    if "item" in db.list_collection_names():
        count = db["item"].count_documents({})
        if count > 0:
            return
    seed_items = [
        # Alphabets
        {"category": "alphabets", "key": "A", "label": "Apple", "phonics": "A says ah", "display": "🍎"},
        {"category": "alphabets", "key": "B", "label": "Ball", "phonics": "B says buh", "display": "🟠"},
        {"category": "alphabets", "key": "C", "label": "Cat", "phonics": "C says kuh", "display": "🐱"},
        # Numbers
        {"category": "numbers", "key": "1", "label": "One", "phonics": None, "display": "1️⃣"},
        {"category": "numbers", "key": "2", "label": "Two", "phonics": None, "display": "2️⃣"},
        {"category": "numbers", "key": "3", "label": "Three", "phonics": None, "display": "3️⃣"},
        # Colors
        {"category": "colors", "key": "red", "label": "Red", "display": "🟥"},
        {"category": "colors", "key": "blue", "label": "Blue", "display": "🟦"},
        {"category": "colors", "key": "green", "label": "Green", "display": "🟩"},
        # Animals
        {"category": "animals", "key": "dog", "label": "Dog", "display": "🐶"},
        {"category": "animals", "key": "lion", "label": "Lion", "display": "🦁"},
        {"category": "animals", "key": "bird", "label": "Bird", "display": "🐦"},
        # Shapes
        {"category": "shapes", "key": "circle", "label": "Circle", "display": "⚪"},
        {"category": "shapes", "key": "square", "label": "Square", "display": "🟥"},
        {"category": "shapes", "key": "triangle", "label": "Triangle", "display": "🔺"},
    ]
    for it in seed_items:
        create_document("item", it)


@app.on_event("startup")
async def startup_event():
    try:
        ensure_seed_content()
    except Exception:
        # If DB not available, continue; app should still run
        pass


@app.get("/")
def read_root():
    return {"message": "Snap Learn API is running"}


@app.get("/api/categories")
def get_categories():
    """Return available categories based on items in DB or defaults."""
    categories = [
        "alphabets", "numbers", "colors", "shapes", "animals",
        "fruits", "vegetables", "birds", "days", "months",
        "family", "body", "seasons", "weather", "habits", "opposites",
    ]
    try:
        if db is not None and "item" in db.list_collection_names():
            cats = db["item"].distinct("category")
            if cats:
                categories = sorted(cats)
    except Exception:
        pass
    return {"categories": categories}


@app.get("/api/items")
def list_items(category: Optional[str] = Query(None)):
    """List learning items; filter by category if provided."""
    try:
        if db is None:
            # Fallback sample content
            sample = [
                {"category": "alphabets", "key": "A", "label": "Apple", "phonics": "A says ah", "display": "🍎"},
                {"category": "alphabets", "key": "B", "label": "Ball", "phonics": "B says buh", "display": "🟠"},
                {"category": "numbers", "key": "1", "label": "One", "display": "1️⃣"},
            ]
            if category:
                sample = [s for s in sample if s["category"] == category]
            return {"items": sample}
        query = {"category": category} if category else {}
        items = get_documents("item", query)
        # Convert ObjectId to str
        for it in items:
            it["_id"] = str(it.get("_id"))
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quiz")
def generate_quiz(category: str):
    """Generate a simple 4-option quiz from items in a category."""
    try:
        base_items: List[Dict[str, Any]] = []
        if db is not None:
            base_items = get_documents("item", {"category": category})
        if not base_items:
            # fallback small pool
            base_items = [
                {"category": "colors", "key": "red", "label": "Red", "display": "🟥"},
                {"category": "colors", "key": "blue", "label": "Blue", "display": "🟦"},
                {"category": "colors", "key": "green", "label": "Green", "display": "🟩"},
                {"category": "colors", "key": "yellow", "label": "Yellow", "display": "🟨"},
            ]
        correct = random.choice(base_items)
        wrongs = [i for i in base_items if i is not correct]
        random.shuffle(wrongs)
        options = [correct] + wrongs[:3]
        random.shuffle(options)
        return {
            "question": f"Select: {correct['label']}",
            "options": [{"label": o["label"], "display": o.get("display"), "key": o["key"]} for o in options],
            "answer": {"key": correct["key"]}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/progress")
def update_progress(update: ProgressUpdate):
    """Update or create progress for a device+category."""
    if db is None:
        # Non-persistent fallback
        return {"status": "ok", "message": "Progress stored in-memory-disabled env"}
    try:
        col = db["progress"]
        doc = col.find_one({"device_id": update.device_id, "category": update.category})
        if doc:
            new_points = doc.get("points", 0) + update.points
            new_correct = doc.get("correct", 0) + update.correct
            new_attempts = doc.get("attempts", 0) + update.attempts
            badges = set(doc.get("badges", []))
            if update.badge:
                badges.add(update.badge)
            col.update_one(
                {"_id": doc["_id"]},
                {"$set": {"points": new_points, "correct": new_correct, "attempts": new_attempts, "badges": list(badges)}}
            )
        else:
            payload = update.model_dump()
            payload["badges"] = [update.badge] if update.badge else []
            create_document("progress", payload)
        doc = col.find_one({"device_id": update.device_id, "category": update.category})
        doc["_id"] = str(doc["_id"])  # type: ignore
        return {"status": "ok", "progress": doc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/progress")
def get_progress(device_id: str, category: Optional[str] = None):
    if db is None:
        return {"progress": []}
    query: Dict[str, Any] = {"device_id": device_id}
    if category:
        query["category"] = category
    docs = get_documents("progress", query)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return {"progress": docs}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
