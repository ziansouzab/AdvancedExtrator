import os
import uuid
from typing import Tuple

def gen_filename(suffix: str) -> str:
    return f"{uuid.uuid4().hex}{suffix}"

def safe_paths(base_dir: str, filename: str) -> str:
    filename = os.path.basename(filename)
    return os.path.join(base_dir, filename)

def is_pdf(content_type: str, filename: str) -> bool:
    return (content_type in ("application/pdf", "application/octet-stream")) and filename.lower().endswith(".pdf")