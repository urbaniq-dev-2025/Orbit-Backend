"""
Service for handling avatar uploads.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from PIL import Image
import io

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Allowed image formats
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DIMENSION = 2000  # Max width/height in pixels


async def upload_avatar(file: UploadFile, user_id: uuid.UUID) -> str:
    """
    Upload and process avatar image.
    
    Returns:
        URL/path to the uploaded avatar
    """
    settings = get_settings()
    
    # Validate file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB")
    
    # Validate and process image
    try:
        image = Image.open(io.BytesIO(content))
        
        # Convert RGBA to RGB if necessary
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        
        # Resize if too large
        if image.width > MAX_DIMENSION or image.height > MAX_DIMENSION:
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
        
        # Generate filename
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}.jpg"
        
        # Save image (for now, save locally - can be extended to S3/Cloudinary)
        upload_dir = Path(settings.upload_dir or "uploads/avatars")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / filename
        image.save(file_path, "JPEG", quality=85, optimize=True)
        
        # Return URL (adjust based on your storage solution)
        # For local storage, return relative path
        # For S3/Cloudinary, return full URL
        avatar_url = f"/uploads/avatars/{filename}"
        
        logger.info(f"Avatar uploaded for user {user_id}: {avatar_url}")
        return avatar_url
        
    except Exception as e:
        logger.error(f"Failed to process avatar image: {e}")
        raise ValueError(f"Invalid image file: {str(e)}") from e
