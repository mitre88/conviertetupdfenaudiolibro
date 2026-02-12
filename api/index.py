# PDF a Audiolibro - API (Versión Lite para Vercel)
# Solo PDFs con texto seleccionable - Sin OCR

import os
import uuid
import asyncio
from pathlib import Path

import pdfplumber
import edge_tts
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydub import AudioSegment

app = FastAPI(title="PDF a Audiolibro", version="2.0.0-lite")

# Directorios - usar /tmp en serverless
UPLOAD_DIR = Path("/tmp/uploads")
AUDIO_DIR = Path("/tmp/audio_output")
TEMP_DIR = Path("/tmp/temp_chunks")

UPLOAD_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Templates
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Voces disponibles
VOICES = {
    "es-MX-JorgeNeural": "🇲🇽 Jorge (Masculino - Latinoamérica)",
    "es-MX-DaliaNeural": "🇲🇽 Dalia (Femenino - Latinoamérica)",
    "es-ES-AlvaroNeural": "🇪🇸 Álvaro (Masculino - España)",
    "es-ES-ElviraNeural": "🇪🇸 Elvira (Femenino - España)",
    "es-AR-TomasNeural": "🇦🇷 Tomás (Masculino - Argentina)",
    "es-AR-ElenaNeural": "🇦🇷 Elena (Femenino - Argentina)",
}


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extrae texto de un PDF usando pdfplumber (solo texto seleccionable)."""
    text_parts = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"\n--- Página {page_num} ---\n{page_text}")
        
        return "\n".join(text_parts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo texto: {str(e)}")


async def text_to_speech(text: str, voice: str, output_path: Path) -> None:
    """Convierte texto a audio usando edge-tts."""
    max_chars = 4000
    chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
    temp_files = []
    
    for chunk in chunks:
        if not chunk.strip():
            continue
        
        temp_file = TEMP_DIR / f"chunk_{uuid.uuid4().hex}.mp3"
        temp_files.append(temp_file)
        
        communicate = edge_tts.Communicate(chunk, voice)
        await communicate.save(str(temp_file))
    
    if temp_files:
        combined = AudioSegment.empty()
        for temp_file in temp_files:
            segment = AudioSegment.from_mp3(temp_file)
            combined += segment
            temp_file.unlink()
        
        combined.export(str(output_path), format="mp3", bitrate="128k")
    else:
        raise HTTPException(status_code=500, detail="No se pudo generar audio")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Página principal."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "voices": VOICES
    })


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Recibe el PDF y extrae el texto."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
    
    job_id = uuid.uuid4().hex[:12]
    pdf_path = UPLOAD_DIR / f"{job_id}.pdf"
    
    try:
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")
    
    text = extract_text_from_pdf(pdf_path)
    
    if not text.strip():
        pdf_path.unlink()
        raise HTTPException(status_code=400, detail="No se encontró texto en el PDF. Este PDF parece estar escaneado o no tiene texto seleccionable. Usa un PDF con texto.")
    
    text_path = UPLOAD_DIR / f"{job_id}.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
    
    preview = text[:500] + "..." if len(text) > 500 else text
    
    return JSONResponse({
        "job_id": job_id,
        "filename": file.filename,
        "preview": preview,
        "total_chars": len(text),
        "status": "text_extracted"
    })


@app.post("/convert")
async def convert_to_audio(data: dict):
    """Convierte el texto extraído a audio."""
    job_id = data.get("job_id")
    voice = data.get("voice", "es-MX-JorgeNeural")
    
    if voice not in VOICES:
        raise HTTPException(status_code=400, detail="Voz no válida")
    
    text_path = UPLOAD_DIR / f"{job_id}.txt"
    if not text_path.exists():
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Limitar tamaño para Vercel (10s timeout en hobby)
    if len(text) > 15000:
        raise HTTPException(status_code=400, detail="El PDF es muy largo para procesarlo en Vercel. Máximo ~15,000 caracteres (~5-6 páginas).")
    
    output_path = AUDIO_DIR / f"{job_id}.mp3"
    
    try:
        await text_to_speech(text, voice, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando audio: {str(e)}")
    
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
    """Descarga el archivo de audio generado."""
    audio_path = AUDIO_DIR / f"{job_id}.mp3"
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio no encontrado")
    
    return FileResponse(
        path=audio_path,
        filename=f"audiolibro_{job_id}.mp3",
        media_type="audio/mpeg"
    )
