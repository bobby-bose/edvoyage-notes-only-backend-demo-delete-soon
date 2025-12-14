# Django ↔ BOBI Integration - Quick Start Guide

## Overview

You now have a complete integration between:
- **Django** (Flashcard model) - Receives PDF uploads
- **BOBI Flask Service** (PDF processor) - Converts PDFs to images + watermark

When you upload a PDF in Django Admin, it:
1. Saves the PDF to disk
2. Sends it to BOBI service via HTTP
3. Receives Base64-encoded images
4. Creates `FlashcardImage` records in database

---

## ✅ What Was Implemented

### 1. **Enhanced BOBI Flask App** (`bobi/app.py`)
✓ Original web UI endpoints (/, /progress, /result)  
✓ New `/api/process` endpoint for Django integration  
✓ `/api/health` endpoint for health checks  
✓ Base64 image encoding in response  
✓ Comprehensive error handling  
✓ Logging for debugging  

### 2. **Django Utils** (`notes/utils.py`)
✓ `send_pdf_to_bobi()` - sends PDF to BOBI service  
✓ `validate_bobi_service()` - health check  
✓ `create_flashcard_images_from_pages()` - creates images in DB  
✓ `process_flashcard_pdf_with_bobi()` - main orchestration  
✓ Custom exception classes for error handling  
✓ Extensive logging  

### 3. **Updated Flashcard Model** (`notes/models.py`)
✓ Changed from local PDF processing to BOBI service  
✓ New `_process_pdf_with_bobi()` method  
✓ Error handling with Django ValidationError  
✓ Atomic database transactions  

### 4. **Settings Configuration** (`BOBI_SETTINGS.md`)
✓ Environment-based configuration  
✓ Optional API key support  
✓ Configurable DPI and format  

### 5. **Test Suite** (`test_bobi_integration.py`)
✓ Health check test  
✓ API endpoint test  
✓ Django integration test  
✓ End-to-end test  

---

## 🚀 Quick Start (5 minutes)

### Step 1: Update Django Settings

Add to `project/settings.py`:

```python
import os

# BOBI Flask Service Configuration
BOBI_SERVICE_URL = os.getenv('BOBI_SERVICE_URL', 'http://localhost:5000')
BOBI_REQUEST_TIMEOUT = int(os.getenv('BOBI_REQUEST_TIMEOUT', '120'))
BOBI_DPI = int(os.getenv('BOBI_DPI', '200'))
BOBI_FORMAT = os.getenv('BOBI_FORMAT', 'png')
BOBI_API_KEY = os.getenv('BOBI_API_KEY', None)
```

### Step 2: Install Dependencies

BOBI Flask requirements (already in `bobi/requirements.txt`):
```bash
pip install flask pymupdf pillow PyPDF2 reportlab cairosvg
```

Django requirements (add if missing):
```bash
pip install requests
```

### Step 3: Create BOBI logo.svg

Create `bobi/logo.svg` (simple example):
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <rect width="200" height="200" fill="none" stroke="gray" stroke-width="2"/>
  <text x="100" y="100" font-size="16" text-anchor="middle" fill="gray">
    OFFICIAL USE ONLY
  </text>
</svg>
```

Or copy your own logo to `bobi/logo.svg`

### Step 4: Start BOBI Service

Terminal 1:
```bash
cd bobi
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

### Step 5: Start Django

Terminal 2:
```bash
python manage.py runserver
```

### Step 6: Test It!

1. Go to: http://localhost:8000/admin/notes/flashcard/
2. Click "Add Flashcard"
3. Select Category, Subject, Sub-subject
4. Upload a PDF file
5. Click "Save"
6. **Wait 3-7 seconds** for BOBI to process
7. **Scroll down** to see "FlashcardImage" inline with page previews ✓

---

## 🧪 Run Integration Tests

```bash
python test_bobi_integration.py
```

This tests:
- ✓ BOBI service is running
- ✓ API endpoints work
- ✓ Django can reach BOBI
- ✓ End-to-end PDF upload workflow

---

## 📊 Architecture Diagram

```
Django Admin                BOBI Flask
     │                           │
     ├─ User uploads PDF         │
     ├─ Flashcard.save()         │
     │  triggers                 │
     │                           │
     ├──────────── HTTP POST /api/process ────────────┐
     │  (multipart: pdf_file)                         │
     │                                                │
     │                      BOBI processes:           │
     │                      1. Extract pages          │
     │                      2. Convert to image       │
     │                      3. Apply watermark        │
     │                      4. Encode Base64          │
     │                                                │
     │  ◄─────── HTTP 200 JSON Response ──────────────┤
     │  {                                             │
     │    "status": "success",                        │
     │    "pages": [                                  │
     │      {                                         │
     │        "page_num": 1,                          │
     │        "image_base64": "iVBORw0...",           │
     │        "width": 1200,                          │
     │        "height": 1600                          │
     │      }                                         │
     │    ]                                           │
     │  }                                             │
     │                                                │
     ├─ Decode Base64                                 │
     ├─ Create FlashcardImage                         │
     ├─ Save to media/flashcards/                     │
     │                                                │
     └─ Flashcard.save() completes                    │
     
Django Admin shows image previews ✓
```

---

## 🔧 Troubleshooting

### Problem: "Cannot connect to BOBI service"
```
Error: [BOBI] Cannot connect to BOBI service at http://localhost:5000
```

**Solution:**
1. Make sure BOBI Flask is running: `python bobi/app.py`
2. Check BOBI_SERVICE_URL in settings.py matches
3. Test manually: `curl http://localhost:5000/api/health`

### Problem: "PDF processing timeout (120s exceeded)"
```
Error: Processing timeout
```

**Solution:**
1. Large PDF files take longer to process
2. Increase `BOBI_REQUEST_TIMEOUT` in settings:
   ```python
   BOBI_REQUEST_TIMEOUT = 300  # 5 minutes
   ```
3. Or reduce DPI for faster processing:
   ```python
   BOBI_DPI = 150  # Instead of 200
   ```

### Problem: "AttributeError: 'Flashcard' object has no attribute 'images'"
```
Error: RelationshipDoesNotExist: Flashcard has no attribute 'images'
```

**Solution:**
- Make sure you have the `FlashcardImage` model in `notes/models.py`
- Check that `FlashcardImage` has `related_name="images"`

### Problem: "Import error in utils.py"
```
Error: ModuleNotFoundError: No module named 'requests'
```

**Solution:**
```bash
pip install requests
```

### Problem: "logo.svg not found"
```
Error: [Errno 2] No such file or directory: '.../bobi/logo.svg'
```

**Solution:**
1. Create a simple logo: `bobi/logo.svg`
2. Or disable watermarking temporarily (remove from watermark.py)

---

## 📝 Configuration Options

### DPI Settings
```python
BOBI_DPI = 150   # Web view (smaller, faster)
BOBI_DPI = 200   # Balanced (recommended)
BOBI_DPI = 300   # Print quality (larger, slower)
```

### Image Format
```python
BOBI_FORMAT = 'png'   # Lossless (recommended for flashcards)
BOBI_FORMAT = 'jpeg'  # Lossy (smaller files)
```

### Timeout
```python
BOBI_REQUEST_TIMEOUT = 60    # Quick for small PDFs
BOBI_REQUEST_TIMEOUT = 120   # Balanced (default)
BOBI_REQUEST_TIMEOUT = 300   # Large PDFs (5 min)
```

---

## 📚 File Structure

```
edvoyage-notes-only-backend-demo-delete-soon/
├── bobi/                          [Flask app - SEPARATE SERVICE]
│   ├── app.py                    (✓ Updated with /api/process)
│   ├── watermark.py
│   ├── requirements.txt
│   ├── logo.svg
│   ├── temp_uploads/              (Temp PDFs during processing)
│   └── static/output/             (Web UI results)
│
├── notes/                         [Django app]
│   ├── models.py                 (✓ Updated Flashcard model)
│   ├── utils.py                  (✓ NEW - BOBI integration)
│   ├── views.py
│   ├── admin.py
│   └── migrations/
│
├── project/                       [Django settings]
│   ├── settings.py               (✓ Add BOBI config)
│   └── ...
│
├── media/                         [Uploaded files]
│   └── flashcards/
│       ├── pdfs/                 (Original PDFs)
│       └── [images from BOBI]     (Processed images)
│
├── test_bobi_integration.py       (✓ NEW - Test suite)
├── BOBI_SETTINGS.md               (✓ NEW - Settings reference)
├── INTEGRATION_PLAN.md            (Original architecture doc)
└── analysis.txt                   (Original analysis doc)
```

---

## 🎯 Data Flow Example

### Scenario: Upload a 3-page flashcard PDF

**Time: t=0s**
- User clicks "Add Flashcard" in Django Admin
- Selects Category, Subject, Sub-subject
- Uploads "lecture.pdf" (3 pages)

**Time: t=0.5s**
- Django saves PDF to: `media/flashcards/pdfs/lecture.pdf`
- Calls `_process_pdf_with_bobi()`

**Time: t=0.6s**
- Django sends HTTP POST to BOBI
- BOBI receives multipart request

**Time: t=1-4s** (BOBI processing)
- Page 1: Extract → Convert → Watermark → Encode
- Page 2: Extract → Convert → Watermark → Encode
- Page 3: Extract → Convert → Watermark → Encode

**Time: t=4.5s**
- BOBI returns JSON with 3 pages (Base64 encoded)
- Django decodes images
- Django creates 3 FlashcardImage records

**Time: t=5s**
- Django Admin page shows 3 image thumbnails
- User confirms processing complete ✓

**Total: ~5 seconds**

---

## 🚨 Important Notes

1. **BOBI Must Run Separately**
   - It's a separate Flask service
   - Must be running before uploading PDFs
   - Runs on localhost:5000 (configurable)

2. **Network Requirements**
   - Django and BOBI communicate via HTTP
   - On same machine: `localhost:5000` works
   - Different machines: use IP address or hostname
   - Docker: use service name (e.g., `bobi-service:5000`)

3. **Resource Usage**
   - PDF processing is CPU-intensive
   - Large PDFs may take 10-30 seconds
   - Increase timeout for large files
   - Each worker can handle one PDF at a time

4. **Error Handling**
   - If BOBI fails, user sees Django ValidationError
   - Error message tells them to check BOBI service
   - PDF is still saved to disk (images not created)
   - User can retry by uploading the flashcard again

5. **Production Deployment**
   - Use Gunicorn instead of Flask dev server
   - Use separate worker machines for BOBI
   - Monitor disk space (temp_uploads folder)
   - Set up log aggregation
   - Use Docker for easy deployment

---

## 🔐 Security Considerations

- BOBI validates PDF file headers (not just extension)
- Temporary files are cleaned up
- Image format is sanitized (png/jpeg only)
- Base64 prevents binary corruption
- Atomic transactions prevent partial saves

### Optional: Add API Authentication

Edit `bobi/app.py` to require API key:
```python
api_key = request.headers.get('X-API-Key')
if api_key != os.getenv('BOBI_API_KEY'):
    return jsonify({"status": "error", "error": "Unauthorized"}), 401
```

Then add to Django settings:
```python
BOBI_API_KEY = 'your-secret-key-here'
```

---

## 📞 Support & Next Steps

**Next Steps:**
1. ✓ Follow Quick Start above
2. ✓ Run test suite to verify setup
3. ✓ Upload a test PDF via Django Admin
4. ✓ Check media folder for generated images
5. ✓ Deploy to production

**If stuck:**
1. Check logs: Look in terminal where BOBI/Django run
2. Test endpoints manually: `curl http://localhost:5000/api/health`
3. Review INTEGRATION_PLAN.md for detailed architecture
4. Check test_bobi_integration.py for expected behavior

---

**Questions? Review:**
- `INTEGRATION_PLAN.md` - Complete architecture
- `bobi.txt` - BOBI application documentation
- `analysis.txt` - Original system analysis
- Test output from `test_bobi_integration.py`

**Good luck! 🚀**
