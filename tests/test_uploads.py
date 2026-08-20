import io
import os
import pytest
from fastapi import HTTPException, UploadFile
from src.api.uploads import save_upload, UPLOAD_DIR

def make_upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=filename)

@pytest.mark.asyncio
async def test_save_upload_rejects_non_pdf():
    upload = make_upload("notes.txt", b"hello")
    with pytest.raises(HTTPException) as exc:
        await save_upload(upload)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_save_upload_rejects_empty_file():
    upload = make_upload("empty.pdf", b"")
    with pytest.raises(HTTPException) as exc:
        await save_upload(upload)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_save_upload_rejects_oversized_file():
    upload = make_upload("big.pdf", b"x" * (25 * 1024 * 1024 + 1))
    with pytest.raises(HTTPException) as exc:
        await save_upload(upload)
    assert exc.value.status_code == 413

@pytest.mark.asyncio
async def test_save_upload_sanitizes_and_saves():
    upload = make_upload("../../evil name!.pdf", b"%PDF-1.4 fake content")
    disk_path, original_name = await save_upload(upload)
    try:
        assert original_name == "../../evil name!.pdf"
        assert os.path.dirname(disk_path) == UPLOAD_DIR
        assert os.path.exists(disk_path)
        assert ".." not in os.path.basename(disk_path)
        assert " " not in os.path.basename(disk_path)
    finally:
        os.remove(disk_path)
