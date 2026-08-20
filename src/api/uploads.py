import os
import re
import uuid
from fastapi import HTTPException, UploadFile

UPLOAD_DIR = os.path.join("data", "pdfs")
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

def _sanitize_filename(original: str) -> str:
    base = os.path.basename(original or "document.pdf")
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return base or "document.pdf"

async def save_upload(file: UploadFile) -> tuple[str, str]:
    original_name = file.filename or "document.pdf"
    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 25MB limit")
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    disk_name = f"{uuid.uuid4().hex[:8]}_{_sanitize_filename(original_name)}"
    disk_path = os.path.join(UPLOAD_DIR, disk_name)
    with open(disk_path, "wb") as f:
        f.write(contents)

    return disk_path, original_name
