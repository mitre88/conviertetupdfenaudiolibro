"""
PDF a Audiolibro - API
Convierte PDFs en audiolibros usando OCR y TTS
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional

import pdfplumber
import edge_tts
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydub import AudioSegment

app = FastAPI(title="PDF a Audiolibro", version="1.0.0")

# Directorios
UPLOAD_DIR = Path("uploads")
AUDIO_DIR = Path("audio_output")
TEMP_DIR = Path("temp_chunks")

UPLOAD_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Templates y static
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Voces disponibles en edge-tts (español latinoamericano y castellano)
VOICES = {
    "es-MX-JorgeNeural": "🇲🇽 Jorge (Masculino - Latinoamérica)",
    "es-MX-DaliaNeural": "🇲🇽 Dalia (Femenino - Latinoamérica)",
    "es-ES-AlvaroNeural": "🇪🇸 Álvaro (Masculino - España)",
    "es-ES-ElviraNeural": "🇪🇸 Elvira (Femenino - España)",
    "es-AR-TomasNeural": "🇦🇷 Tomás (Masculino - Argentina)",
    "es-AR-ElenaNeural": "🇦🇷 Elena (Femenino - Argentina)",
}


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extrae texto de un PDF usando pdfplumber."""
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
    # Dividir texto en chunks para no sobrecargar la API
    max_chars = 4000
    chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
    
    temp_files = []
    
    for idx, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        
        temp_file = TEMP_DIR / f"chunk_{uuid.uuid4().hex}.mp3"
        temp_files.append(temp_file)
        
        communicate = edge_tts.Communicate(chunk, voice)
        await communicate.save(str(temp_file))
    
    # Unir todos los chunks en un solo archivo
    if temp_files:
        combined = AudioSegment.empty()
        for temp_file in temp_files:
            segment = AudioSegment.from_mp3(temp_file)
            combined += segment
            temp_file.unlink()  # Eliminar archivo temporal
        
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
    
    # Generar ID único
    job_id = uuid.uuid4().hex[:12]
    pdf_path = UPLOAD_DIR / f"{job_id}.pdf"
    
    # Guardar archivo
    try:
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")
    
    # Extraer texto
    text = extract_text_from_pdf(pdf_path)
    
    if not text.strip():
        pdf_path.unlink()
        raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF. ¿Es un PDF escaneado? Prueba con un PDF que tenga texto seleccionable.")
    
    # Guardar texto para referencia
    text_path = UPLOAD_DIR / f"{job_id}.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
    
    # Calcular preview (primeros 500 caracteres)
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
    
    # Leer texto
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Generar audio
    output_path = AUDIO_DIR / f"{job_id}.mp3"
    
    try:
        await text_to_speech(text, voice, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando audio: {str(e)}")
    
    # Eliminar archivos temporales
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


@app.get("/preview/{job_id}")
async def get_preview(job_id: str, limit: int = 1000):
    """Obtiene un preview del texto extraído."""
    text_path = UPLOAD_DIR / f"{job_id}.txt"
    
    if not text_path.exists():
        raise HTTPException(status_code=404, detail="Texto no encontrado")
    
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    preview = text[:limit]
    remaining = len(text) - limit
    
    return JSONResponse({
        "preview": preview,
        "remaining": remaining if remaining > 0 else 0,
        "total": len(text)
    })


@app.on_event("startup")
async def cleanup_old_files():
    """Limpia archivos temporales al iniciar."""
    for dir_path in [UPLOAD_DIR, AUDIO_DIR, TEMP_DIR]:
        for file in dir_path.glob("*"):
            try:
                file.unlink()
            except:
                pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
