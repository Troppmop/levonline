import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}


async def save_damage_report_photo(report_id: uuid.UUID, upload: UploadFile) -> str:
    """Persists an uploaded photo to local disk under UPLOAD_DIR and returns
    a URL path servable via the /uploads static mount.

    MVP uses local disk (backed by a Railway volume); swapping to S3-style
    object storage later only requires changing this function.
    """
    if upload.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload.content_type}")

    contents = await upload.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    target_dir = Path(settings.UPLOAD_DIR) / "damage-reports" / str(report_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(upload.filename or "").suffix or ".jpg"
    filename = f"{uuid.uuid4()}{extension}"
    target_path = target_dir / filename
    target_path.write_bytes(contents)

    return f"/uploads/damage-reports/{report_id}/{filename}"


async def save_avatar_photo(user_id: uuid.UUID, upload: UploadFile) -> str:
    """Persists a profile picture, overwriting any previous one for that
    user (old files under their folder are left behind — same minor,
    accepted tradeoff as damage report photos; not worth a cleanup pass
    for an MVP with local-disk storage)."""
    if upload.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload.content_type}")

    contents = await upload.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    target_dir = Path(settings.UPLOAD_DIR) / "avatars" / str(user_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(upload.filename or "").suffix or ".jpg"
    filename = f"{uuid.uuid4()}{extension}"
    target_path = target_dir / filename
    target_path.write_bytes(contents)

    return f"/uploads/avatars/{user_id}/{filename}"
