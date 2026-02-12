# PDF a Audiolibro - API
# Convierte PDFs en audiolibros usando OCR y TTS

import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional

import pdfplumber
import edge_tts
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydub import AudioSegment

app = FastAPI(title="PDF a Audiolibro", version="1.0.0")

# Directorios - usar /tmp en serverless
UPLOAD_DIR = Path("/tmp/uploads")
AUDIO_DIR = Path("/tmp/audio_output")
TEMP_DIR = Path("/tmp/temp_chunks")

UPLOAD_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Templates y static - ajustar paths para Vercel
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Voces disponibles en edge-tts (español latinoamericano y castellano)
VOICES = {
    "es-MX-JorgeNeural": "🇲🇽 Jorge (Masculino - Latinoamérica)",
    "es-MX-DaliaNeural": "🇲🇽 Dalia (Femenino - Latinoamérica)",
    "es-ES-AlvaroNeural": "🇪🇸 Álvaro (Masculino - España)",
    "es-ES-ElviraNeural": "🇪🇸 Elvira (Femenino - España)",
    "es-AR-TomasNeural": "🇦🇷 Tomás (Masculino - Argentina)",
    "es-AR-ElenaNeural": "🇦🇷 Elena (Femenino - Argentina)",
}


def extract_text_with_ocr(pdf_path: Path) -> str:
    """Extrae texto de un PDF escaneado usando OCR con pytesseract."""
    text_parts = []
    try:
        # Convertir PDF a imágenes
        images = convert_from_path(str(pdf_path), dpi=200)
        
        for page_num, image in enumerate(images, 1):
            # Extraer texto de la imagen usando OCR
            page_text = pytesseract.image_to_string(image, lang='spa')
            if page_text.strip():
                text_parts.append(f"\n--- Página {page_num} ---\n{page_text}")
        
        return "\n".join(text_parts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en OCR: {str(e)}")


def extract_text_from_pdf(pdf_path: Path, use_ocr: bool = False) -> str:
    """Extrae texto de un PDF usando pdfplumber o OCR según el caso."""
    text_parts = []
    
    # Si se fuerza OCR, saltar pdfplumber
    if not use_ocr:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"\n--- Página {page_num} ---\n{page_text}")
            
            # Si pdfplumber extrajo texto suficiente, usar ese
            full_text = "\n".join(text_parts)
            if len(full_text.strip()) > 100:
                return full_text
        except Exception as e:
            pass  # Si falla, intentar OCR
    
    # Usar OCR (para PDFs escaneados o si pdfplumber no resultó)
    return extract_text_with_ocr(pdf_path)


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
async def upload_pdf(file: UploadFile = File(...), use_ocr: bool = False):
    """Recibe el PDF y extrae el texto. Si use_ocr=True, fuerza OCR."""
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
    
    # Extraer texto (con fallback automático a OCR si no se encuentra texto)
    text = extract_text_from_pdf(pdf_path, use_ocr=use_ocr)
    
    # Detectar si se usó OCR
    extraction_method = "OCR" if use_ocr else "auto"
    
    if not text.strip():
        pdf_path.unlink()
        raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF. Verifica que el PDF no esté corrupto o protegido.")
    
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
        "status": "text_extracted",
        "extraction_method": extraction_method
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
