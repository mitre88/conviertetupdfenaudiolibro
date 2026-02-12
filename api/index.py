from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import pdfplumber
import edge_tts
import uuid
import os

app = FastAPI(title="PDF a Audiolibro", version="3.0.0-vercel")

# Directorios
UPLOAD_DIR = Path("/tmp/uploads")
AUDIO_DIR = Path("/tmp/audio")

for d in [UPLOAD_DIR, AUDIO_DIR]:
    d.mkdir(exist_ok=True, parents=True)

# Templates
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

VOICES = {
    "es-MX-JorgeNeural": "Jorge (MX)",
    "es-MX-DaliaNeural": "Dalia (MX)",
    "es-ES-AlvaroNeural": "Álvaro (ES)",
    "es-ES-ElviraNeural": "Elvira (ES)",
    "es-AR-TomasNeural": "Tomás (AR)",
    "es-AR-ElenaNeural": "Elena (AR)",
}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "voices": VOICES})

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo PDFs")
    
    job_id = uuid.uuid4().hex[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}.pdf"
    
    content = await file.read()
    with open(pdf_path, "wb") as f:
        f.write(content)
    
    # Extraer texto
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            txt = page.extract_text()
            if txt:
                text_parts.append(txt)
    
    text = "\n\n".join(text_parts)
    
    if not text.strip():
        pdf_path.unlink()
        raise HTTPException(status_code=400, detail="No se encontró texto. Usa un PDF con texto seleccionable.")
    
    # Guardar texto
    text_path = UPLOAD_DIR / f"{job_id}.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
    
    # Limitar para Vercel - 5000 chars max (un solo chunk de TTS)
    if len(text) > 5000:
        text = text[:5000]
        truncated = True
    else:
        truncated = False
    
    return JSONResponse({
        "job_id": job_id,
        "filename": file.filename,
        "preview": text[:300] + "..." if len(text) > 300 else text,
        "total_chars": len(text),
        "truncated": truncated
    })

@app.post("/convert")
async def convert_to_audio(data: dict):
    job_id = data.get("job_id")
    voice = data.get("voice", "es-MX-JorgeNeural")
    
    text_path = UPLOAD_DIR / f"{job_id}.txt"
    if not text_path.exists():
        raise HTTPException(status_code=404, detail="No encontrado")
    
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Limitar a 5000 chars (un solo chunk para Vercel)
    text = text[:5000]
    
    # Generar audio
    output_path = AUDIO_DIR / f"{job_id}.mp3"
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
    
    # Limpiar
    pdf_path = UPLOAD_DIR / f"{job_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()
    
    return JSONResponse({
        "job_id": job_id,
        "audio_url": f"/download/{job_id}",
        "status": "completed"
    })

@app.get("/download/{job_id}")
async def download_audio(job_id: str):
    audio_path = AUDIO_DIR / f"{job_id}.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="No encontrado")
    
    return FileResponse(
        path=audio_path,
        filename=f"audiolibro_{job_id}.mp3",
        media_type="audio/mpeg"
    )

# Handler for Vercel
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    handler = app
