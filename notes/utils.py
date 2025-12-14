"""
Django utility functions for BOBI Flask integration
Handles communication between Django Flashcard model and BOBI PDF processor
"""

import requests
import logging
import os
from base64 import b64decode
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from pathlib import Path

logger = logging.getLogger(__name__)


class BOBIServiceError(Exception):
    """Raised when BOBI service returns an error"""
    pass


class BOBIConnectionError(Exception):
    """Raised when unable to connect to BOBI service"""
    pass


def get_bobi_url():
    """Get BOBI service URL from settings"""
    return getattr(settings, 'BOBI_SERVICE_URL', 'http://localhost:5000')


def send_pdf_to_bobi(pdf_path, flashcard_id):
    """
    Send PDF to BOBI Flask service for processing
    
    Args:
        pdf_path (str): Full path to PDF file
        flashcard_id (int): Flashcard ID for tracking
    
    Returns:
        list: List of dicts with page data:
            [
                {
                    'page_num': 1,
                    'image_bytes': b'...',
                    'caption': 'Page 1',
                    'width': 1200,
                    'height': 1600,
                    'size_bytes': 45678
                },
                ...
            ]
    
    Raises:
        BOBIConnectionError: If BOBI service is unreachable
        BOBIServiceError: If BOBI returns an error
        ValueError: If response is malformed
    """
    
    bobi_url = get_bobi_url()
    timeout = getattr(settings, 'BOBI_REQUEST_TIMEOUT', 120)
    dpi = getattr(settings, 'BOBI_DPI', 200)
    output_format = getattr(settings, 'BOBI_FORMAT', 'png')
    
    try:
        # 1. Open PDF file and prepare multipart request
        with open(pdf_path, 'rb') as pdf_file:
            files = {
                'pdf_file': pdf_file,
            }
            data = {
                'flashcard_id': str(flashcard_id),
                'dpi': str(dpi),
                'format': output_format
            }
            
            # Add optional API key header
            headers = {}
            api_key = getattr(settings, 'BOBI_API_KEY', None)
            if api_key:
                headers['X-API-Key'] = api_key
            
            logger.info(f"[BOBI] Sending PDF to {bobi_url}/api/process (flashcard_id={flashcard_id})")
            
            # 2. Send POST request to BOBI
            response = requests.post(
                f"{bobi_url}/api/process",
                files=files,
                data=data,
                headers=headers,
                timeout=timeout
            )
        
        # 3. Handle HTTP errors
        if response.status_code != 200:
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
            
            error_msg = error_data.get('error', 'Unknown error')
            error_code = error_data.get('error_code', 'UNKNOWN')
            
            logger.error(f"[BOBI] Error ({response.status_code}): {error_msg} ({error_code})")
            raise BOBIServiceError(f"BOBI processing failed: {error_msg}")
        
        # 4. Parse JSON response
        try:
            result = response.json()
        except ValueError as e:
            logger.error(f"[BOBI] Invalid JSON response: {str(e)}")
            raise ValueError(f"BOBI returned invalid JSON: {str(e)}")
        
        # 5. Check result status
        if result.get('status') != 'success':
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"[BOBI] Processing failed: {error_msg}")
            raise BOBIServiceError(f"BOBI processing failed: {error_msg}")
        
        # 6. Extract and decode page data
        pages = []
        for page_data in result.get('pages', []):
            try:
                image_bytes = b64decode(page_data['image_base64'])
                pages.append({
                    'page_num': page_data['page_num'],
                    'image_bytes': image_bytes,
                    'caption': f"Page {page_data['page_num']}",
                    'width': page_data.get('width'),
                    'height': page_data.get('height'),
                    'size_bytes': page_data.get('size_bytes'),
                    'format': page_data.get('format', 'png')
                })
            except (KeyError, ValueError) as e:
                logger.error(f"[BOBI] Error parsing page data: {str(e)}")
                raise ValueError(f"Invalid page data in BOBI response: {str(e)}")
        
        processing_time = result.get('processing_time_ms', 0)
        logger.info(f"[BOBI] Successfully processed {len(pages)} pages in {processing_time}ms")
        
        return pages
    
    except requests.exceptions.Timeout:
        error_msg = f"PDF processing timeout ({timeout}s exceeded). PDF too large?"
        logger.error(f"[BOBI] {error_msg}")
        raise BOBIConnectionError(error_msg)
    
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to BOBI service at {bobi_url}. Is Flask running on port 5000?"
        logger.error(f"[BOBI] {error_msg}")
        raise BOBIConnectionError(error_msg)
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error communicating with BOBI: {str(e)}"
        logger.error(f"[BOBI] {error_msg}")
        raise BOBIConnectionError(error_msg)
    
    except (BOBIServiceError, BOBIConnectionError, ValueError):
        # Re-raise our custom exceptions
        raise
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"[BOBI] {error_msg}")
        raise BOBIServiceError(error_msg)


def validate_bobi_service():
    """
    Validate that BOBI service is reachable
    
    Returns:
        bool: True if service is healthy
    
    Raises:
        BOBIConnectionError: If service is not reachable
    """
    bobi_url = get_bobi_url()
    
    try:
        response = requests.get(
            f"{bobi_url}/api/health",
            timeout=5
        )
        if response.status_code == 200:
            logger.info(f"[BOBI] Health check passed: {bobi_url}")
            return True
        else:
            raise BOBIConnectionError(f"BOBI returned status {response.status_code}")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[BOBI] Health check failed: {str(e)}")
        raise BOBIConnectionError(f"Cannot reach BOBI service: {str(e)}")


def create_flashcard_images_from_pages(flashcard, pages):
    """
    Create FlashcardImage objects from BOBI response pages
    
    Args:
        flashcard (Flashcard): The Flashcard model instance
        pages (list): List of page dicts from send_pdf_to_bobi()
    
    Returns:
        list: List of created FlashcardImage instances
    
    Raises:
        Exception: If image creation fails
    """
    from uuid import uuid4
    from .models import FlashcardImage
    
    created_images = []
    
    try:
        for page in pages:
            try:
                # Create Django File object from image bytes
                image_file = ContentFile(
                    page['image_bytes'],
                    name=f"{uuid4()}.{page.get('format', 'png')}"
                )
                
                # Create FlashcardImage record
                flashcard_image = FlashcardImage.objects.create(
                    flashcard=flashcard,
                    image=image_file,
                    caption=page['caption']
                )
                
                created_images.append(flashcard_image)
                
                logger.info(
                    f"[Flashcard] Created image for page {page['page_num']} "
                    f"(flashcard_id={flashcard.id}, size={len(page['image_bytes'])} bytes)"
                )
            
            except Exception as e:
                logger.error(f"[Flashcard] Failed to create image for page {page['page_num']}: {str(e)}")
                raise
        
        logger.info(f"[Flashcard] Successfully created {len(created_images)} images for flashcard {flashcard.id}")
        return created_images
    
    except Exception as e:
        logger.error(f"[Flashcard] Error creating flashcard images: {str(e)}")
        raise


def process_flashcard_pdf_with_bobi(flashcard):
    """
    Complete workflow: send PDF to BOBI and create images in Flashcard
    This is the main function called from Flashcard.save()
    
    Args:
        flashcard (Flashcard): Flashcard instance with pdf_file
    
    Raises:
        BOBIConnectionError: If cannot reach BOBI service
        BOBIServiceError: If BOBI processing fails
        ValueError: If response is malformed
    """
    from django.db import transaction
    
    if not flashcard.pdf_file:
        raise ValueError("Flashcard has no PDF file")
    
    pdf_path = flashcard.pdf_file.path
    
    # Verify PDF file exists
    if not os.path.exists(pdf_path):
        raise ValueError(f"PDF file not found: {pdf_path}")
    
    logger.info(f"[Flashcard] Starting PDF processing for flashcard {flashcard.id}")
    
    # Send to BOBI
    pages = send_pdf_to_bobi(pdf_path, flashcard.id)
    
    # Create images in transaction (all or nothing)
    with transaction.atomic():
        # Clear any existing images
        flashcard.images.all().delete()
        
        # Create new images from BOBI response
        create_flashcard_images_from_pages(flashcard, pages)
    
    logger.info(f"[Flashcard] Successfully processed PDF for flashcard {flashcard.id}")


# Optional: Health check decorator for views
def require_bobi_health(view_func):
    """
    Decorator to ensure BOBI service is healthy before processing
    Usage:
        @require_bobi_health
        def my_view(request):
            ...
    """
    def wrapper(request, *args, **kwargs):
        try:
            validate_bobi_service()
        except BOBIConnectionError as e:
            from django.http import HttpResponse
            return HttpResponse(f"Service unavailable: {str(e)}", status=503)
        return view_func(request, *args, **kwargs)
    return wrapper
