# 📚 PDF a Audiolibro

Aplicación web que convierte PDFs en audiolibros usando OCR y texto a voz (TTS).

## Features

- 📄 **Upload de PDFs** - Arrastra y suelta archivos PDF
- 🔍 **Extracción de texto** - Extrae texto directamente de PDFs con texto seleccionable
- 🎙️ **Múltiples voces** - Voces en español latinoamericano y castellano
- 🎧 **Audiolibro MP3** - Genera archivo de audio listo para reproducir
- 📱 **UI Minimalista** - Interfaz limpia y fácil de usar

## Stack Tecnológico

- **Backend**: FastAPI (Python)
- **OCR**: pdfplumber
- **TTS**: edge-tts (Microsoft Edge TTS - gratuito)
- **Frontend**: HTML + Tailwind CSS

## Instalación

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
2. Arrastra un PDF al área de upload (debe tener texto seleccionable)
3. Selecciona la voz que prefieras
4. Revisa el preview del texto extraído
5. Haz clic en "Crear Audiolibro"
6. Descarga tu MP3 cuando termine

## Notas

- Funciona mejor con PDFs que tienen texto seleccionable (no escaneados)
- Para PDFs escaneados, se necesitaría integrar pytesseract + OCR adicional
- El audio se genera usando edge-tts (gratuito, no requiere API key)
- Los archivos temporales se limpian automáticamente

## Licencia

MIT
