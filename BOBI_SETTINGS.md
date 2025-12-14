"""
BOBI Flask Service Configuration Settings

Add these settings to your Django settings.py file
"""

# ============================================================================
# BOBI Flask Service Configuration
# ============================================================================
# BOBI is a separate Flask service that handles PDF processing
# It converts PDFs to images and applies watermarks
# 
# The following settings configure how Django communicates with BOBI

import os

# URL of the BOBI service
# Must match the Flask app host and port
# Default: http://localhost:5000 (for local development)
# Production: https://bobi.yourserver.com or http://bobi-internal:5000
BOBI_SERVICE_URL = os.getenv('BOBI_SERVICE_URL', 'http://localhost:5000')

# Request timeout in seconds
# Increase this for large PDFs (>10MB) or slow servers
# Typical: 60-120 seconds
BOBI_REQUEST_TIMEOUT = int(os.getenv('BOBI_REQUEST_TIMEOUT', '120'))

# DPI (dots per inch) for PDF to image conversion
# 150 = good for web viewing (smaller files)
# 200 = balanced quality and size (recommended for flashcards)
# 300 = high quality (larger files, for printing)
BOBI_DPI = int(os.getenv('BOBI_DPI', '200'))

# Output image format
# 'png' = lossless, larger files, better for screenshots
# 'jpeg' = lossy, smaller files, better for photos
BOBI_FORMAT = os.getenv('BOBI_FORMAT', 'png')

# Optional: API key for BOBI service authentication
# If BOBI requires authentication, set this to the shared secret
# Leave as None if BOBI doesn't require authentication
BOBI_API_KEY = os.getenv('BOBI_API_KEY', None)

# ============================================================================
# Installation Instructions
# ============================================================================
# 
# 1. Add these settings to your Django settings.py
# 
# 2. Install required packages:
#    pip install requests (for Django → BOBI communication)
# 
# 3. Start BOBI Flask service:
#    cd bobi/
#    python app.py
#    (or for production: gunicorn -w 2 -b 127.0.0.1:5000 app:app)
# 
# 4. Verify BOBI is running:
#    curl http://localhost:5000/api/health
#    Expected: {"status": "ok", ...}
# 
# 5. Test Django integration:
#    - Go to Django admin: http://localhost:8000/admin/notes/flashcard/
#    - Click "Add Flashcard"
#    - Upload a PDF file
#    - Wait for processing (should show images in FlashcardImageInline)
#
# ============================================================================
# Environment Variables (for Docker/production)
# ============================================================================
#
# Set these environment variables instead of editing settings.py:
#
# export BOBI_SERVICE_URL=http://bobi-service:5000
# export BOBI_REQUEST_TIMEOUT=180
# export BOBI_DPI=200
# export BOBI_FORMAT=png
# export BOBI_API_KEY=your-secret-key
#
# ============================================================================
# Troubleshooting
# ============================================================================
#
# Problem: "Cannot connect to BOBI service"
# Solution: Ensure BOBI Flask is running and BOBI_SERVICE_URL is correct
#
# Problem: "Processing timeout"
# Solution: Increase BOBI_REQUEST_TIMEOUT in settings
#
# Problem: "Invalid image format"
# Solution: Ensure BOBI_FORMAT is 'png' or 'jpeg'
#
# ============================================================================
