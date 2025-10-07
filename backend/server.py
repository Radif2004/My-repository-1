# backend/server.py
import os
import traceback
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
import fitz  # PyMuPDF
import openai

# Load env
load_dotenv()

# Config
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("DB_NAME", "resource_app")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # may be empty in offline mode
COPILOT_API_KEY = os.environ.get("COPILOT_API_KEY", "resource-app-copilot-key-2024")

# Setup DB + OpenAI
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

app = FastAPI(title="Resource App Backend")

# CORS - restrict in production to your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Security dependency
# -------------------------
def require_api_key(request: Request):
    api_key = request.headers.get("X-API-Key")
    if api_key != COPILOT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True

# -------------------------
# Pydantic models
# -------------------------
class NoteIn(BaseModel):
    title: str
    content: str

class ScheduleIn(BaseModel):
    title: str
    description: str
    scheduled_time: str  # ISO datetime string
    notification_type: str

class CommandIn(BaseModel):
    command: str
    context: Optional[dict] = None

# -------------------------
# Utility helpers
# -------------------------
def to_id_str(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc

def safe_objectid(id_str):
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id format")

# -------------------------
# Health / connectivity
# -------------------------
@app.get("/api/connection-status")
async def connection_status():
    # Basic check; could expand to test DB connectivity
    try:
        # quick lightweight DB ping
        client.admin.command('ping')
        db_ok = True
    except Exception:
        db_ok = False
    return {"has_internet": True, "db_ok": db_ok, "time": datetime.utcnow().isoformat()}

# -------------------------
# Notes endpoints
# -------------------------
@app.post("/api/notes")
async def create_note(note: NoteIn, authorized: bool = Depends(require_api_key)):
    note_doc = note.dict()
    note_doc["created_at"] = datetime.utcnow().isoformat()
    # Offline summarization: simple truncation / excerpt for now
    excerpt = note_doc["content"][:400]
    note_doc["offline_summary"] = excerpt
    # Try AI online summary if key present
    online_summary = None
    has_internet = False
    if OPENAI_API_KEY:
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user", "content": f"Summarize the following note:\n\n{note_doc['content']}"}],
                max_tokens=300,
                temperature=0.2,
            )
            online_summary = resp["choices"][0]["message"]["content"].strip()
            has_internet = True
        except Exception:
            online_summary = None
    note_doc["online_summary"] = online_summary
    note_doc["has_internet"] = has_internet
    result = db.notes.insert_one(note_doc)
    return {"id": str(result.inserted_id), **note_doc}

@app.get("/api/notes")
async def get_notes(authorized: bool = Depends(require_api_key)):
    docs = list(db.notes.find({}, {"title":1,"content":1,"offline_summary":1,"online_summary":1,"created_at":1}))
    for d in docs:
        to_id_str(d)
    return docs

@app.get("/api/notes/{note_id}")
async def get_note_by_id(note_id: str, authorized: bool = Depends(require_api_key)):
    oid = safe_objectid(note_id)
    doc = db.notes.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Note not found")
    to_id_str(doc)
    return doc

@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: str, authorized: bool = Depends(require_api_key)):
    oid = safe_objectid(note_id)
    result = db.notes.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"id": note_id, "deleted": True}

# -------------------------
# Schedule endpoints
# -------------------------
@app.post("/api/schedule")
async def create_schedule(schedule: ScheduleIn, authorized: bool = Depends(require_api_key)):
    doc = schedule.dict()
    # store scheduled_time as ISO string and also created_at
    doc["created_at"] = datetime.utcnow().isoformat()
    doc["is_completed"] = False
    result = db.schedules.insert_one(doc)
    return {"id": str(result.inserted_id), **doc}

@app.get("/api/schedule")
async def get_schedule(authorized: bool = Depends(require_api_key)):
    docs = list(db.schedules.find({}, {"title":1,"description":1,"scheduled_time":1,"notification_type":1,"is_completed":1}))
    for d in docs:
        to_id_str(d)
    return docs

@app.get("/api/schedule/upcoming")
async def get_upcoming_schedules(authorized: bool = Depends(require_api_key)):
    now = datetime.utcnow()
    # find schedules with scheduled_time >= now
    docs = list(db.schedules.find({ "scheduled_time": {"$gte": now.isoformat()} }))
    for d in docs:
        to_id_str(d)
    return docs

@app.put("/api/schedule/{schedule_id}/complete")
async def complete_schedule(schedule_id: str, authorized: bool = Depends(require_api_key)):
    oid = safe_objectid(schedule_id)
    result = db.schedules.update_one({"_id": oid}, {"$set": {"is_completed": True}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"id": schedule_id, "message": "Schedule marked complete"}

# -------------------------
# PDF upload & summaries
# -------------------------
@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), authorized: bool = Depends(require_api_key)):
    try:
        contents = await file.read()
        doc = fitz.open(stream=contents, filetype="pdf")
        text_pages = [page.get_text() for page in doc]
        text = "\n".join(text_pages).strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {str(e)}")

    offline_summary = text[:500] + ("..." if len(text) > 500 else "")
    text_length = len(text)
    has_internet = False
    online_summary = None

    if OPENAI_API_KEY:
        try:
            sample_text = text[:2000] if len(text) > 2000 else text
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":f"Summarize the following document:\n\n{sample_text}"}],
                max_tokens=400,
                temperature=0.2,
            )
            online_summary = resp["choices"][0]["message"]["content"].strip()
            has_internet = True
        except Exception:
            online_summary = None

    summary_doc = {
        "filename": file.filename,
        "offline_summary": offline_summary,
        "online_summary": online_summary,
        "text_length": text_length,
        "has_internet": has_internet,
        "status": "processed",
        "created_at": datetime.utcnow().isoformat()
    }
    result = db.summaries.insert_one(summary_doc)
    return {"id": str(result.inserted_id), **summary_doc}

@app.get("/api/summaries")
async def get_summaries(authorized: bool = Depends(require_api_key)):
    docs = list(db.summaries.find({}, {"filename":1,"offline_summary":1,"online_summary":1,"text_length":1,"created_at":1}))
    for d in docs:
        to_id_str(d)
    return docs

@app.post("/api/refresh-summary/{summary_id}")
async def refresh_summary(summary_id: str, authorized: bool = Depends(require_api_key)):
    oid = safe_objectid(summary_id)
    doc = db.summaries.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Summary not found")

    if OPENAI_API_KEY:
        try:
            text = (doc.get("offline_summary") or "")[:2000]
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":f"Create an improved summary:\n\n{text}"}],
                max_tokens=400,
                temperature=0.2,
            )
            new_online = resp["choices"][0]["message"]["content"].strip()
            db.summaries.update_one({"_id": oid}, {"$set": {"online_summary": new_online, "has_internet": True}})
            return {"id": summary_id, "summary": new_online}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI refresh failed: {str(e)}")
    else:
        raise HTTPException(status_code=503, detail="No online AI key configured")

# -------------------------
# Copilot command processor
# -------------------------
@app.post("/api/copilot/process-command")
async def process_command(body: CommandIn, authorized: bool = Depends(require_api_key)):
    cmd = body.command.strip().lower()

    # Basic dispatcher - return an action + message + optional data
    if "note" in cmd:
        return {"action": "create_note", "message": "I can create a note for you. What is the title and content?", "data": {}}
    if "pdf" in cmd or "summarize" in cmd:
        return {"action": "upload_pdf", "message": "Upload the PDF you'd like summarized.", "data": {}}
    if "schedule" in cmd or "reminder" in cmd:
        return {"action": "create_schedule", "message": "When should I schedule your reminder?", "data": {}}
    if "summaries" in cmd or "show me" in cmd:
        return {"action": "get_summaries", "message": "Here are your summaries.", "data": {}}

    return {"action": "unknown", "message": f"Command not recognized: {body.command}", "data": {}}
