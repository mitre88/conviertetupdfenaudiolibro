# 📚 PDF a Audiolibro (Versión Lite para Vercel)

Aplicación web que convierte PDFs con **texto seleccionable** en audiolibros usando texto a voz (TTS).

> ⚠️ **Nota**: Esta es la versión Lite optimizada para Vercel. Solo funciona con PDFs que tienen texto seleccionable (no escaneados). Para OCR de PDFs escaneados, usa la versión completa con Docker o Railway.

## Features

- 📄 **Upload de PDFs** - Arrastra y suelta archivos PDF
- 🔍 **Extracción de texto** - Extrae texto de PDFs con texto seleccionable
- 🎙️ **Múltiples voces** - Voces en español latinoamericano y castellano
- 🎧 **Audiolibro MP3** - Genera archivo de audio listo para reproducir
- 📱 **UI Minimalista** - Interfaz limpia y fácil de usar

## Stack Tecnológico

- **Backend**: FastAPI (Python)
- **Extracción de texto**: pdfplumber
- **TTS**: edge-tts (Microsoft Edge TTS - gratuito)
- **Frontend**: HTML + Tailwind CSS

## Deploy en Vercel

1. Ve a https://vercel.com/new
2. Importa este repositorio
3. En **Framework Preset** selecciona `Other`
4. En **Root Directory** déjalo en `/`
5. Deploy

## Limitaciones de Vercel (Hobby)

- **Timeout**: 10 segundos - máximo ~15,000 caracteres (~5-6 páginas)
- **Sin OCR**: Los PDFs escaneados no son compatibles
- **Archivos temporales**: Se almacenan en `/tmp`

## Uso Local

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
python api/index.py
```

La app estará disponible en: `http://localhost:8000`

## Notas

- Funciona solo con PDFs que tienen texto seleccionable
- Los PDFs escaneados requieren OCR (versión completa en Railway/Docker)
- El audio se genera usando edge-tts (gratuito, no requiere API key)

## Licencia

MIT
