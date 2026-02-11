# 📚 PDF a Audiolibro

Aplicación web que convierte PDFs en audiolibros usando OCR y texto a voz (TTS).

## Features

- 📄 **Upload de PDFs** - Arrastra y suelta archivos PDF
- 🔍 **Extracción de texto** - Extrae texto de PDFs con texto seleccionable
- 🔎 **OCR para escaneados** - Extracción automática de texto de PDFs escaneados
- 🎙️ **Múltiples voces** - Voces en español latinoamericano y castellano
- 🎧 **Audiolibro MP3** - Genera archivo de audio listo para reproducir
- 📱 **UI Minimalista** - Interfaz limpia y fácil de usar

## Stack Tecnológico

- **Backend**: FastAPI (Python)
- **Extracción de texto**: pdfplumber (para PDFs con texto seleccionable)
- **OCR**: pytesseract + pdf2image (para PDFs escaneados)
- **TTS**: edge-tts (Microsoft Edge TTS - gratuito)
- **Frontend**: HTML + Tailwind CSS

## Instalación

### Requisitos del Sistema

Para OCR (PDFs escaneados), necesitas instalar:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa poppler-utils
```

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
```

**Windows:**
- Descarga e instala Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Descarga poppler: https://github.com/oschwartz10612/poppler-windows/releases

### Instalación de Python

```bash
# 1. Clonar el repositorio
cd conviertetupdfenaudiolibro

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar
python main.py
```

La app estará disponible en: `http://localhost:8000`

## Uso

1. Abre `http://localhost:8000` en tu navegador
2. Arrastra un PDF al área de upload
   - PDFs con texto seleccionable: se procesan automáticamente
   - PDFs escaneados: se usa OCR automáticamente si no se detecta texto
   - Para PDFs escaneados de baja calidad, activa "Forzar OCR"
3. Selecciona la voz que prefieras
4. Revisa el preview del texto extraído
5. Haz clic en "Crear Audiolibro"
6. Descarga tu MP3 cuando termine

## Notas

- **PDFs con texto**: Usan pdfplumber (rápido y preciso)
- **PDFs escaneados**: Usan pytesseract + OCR automáticamente
- **Calidad de OCR**: Depende de la resolución del PDF. Si el texto es pobre, prueba con "Forzar OCR"
- El audio se genera usando edge-tts (gratuito, no requiere API key)
- Los archivos temporales se limpian automáticamente

## Licencia

MIT
