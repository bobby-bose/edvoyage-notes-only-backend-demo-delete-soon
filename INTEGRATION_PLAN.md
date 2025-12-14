# Django ↔ BOBI Flask Integration Plan
## Complete Architecture & API Specification

---

## EXECUTIVE SUMMARY

**Goal:** When a user uploads a PDF via Django Admin for a Flashcard:
1. Django receives the PDF file
2. Django sends PDF to BOBI Flask app (via HTTP API)
3. BOBI processes: PDF → Images + Logo
4. BOBI returns images + metadata to Django
5. Django stores images in FlashcardImage model

**Key Decision:** BOBI returns **JSON + Base64 encoded images** (not raw files)

---

## CURRENT ARCHITECTURE (Before Integration)

### Django Flashcard Model
```python
class Flashcard(models.Model):
    category = ForeignKey(Category, ...)
    subject = ForeignKey(Subject, ...)
    sub_subject = ForeignKey(SubSubject, ...)
    description = TextField()
    pdf_file = FileField(upload_to="flashcards/pdfs/")
    
    # When PDF uploaded → calls _process_pdf_to_images()
    # Currently: Local conversion (PyPDF2 + pdf2image + Pillow)
```

### FlashcardImage Model (Child)
```python
class FlashcardImage(models.Model):
    flashcard = ForeignKey(Flashcard, related_name="images")
    image = ImageField(upload_to="flashcards/")
    caption = CharField(max_length=255)  # e.g., "Page 1"
```

### Current Processing Flow
```
PDF Upload → save() triggered → _process_pdf_to_images()
                                 ├─ Read PDF with PyPDF2
                                 ├─ Extract each page
                                 ├─ Apply watermark (local)
                                 ├─ Convert to image (local)
                                 └─ Create FlashcardImage records
```

---

## NEW INTEGRATED ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│ Django Admin User: Uploads PDF for Flashcard                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
            ┌──────────────────────────┐
            │  Django: Flashcard Model │
            │  (notes/models.py)       │
            │  save() method triggered │
            └────────┬─────────────────┘
                     │
                     ├─ Save PDF file to disk (MEDIA_ROOT)
                     │
                     └─> [NEW] Call: send_pdf_to_bobi(pdf_path)
                              │
                              ├─ Read PDF file as binary
                              ├─ Create HTTP request to BOBI
                              ├─ POST /api/process to BOBI Flask
                              │
                              ▼
              ┌────────────────────────────────────────┐
              │ BOBI Flask App (bobi/ folder)          │
              │ POST /api/process endpoint             │
              │                                        │
              │ 1. Receive PDF binary + metadata       │
              │ 2. Save to temp file                   │
              │ 3. Apply watermark                     │
              │ 4. Convert PDF → Images (PNG)          │
              │ 5. Encode images to Base64             │
              │ 6. Return JSON response                │
              └────────┬─────────────────────────────────┘
                       │
                       ▼
            ┌──────────────────────────────┐
            │ Return JSON Response:        │
            │ {                            │
            │   "status": "success",       │
            │   "pages": [                 │
            │     {                        │
            │       "page_num": 1,         │
            │       "image_base64": "...", │
            │       "width": 1200,         │
            │       "height": 1600,        │
            │       "format": "png"        │
            │     }, ...                   │
            │   ]                          │
            │ }                            │
            └────────┬──────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ Django receives JSON       │
        │ (notes/models.py)          │
        │                            │
        │ For each page in response: │
        │  1. Decode Base64 → bytes  │
        │  2. Create FlashcardImage  │
        │  3. Save to media storage  │
        │  4. Link to Flashcard      │
        └────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ FlashcardImage records     │
        │ created & stored in DB     │
        │                            │
        │ All in transaction:        │
        │ If any page fails → all    │
        │ rollback (atomic)          │
        └────────────────────────────┘
```

---

## ANSWER: HOW BOBI RETURNS DATA

### ✅ RECOMMENDED: JSON + Base64 Encoding

```json
{
  "status": "success",
  "job_id": "abc-123-def-456",
  "total_pages": 3,
  "pages": [
    {
      "page_num": 1,
      "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
      "format": "png",
      "width": 1200,
      "height": 1600,
      "size_bytes": 45678
    },
    {
      "page_num": 2,
      "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
      "format": "png",
      "width": 1200,
      "height": 1600,
      "size_bytes": 47891
    },
    {
      "page_num": 3,
      "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
      "format": "png",
      "width": 1200,
      "height": 1600,
      "size_bytes": 46234
    }
  ],
  "processing_time_ms": 3456
}
```

### Why Base64 + JSON? (Not Raw Files)

| Aspect | Raw Files | Base64 + JSON |
|--------|-----------|---------------|
| **Request/Response** | Multipart file streaming | Single JSON payload |
| **State tracking** | Need temp storage | No temp storage needed |
| **Error handling** | Partial uploads fail | Complete/fail atomically |
| **Data integrity** | Verify checksums | Validation built-in |
| **Simplicity** | Complex multipart handling | Standard HTTP JSON |
| **Database storage** | Reference file paths | Direct image creation |
| **Transaction safety** | Split operations | Atomic: all or nothing |
| **Network resilience** | Resume broken uploads | Retry entire request |
| **Reverse compatibility** | Fragile | Stable JSON schema |

**Verdict:** Base64 + JSON is **superior** for this use case.

---

## DETAILED REQUEST/RESPONSE SPECIFICATION

### 1️⃣ DJANGO → BOBI Request

#### Endpoint
```
POST http://localhost:5000/api/process
```

#### Headers
```
Content-Type: application/json
X-API-Key: your-secret-key (optional for auth)
```

#### Request Body (JSON)
```json
{
  "flashcard_id": 42,
  "dpi": 200,
  "format": "png",
  "logo_path": "logo.svg",
  "timeout": 60
}
```

#### File Attachment (Multipart Alternative)
```
If you want to avoid reading file on Django side, use multipart:

POST /api/process
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="flashcard_id"

42
--boundary
Content-Disposition: form-data; name="pdf_file"; filename="flashcard.pdf"
Content-Type: application/pdf

[binary PDF data]
--boundary
Content-Disposition: form-data; name="dpi"

200
--boundary--
```

**Recommendation:** Use **multipart** (simpler on Django side, just use request.FILES)

---

### 2️⃣ BOBI Flask Processes

#### Processing Steps (in BOBI Flask)
```python
@app.route("/api/process", methods=["POST"])
def process_flashcard_pdf():
    """
    1. Receive PDF from Django
    2. Validate PDF
    3. Extract pages
    4. Apply watermark to each page
    5. Encode each image to Base64
    6. Return JSON response
    """
    
    try:
        # 1. Extract PDF from multipart
        pdf_file = request.files['pdf_file']
        flashcard_id = request.form.get('flashcard_id')
        dpi = int(request.form.get('dpi', 200))
        
        # 2. Validate PDF
        if not pdf_file.filename.endswith('.pdf'):
            return jsonify({
                "status": "error",
                "error": "Invalid file format. Only PDF accepted."
            }), 400
        
        # 3. Process PDF
        temp_path = save_temp_file(pdf_file)
        
        # 4. Convert pages
        pages_data = []
        for page_num, image in convert_pdf_to_images(temp_path, dpi=dpi):
            # Apply watermark
            watermarked = apply_watermark(image)
            
            # Encode to Base64
            base64_image = image_to_base64(watermarked)
            
            pages_data.append({
                "page_num": page_num,
                "image_base64": base64_image,
                "format": "png",
                "width": watermarked.width,
                "height": watermarked.height,
                "size_bytes": len(base64_image) // 4 * 3  # approx
            })
        
        # 5. Clean temp files
        cleanup_temp_file(temp_path)
        
        # 6. Return response
        return jsonify({
            "status": "success",
            "flashcard_id": flashcard_id,
            "total_pages": len(pages_data),
            "pages": pages_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
```

---

### 3️⃣ BOBI → DJANGO Response

#### Success Response (200)
```json
{
  "status": "success",
  "flashcard_id": 42,
  "total_pages": 3,
  "pages": [
    {
      "page_num": 1,
      "image_base64": "iVBORw0KGgoAAAANSUhE...",
      "format": "png",
      "width": 1200,
      "height": 1600,
      "size_bytes": 45678
    },
    ...
  ],
  "processing_time_ms": 3456
}
```

#### Error Response (400/500)
```json
{
  "status": "error",
  "flashcard_id": 42,
  "error": "Invalid PDF: File corrupted",
  "error_code": "PDF_CORRUPT"
}
```

---

### 4️⃣ DJANGO Receives & Stores

#### Processing in Django (Flashcard.save())
```python
def save(self, *args, **kwargs):
    # Original code...
    super().save(*args, **kwargs)
    
    if self.pdf_file:
        # Clear old images
        self.images.all().delete()
        
        # NEW: Send to BOBI instead of local processing
        self._process_pdf_with_bobi()

def _process_pdf_with_bobi(self):
    """
    Send PDF to BOBI Flask app and receive processed images
    """
    import requests
    from base64 import b64decode
    from io import BytesIO
    from django.core.files.base import ContentFile
    
    bobi_url = "http://localhost:5000/api/process"
    
    try:
        # 1. Open PDF file
        with open(self.pdf_file.path, 'rb') as pdf:
            files = {
                'pdf_file': pdf,
            }
            data = {
                'flashcard_id': self.id,
                'dpi': 200,
                'format': 'png'
            }
            
            # 2. Send to BOBI
            response = requests.post(
                bobi_url,
                files=files,
                data=data,
                timeout=120
            )
        
        # 3. Handle response
        if response.status_code != 200:
            raise Exception(f"BOBI error: {response.text}")
        
        result = response.json()
        
        if result['status'] != 'success':
            raise Exception(f"Processing failed: {result.get('error')}")
        
        # 4. Create FlashcardImage for each page
        for page_data in result['pages']:
            # Decode Base64
            image_bytes = b64decode(page_data['image_base64'])
            
            # Create in-memory file
            image_file = ContentFile(image_bytes)
            
            # Save to FlashcardImage
            FlashcardImage.objects.create(
                flashcard=self,
                image=image_file,
                caption=f"Page {page_data['page_num']}"
            )
        
        print(f"✓ Successfully processed {result['total_pages']} pages")
        
    except requests.exceptions.Timeout:
        raise Exception("BOBI processing timeout (120s exceeded)")
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to BOBI service. Is it running?")
    except Exception as e:
        raise Exception(f"PDF processing failed: {str(e)}")
```

---

## COMMUNICATION FLOW: DETAILED TIMELINE

### Scenario: User uploads 3-page flashcard PDF

```
t=0s   User clicks "Save" in Django Admin
       │
       ├─ Django: Flashcard.save() called
       │
       ├─ Django: PDF saved to disk
       │  └─ Location: media/flashcards/pdfs/file_xyz.pdf
       │
       ├─ Django: _process_pdf_with_bobi() called
       │  │
       │  ├─ [HTTP POST] Django → BOBI
       │  │  Headers: Content-Type: multipart/form-data
       │  │  Body: {
       │  │    pdf_file: [binary PDF],
       │  │    flashcard_id: 42,
       │  │    dpi: 200
       │  │  }
       │
t=1s   BOBI: /api/process endpoint receives request
       │  │
       │  ├─ Validate PDF (magic bytes)
       │  ├─ Save PDF to temp file
       │  │
       │  ├─ Convert page 1: PDF → PNG (0-1s)
       │  │  └─ Apply watermark
       │  │  └─ Encode to Base64
       │  │  └─ Size: ~45KB base64
       │  │
       │  ├─ Convert page 2: PDF → PNG (1-2s)
       │  │  └─ Apply watermark
       │  │  └─ Encode to Base64
       │  │
       │  ├─ Convert page 3: PDF → PNG (2-3s)
       │  │  └─ Apply watermark
       │  │  └─ Encode to Base64
       │  │
       │  ├─ Clean temp files
       │  │
t=4s   BOBI: Return JSON response
       │  └─ HTTP 200 OK
       │  └─ Body: {
       │       status: "success",
       │       pages: [
       │         {page_num: 1, image_base64: "...", ...},
       │         {page_num: 2, image_base64: "...", ...},
       │         {page_num: 3, image_base64: "...", ...}
       │       ]
       │     }
       │
       ├─ Django: Receive response (4-5s)
       │  │
       │  ├─ Parse JSON
       │  │
       │  ├─ For page 1:
       │  │  ├─ Decode Base64 → bytes
       │  │  ├─ Create File object
       │  │  └─ FlashcardImage.create(image=file, caption="Page 1")
       │  │
       │  ├─ For page 2:
       │  │  └─ FlashcardImage.create(image=file, caption="Page 2")
       │  │
       │  ├─ For page 3:
       │  │  └─ FlashcardImage.create(image=file, caption="Page 3")
       │  │
t=5s   Django Admin: Page reloads
       │
       └─ User sees 3 images in FlashcardImageInline
           (Page 1, Page 2, Page 3 with thumbnails)
```

---

## TRANSACTION & ERROR HANDLING

### Atomic Transaction (All or Nothing)

```python
from django.db import transaction

def _process_pdf_with_bobi(self):
    with transaction.atomic():
        # If anything fails, all FlashcardImages are rolled back
        for page_data in result['pages']:
            image_bytes = b64decode(page_data['image_base64'])
            FlashcardImage.objects.create(
                flashcard=self,
                image=ContentFile(image_bytes),
                caption=f"Page {page_data['page_num']}"
            )
        # If one page fails, all are deleted automatically
```

### Error Scenarios & Handling

| Scenario | Error | Django Action |
|----------|-------|---|
| BOBI down | ConnectionError | Show message: "PDF service unavailable" |
| PDF corrupt | 400 Bad Request | Show message: "Invalid PDF file" |
| Timeout > 120s | TimeoutError | Show message: "Processing took too long" |
| Out of memory | 500 Server Error | Show message: "Service overloaded" |
| Invalid response | JSON decode error | Show message: "Service error" |

```python
try:
    response = requests.post(bobi_url, ..., timeout=120)
    
    if response.status_code == 400:
        raise ValidationError(f"Invalid PDF: {response.json()['error']}")
    elif response.status_code == 500:
        raise Exception("BOBI service error")
    elif response.status_code != 200:
        raise Exception(f"Unexpected response: {response.status_code}")
        
except requests.exceptions.Timeout:
    raise ValidationError("PDF processing timeout (120s exceeded)")
except requests.exceptions.ConnectionError:
    raise ValidationError("Cannot connect to BOBI. Is it running on port 5000?")
except requests.exceptions.RequestException as e:
    raise ValidationError(f"Network error: {str(e)}")
```

---

## DATABASE SCHEMA (Unchanged)

```python
# notes/models.py

class Flashcard(models.Model):
    category = ForeignKey(Category, ...)
    subject = ForeignKey(Subject, ...)
    sub_subject = ForeignKey(SubSubject, ...)
    description = TextField()
    pdf_file = FileField(upload_to="flashcards/pdfs/")  # Original PDF stored
    created_at = DateTimeField(auto_now_add=True)

class FlashcardImage(models.Model):
    flashcard = ForeignKey(Flashcard, related_name="images")
    image = ImageField(upload_to="flashcards/")        # Converted image
    caption = CharField(max_length=255)                 # "Page 1", "Page 2", etc.
    created_at = DateTimeField(auto_now_add=True)      # (optional)

# media/ directory structure:
# media/
# ├─ flashcards/
# │  ├─ pdfs/
# │  │  ├─ file_abc123.pdf       (original upload)
# │  │  └─ file_def456.pdf
# │  │
# │  └─ uuid1.jpg                 (converted from BOBI)
# │     uuid2.jpg
# │     uuid3.jpg
# │     uuid4.jpg
```

---

## CONFIGURATION & SETTINGS

### Django settings.py

```python
# settings.py

# BOBI Flask service URL
BOBI_SERVICE_URL = os.getenv('BOBI_SERVICE_URL', 'http://localhost:5000')
BOBI_REQUEST_TIMEOUT = 120  # seconds
BOBI_DPI = 200              # Conversion DPI
BOBI_FORMAT = 'png'         # Output format

# Optional: API key for BOBI service
BOBI_API_KEY = os.getenv('BOBI_API_KEY', None)
```

### Django utils.py (New File)

```python
# notes/utils.py

import requests
import logging
from base64 import b64decode
from django.core.files.base import ContentFile
from django.conf import settings

logger = logging.getLogger(__name__)

def send_pdf_to_bobi(pdf_path, flashcard_id):
    """
    Send PDF to BOBI Flask service for processing
    
    Args:
        pdf_path: Full path to PDF file
        flashcard_id: Flashcard ID for tracking
    
    Returns:
        List of dicts: [
            {
                'page_num': 1,
                'image_bytes': b'...',
                'caption': 'Page 1'
            },
            ...
        ]
    
    Raises:
        ValueError: If BOBI returns error
        requests.exceptions.RequestException: If network error
    """
    
    try:
        with open(pdf_path, 'rb') as pdf_file:
            files = {
                'pdf_file': pdf_file,
            }
            data = {
                'flashcard_id': flashcard_id,
                'dpi': settings.BOBI_DPI,
                'format': settings.BOBI_FORMAT
            }
            headers = {}
            if settings.BOBI_API_KEY:
                headers['X-API-Key'] = settings.BOBI_API_KEY
            
            response = requests.post(
                f"{settings.BOBI_SERVICE_URL}/api/process",
                files=files,
                data=data,
                headers=headers,
                timeout=settings.BOBI_REQUEST_TIMEOUT
            )
        
        # Handle HTTP errors
        if response.status_code != 200:
            error_msg = response.json().get('error', 'Unknown error')
            logger.error(f"BOBI error ({response.status_code}): {error_msg}")
            raise ValueError(f"BOBI processing failed: {error_msg}")
        
        # Parse response
        result = response.json()
        
        if result.get('status') != 'success':
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"BOBI processing failed: {error_msg}")
            raise ValueError(f"BOBI processing failed: {error_msg}")
        
        # Extract page data
        pages = []
        for page_data in result.get('pages', []):
            image_bytes = b64decode(page_data['image_base64'])
            pages.append({
                'page_num': page_data['page_num'],
                'image_bytes': image_bytes,
                'caption': f"Page {page_data['page_num']}"
            })
        
        logger.info(f"Successfully processed {len(pages)} pages from BOBI")
        return pages
    
    except requests.exceptions.Timeout:
        raise ValueError("PDF processing timeout (120s exceeded). PDF too large?")
    except requests.exceptions.ConnectionError:
        raise ValueError("Cannot connect to BOBI service. Is Flask running on port 5000?")
    except Exception as e:
        logger.exception(f"Error communicating with BOBI: {str(e)}")
        raise ValueError(f"PDF processing failed: {str(e)}")
```

### Updated Flashcard.save() Method

```python
# notes/models.py

from django.db import transaction
from .utils import send_pdf_to_bobi
from django.core.files.base import ContentFile

class Flashcard(models.Model):
    # ... fields ...
    
    def save(self, *args, **kwargs):
        new_pdf = self.pk is None or 'pdf_file' in kwargs.get('update_fields', [])
        
        super().save(*args, **kwargs)
        
        if self.pdf_file and new_pdf:
            self.images.all().delete()
            
            try:
                self._process_pdf_with_bobi()
            except Exception as e:
                # Log error but don't prevent save
                logger.error(f"Failed to process PDF for flashcard {self.id}: {str(e)}")
                # Optional: Set error flag on flashcard
                # self.processing_error = str(e)
                # self.save(update_fields=['processing_error'])
    
    def _process_pdf_with_bobi(self):
        """Send PDF to BOBI and store returned images"""
        
        pages = send_pdf_to_bobi(self.pdf_file.path, self.id)
        
        # Use atomic transaction for data integrity
        with transaction.atomic():
            for page in pages:
                image_file = ContentFile(
                    page['image_bytes'],
                    name=f"{uuid4()}.jpg"
                )
                
                FlashcardImage.objects.create(
                    flashcard=self,
                    image=image_file,
                    caption=page['caption']
                )
```

---

## API SPECIFICATION: Complete BOBI Endpoint

### Modified BOBI app.py

```python
# bobi/app.py

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import fitz
import uuid
import base64
import os
import io
from watermark import apply_watermark

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "temp_uploads")
LOGO_SVG = os.path.join(BASE_DIR, "logo.svg")

os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/api/process", methods=["POST"])
def process_pdf():
    """
    Process PDF from Django Flashcard upload
    
    Request:
        - pdf_file: PDF file (multipart)
        - flashcard_id: Flashcard ID (form data)
        - dpi: Conversion DPI, default 200 (form data)
        - format: Output format (png/jpeg), default png (form data)
    
    Response:
        {
            "status": "success|error",
            "flashcard_id": <id>,
            "total_pages": <count>,
            "pages": [
                {
                    "page_num": 1,
                    "image_base64": "iVBORw0...",
                    "format": "png",
                    "width": 1200,
                    "height": 1600,
                    "size_bytes": 45678
                },
                ...
            ],
            "processing_time_ms": 3456
        }
    """
    
    import time
    start_time = time.time()
    
    try:
        # 1. Extract request data
        if 'pdf_file' not in request.files:
            return jsonify({
                "status": "error",
                "error": "No pdf_file provided"
            }), 400
        
        pdf_file = request.files['pdf_file']
        flashcard_id = request.form.get('flashcard_id')
        dpi = int(request.form.get('dpi', 200))
        output_format = request.form.get('format', 'png').lower()
        
        if not pdf_file.filename.lower().endswith('.pdf'):
            return jsonify({
                "status": "error",
                "error": "File must be PDF format",
                "error_code": "INVALID_FORMAT"
            }), 400
        
        # 2. Save PDF temporarily
        temp_filename = f"{uuid.uuid4()}_{secure_filename(pdf_file.filename)}"
        temp_path = os.path.join(UPLOAD_DIR, temp_filename)
        pdf_file.save(temp_path)
        
        try:
            # 3. Open PDF with PyMUPDF
            doc = fitz.open(temp_path)
            total_pages = len(doc)
            
            if total_pages == 0:
                return jsonify({
                    "status": "error",
                    "error": "PDF has no pages",
                    "error_code": "EMPTY_PDF"
                }), 400
            
            pages_data = []
            
            # 4. Process each page
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Get pixmap at specified DPI
                mat = fitz.Matrix(dpi/72, dpi/72)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image for watermarking
                img_bytes = pix.tobytes("ppm")
                from PIL import Image
                img = Image.open(io.BytesIO(img_bytes))
                
                # Apply watermark (integrate with existing logic)
                watermarked = apply_watermark_to_image(img)
                
                # Save to bytes
                output_bytes = io.BytesIO()
                watermarked.save(output_bytes, format=output_format.upper())
                output_bytes.seek(0)
                
                # Encode to Base64
                image_base64 = base64.b64encode(output_bytes.read()).decode('utf-8')
                
                pages_data.append({
                    "page_num": page_num + 1,
                    "image_base64": image_base64,
                    "format": output_format,
                    "width": watermarked.width,
                    "height": watermarked.height,
                    "size_bytes": len(image_base64)
                })
            
            # 5. Return success response
            processing_time = int((time.time() - start_time) * 1000)
            
            return jsonify({
                "status": "success",
                "flashcard_id": flashcard_id,
                "total_pages": total_pages,
                "pages": pages_data,
                "processing_time_ms": processing_time
            }), 200
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "error_code": "PROCESSING_ERROR"
        }), 500

if __name__ == "__main__":
    app.run(debug=False, host='127.0.0.1', port=5000)
```

---

## DEPLOYMENT ARCHITECTURE

### Local Development

```
┌──────────────────────────────────────────────────────┐
│ Your Machine                                         │
│                                                      │
│ ┌─────────────────────┐      ┌──────────────────┐   │
│ │ Django Admin        │◄────►│ BOBI Flask       │   │
│ │ http://8000         │      │ http://5000      │   │
│ │ (Port 8000)         │      │ (Port 5000)      │   │
│ └─────────────────────┘      └──────────────────┘   │
│                                                      │
│ Both running on localhost (127.0.0.1)              │
└──────────────────────────────────────────────────────┘

Commands to run:

Terminal 1: django/
$ python manage.py runserver 8000

Terminal 2: bobi/
$ python app.py

# Test:
curl -X POST http://localhost:5000/api/process \
  -F "pdf_file=@flashcard.pdf" \
  -F "flashcard_id=42"
```

### Production (VPS/Nginx)

```
┌────────────────────────────────────────────────────────┐
│ VPS Server (e.g., EC2, Linode, DigitalOcean)         │
│                                                        │
│ ┌──────────────────────────────────────────────────┐  │
│ │ Nginx (Reverse Proxy)                            │  │
│ │ ├─ Port 80/443 (public)                         │  │
│ │ └─ Routes:                                       │  │
│ │    ├─ /admin → Django (127.0.0.1:8000)         │  │
│ │    ├─ /api → Django (127.0.0.1:8000)           │  │
│ │    └─ /static → Static files                    │  │
│ └──────────────────────────────────────────────────┘  │
│                        ▲                              │
│   ┌────────────────────┼────────────────────┐        │
│   │                    │                    │        │
│ ┌─┴──────────────┐  ┌─┴──────────────┐  ┌─┴────────┐ │
│ │ Gunicorn       │  │ BOBI Flask     │  │ Redis    │ │
│ │ (Django)       │  │ (Processing)   │  │ (Cache)  │ │
│ │ :8000 (4 workers)  │ :5000 (2 workers)  │ :6379   │ │
│ └────────────────┘  └────────────────┘  └─────────┘ │
│                                                        │
│ /var/www/edvoyage/                                    │
│ ├─ manage.py                                          │
│ ├─ media/                     (images stored here)    │
│ │  ├─ flashcards/                                    │
│ │  │  ├─ pdfs/                                       │
│ │  │  └─ [converted images]                          │
│ │                                                     │
│ ├─ bobi/                      (separate app)          │
│ │  ├─ app.py                                         │
│ │  ├─ temp_uploads/           (temp PDFs)            │
│ │  └─ logo.svg                                       │
│                                                        │
└────────────────────────────────────────────────────────┘

Systemd services:
├─ django.service (Gunicorn)
├─ bobi.service (Flask)
└─ redis.service
```

---

## SUMMARY: Decision & Recommendation

### ✅ FINAL ANSWER: HOW TO RETURN DATA

**Format:** JSON Response with Base64-encoded images

**Why?**
1. ✓ Simple: Single HTTP request/response
2. ✓ Atomic: All pages or nothing
3. ✓ Secure: Validates JSON schema
4. ✓ Reliable: No partial failures
5. ✓ Scalable: Works with multiple servers
6. ✓ Debuggable: Can inspect JSON

**Response Structure:**
```json
{
  "status": "success",
  "flashcard_id": <int>,
  "total_pages": <int>,
  "pages": [
    {
      "page_num": <int>,
      "image_base64": "<string>",
      "format": "png",
      "width": <int>,
      "height": <int>,
      "size_bytes": <int>
    }
  ],
  "processing_time_ms": <int>
}
```

**Django Code to Store:**
```python
# Decode each page from Base64
# Create FlashcardImage record
# Save to media/flashcards/
```

**Expected Timeline:**
- PDF upload: 1-2s
- BOBI processing: 2-4s (depends on page count/DPI)
- Django storage: 1s
- Total: 4-7s per flashcard

---

## Next Steps

1. **Modify BOBI:** Add `/api/process` endpoint (see code above)
2. **Modify Django:** Update `Flashcard._process_pdf_with_bobi()` method
3. **Test locally:** Both services running on localhost
4. **Deploy:** Both services on VPS with Nginx proxy

Would you like me to:
- [ ] Generate complete bobi/app.py with /api/process endpoint?
- [ ] Generate complete notes/utils.py helper functions?
- [ ] Generate complete notes/models.py updated Flashcard class?
- [ ] Create admin.py modifications for better UX?
- [ ] Create docker-compose.yml for easy local testing?

