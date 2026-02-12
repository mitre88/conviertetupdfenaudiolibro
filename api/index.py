from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import pdfplumber
import edge_tts
from pydub import AudioSegment
import uuid

app = FastAPI(title="PDF a Audiolibro", version="2.0.0-lite")

# Directorios
UPLOAD_DIR = Path("/tmp/uploads")
AUDIO_DIR = Path("/tmp/audio_output") 
TEMP_DIR = Path("/tmp/temp_chunks")

for d in [UPLOAD_DIR, AUDIO_DIR, TEMP_DIR]:
    d.mkdir(exist_ok=True, parents=True)

# Templates - path absoluto
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

VOICES = {
    "es-MX-JorgeNeural": "Jorge",
    "es-MX-DaliaNeural": "Dalia",
    "es-ES-AlvaroNeural": "Álvaro",
    "es-ES-ElviraNeural": "Elvira",
    "es-AR-TomasNeural": "Tomás",
    "es-AR-ElenaNeural": "Elena",
}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "voices": VOICES})

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo PDFs")
    
    job_id = uuid.uuid4().hex[:12]
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
                text_parts.append(f"\n--- Página {i} ---\n{txt}")
    
    text = "\n".join(text_parts)
    
    if not text.strip():
        pdf_path.unlink()
        raise HTTPException(status_code=400, detail="No se encontró texto. Usa un PDF con texto seleccionable.")
    
    # Guardar texto
    text_path = UPLOAD_DIR / f"{job_id}.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
    
    # Limitar para Vercel
    if len(text) > 10000:
        raise HTTPException(status_code=400, detail="PDF muy largo. Máx ~10,000 caracteres.")
    
    return JSONResponse({
        "job_id": job_id,
        "filename": file.filename,
        "preview": text[:400] + "..." if len(text) > 400 else text,
        "total_chars": len(text)
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
    
    # Generar audio por chunks
    output_path = AUDIO_DIR / f"{job_id}.mp3"
    chunks = [text[i:i+3000] for i in range(0, len(text), 3000)]
    temp_files = []
    
    for chunk in chunks:
        if not chunk.strip():
            continue
        temp = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"
        temp_files.append(temp)
        communicate = edge_tts.Communicate(chunk, voice)
        await communicate.save(str(temp))
    
    # Unir
    combined = AudioSegment.empty()
    for f in temp_files:
        combined += AudioSegment.from_mp3(str(f))
        f.unlink()
    
    combined.export(str(output_path), format="mp3")
    
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
import asyncio

# Vercel requires a handler function
def handler(request, context):
    return app

# Alternative for ASGI
from mangum import Adapter

# If mangum is available, use it
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    # Fallback - standard handler
    pass
