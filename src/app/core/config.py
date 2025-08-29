import os
from pydantic import BaseModel

class Settings(BaseModel):
    STORAGE_UPLOADS: str = os.getenv("STORAGE_UPLOADS", ".storage/uploads")
    STORAGE_EXPORTS: str = os.getenv("STORAGE_EXPORTS", "./storage/exports")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")

    
settings = Settings()

os.makedirs(settings.STORAGE_UPLOADS, exist_ok=True)
os.makedirs(settings.STORAGE_EXPORTS, exist_ok=True)