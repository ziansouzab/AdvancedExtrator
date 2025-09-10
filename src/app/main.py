import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.core.config import settings
from app.models.schemas import ExtractResponse, Lancamento
from app.services.extractor_service import extract_from_pdf_path
from app.utils.files import gen_filename, safe_paths, is_pdf

app = FastAPI(title="Advanced Extrator", version="1.0.0")

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/extract", response_model=ExtractResponse)
def extract_pdf(bank_code = Form(...), file: UploadFile = File(...), save_xlsx = Form(True)):
    if not is_pdf(file.content_type, file.filename):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF válido.")

    # Limite simples de tamanho (ex.: 20MB)
    raw = file.file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (limite 20MB).")

    # Persiste upload
    pdf_name = gen_filename(".pdf")
    pdf_path = safe_paths(settings.STORAGE_UPLOADS, pdf_name)
    with open(pdf_path, "wb") as f:
        f.write(raw)

    lancamentos, xlsx_filename, totals = extract_from_pdf_path(bank_code, pdf_path, make_xlsx=save_xlsx)

    if xlsx_filename:
        download_url = f"/api/v1/files/{xlsx_filename}"
    else:
        None

    return ExtractResponse(
        total_lancamentos=len(lancamentos),
        total_debitos=totals["total_debitos"],
        total_creditos=totals["total_creditos"],
        saldo_liquido=totals["saldo_liquido"],
        download_url=download_url,
    )

@app.get("/api/v1/files/{filename}")
def download_file(filename: str):
    fullpath = os.path.join(settings.STORAGE_EXPORTS, os.path.basename(filename))
    if not os.path.exists(fullpath):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(fullpath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)