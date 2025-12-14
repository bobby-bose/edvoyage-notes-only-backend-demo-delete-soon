#!/usr/bin/env python
"""
Integration Test Script for Django ↔ BOBI Service
Tests the complete workflow of PDF upload and processing

Usage:
    python test_bobi_integration.py

Requirements:
    - BOBI Flask service running on http://localhost:5000
    - Django test database configured
    - Test PDF file in current directory
"""

import os
import sys
import json
import requests
import base64
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(message):
    print(f"{Colors.BLUE}[TEST]{Colors.RESET} {message}")

def print_pass(message):
    print(f"{Colors.GREEN}[PASS]{Colors.RESET} {message}")

def print_fail(message):
    print(f"{Colors.RED}[FAIL]{Colors.RESET} {message}")

def print_info(message):
    print(f"{Colors.YELLOW}[INFO]{Colors.RESET} {message}")

# ============================================================================
# Test 1: BOBI Service Health Check
# ============================================================================

def test_bobi_health():
    """Test that BOBI service is reachable and healthy"""
    print_test("Checking BOBI service health...")
    
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        
        if response.status_code != 200:
            print_fail(f"BOBI returned status {response.status_code}")
            return False
        
        data = response.json()
        if data.get('status') == 'ok':
            print_pass(f"BOBI service is healthy: {data['service']} v{data['version']}")
            return True
        else:
            print_fail(f"BOBI returned unexpected status: {data}")
            return False
    
    except requests.exceptions.ConnectionError:
        print_fail("Cannot connect to BOBI service on http://localhost:5000")
        print_info("Make sure BOBI Flask is running: cd bobi/ && python app.py")
        return False
    
    except Exception as e:
        print_fail(f"Health check error: {str(e)}")
        return False


# ============================================================================
# Test 2: API Endpoint Test
# ============================================================================

def create_test_pdf():
    """Create a simple test PDF if it doesn't exist"""
    pdf_path = 'test_sample.pdf'
    
    if os.path.exists(pdf_path):
        print_info(f"Using existing PDF: {pdf_path}")
        return pdf_path
    
    print_test("Creating test PDF...")
    
    try:
        # Try using reportlab to create a simple PDF
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas as pdf_canvas
        from io import BytesIO
        
        c = pdf_canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "Test Flashcard PDF")
        c.drawString(100, 700, "Page 1 - Sample content")
        c.drawString(100, 650, "This is a test PDF for BOBI integration testing")
        c.showPage()
        
        c.drawString(100, 750, "Test Flashcard PDF")
        c.drawString(100, 700, "Page 2 - More content")
        c.drawString(100, 650, "Multi-page PDF test")
        c.showPage()
        
        c.save()
        print_pass(f"Created test PDF: {pdf_path}")
        return pdf_path
    
    except ImportError:
        print_fail("reportlab not installed. Please install: pip install reportlab")
        return None
    
    except Exception as e:
        print_fail(f"Error creating test PDF: {str(e)}")
        return None


def test_api_process(pdf_path):
    """Test the /api/process endpoint"""
    print_test("Testing BOBI /api/process endpoint...")
    
    if not os.path.exists(pdf_path):
        print_fail(f"PDF file not found: {pdf_path}")
        return False
    
    try:
        # Prepare multipart request
        with open(pdf_path, 'rb') as pdf_file:
            files = {
                'pdf_file': pdf_file,
            }
            data = {
                'flashcard_id': '123',
                'dpi': '200',
                'format': 'png'
            }
            
            print_info("Sending PDF to BOBI...")
            response = requests.post(
                'http://localhost:5000/api/process',
                files=files,
                data=data,
                timeout=120
            )
        
        # Check response
        if response.status_code != 200:
            print_fail(f"BOBI returned status {response.status_code}")
            print_fail(f"Response: {response.text}")
            return False
        
        result = response.json()
        
        if result.get('status') != 'success':
            print_fail(f"Processing failed: {result.get('error')}")
            return False
        
        # Validate response structure
        pages = result.get('pages', [])
        print_pass(f"BOBI processing successful!")
        print_info(f"  - Total pages: {result.get('total_pages')}")
        print_info(f"  - Processing time: {result.get('processing_time_ms')}ms")
        print_info(f"  - Output format: {pages[0].get('format') if pages else 'N/A'}")
        
        # Verify first page can be decoded
        if pages:
            first_page = pages[0]
            try:
                image_bytes = base64.b64decode(first_page['image_base64'])
                print_info(f"  - Page 1 size: {len(image_bytes)} bytes")
                print_info(f"  - Page 1 dimensions: {first_page.get('width')}x{first_page.get('height')}")
            except Exception as e:
                print_fail(f"Error decoding page 1 Base64: {str(e)}")
                return False
        
        return True
    
    except requests.exceptions.Timeout:
        print_fail("Request timeout (120s exceeded)")
        return False
    
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


# ============================================================================
# Test 3: Django Integration
# ============================================================================

def test_django_integration():
    """Test Django utils.py functions"""
    print_test("Testing Django integration functions...")
    
    try:
        # Setup Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
        import django
        django.setup()
        
        from notes.utils import validate_bobi_service
        from django.conf import settings
        
        # Check settings
        bobi_url = getattr(settings, 'BOBI_SERVICE_URL', None)
        if not bobi_url:
            print_fail("BOBI_SERVICE_URL not configured in settings.py")
            print_info("Add this to settings.py:")
            print_info("  BOBI_SERVICE_URL = 'http://localhost:5000'")
            return False
        
        print_info(f"BOBI service URL: {bobi_url}")
        
        # Validate service
        try:
            validate_bobi_service()
            print_pass("Django can communicate with BOBI service")
        except Exception as e:
            print_fail(f"Django cannot reach BOBI: {str(e)}")
            return False
        
        return True
    
    except ImportError as e:
        print_fail(f"Django not properly configured: {str(e)}")
        print_info("Make sure you're running this from the Django project directory")
        return False
    
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


# ============================================================================
# Test 4: End-to-End Test (Optional)
# ============================================================================

def test_end_to_end():
    """Full end-to-end test: upload PDF via Django and check results"""
    print_test("Running end-to-end test...")
    
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
        import django
        django.setup()
        
        from notes.models import Flashcard, Category, Subject, SubSubject
        from django.test import TestCase
        import tempfile
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create or get test data
        category, _ = Category.objects.get_or_create(name='Test Category')
        subject, _ = Subject.objects.get_or_create(name='Test Subject')
        sub_subject, _ = SubSubject.objects.get_or_create(
            name='Test Sub-subject',
            subject=subject
        )
        
        # Create test PDF
        pdf_path = create_test_pdf()
        if not pdf_path:
            return False
        
        with open(pdf_path, 'rb') as f:
            pdf_file = SimpleUploadedFile(
                "test.pdf",
                f.read(),
                content_type="application/pdf"
            )
        
        # Create flashcard
        print_info("Creating flashcard with PDF upload...")
        flashcard = Flashcard(
            category=category,
            subject=subject,
            sub_subject=sub_subject,
            description="Test Flashcard",
            pdf_file=pdf_file
        )
        
        # Save triggers PDF processing
        try:
            flashcard.save()
            print_pass("Flashcard saved successfully")
        except Exception as e:
            print_fail(f"Error saving flashcard: {str(e)}")
            return False
        
        # Check images were created
        images = flashcard.images.all()
        if images.exists():
            print_pass(f"Created {images.count()} images")
            for img in images:
                print_info(f"  - {img.caption}: {img.image.size} bytes")
            return True
        else:
            print_fail("No images were created")
            return False
    
    except Exception as e:
        print_fail(f"End-to-end test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# Main Test Suite
# ============================================================================

def run_all_tests():
    """Run all integration tests"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}  BOBI Django Integration Test Suite{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")
    
    results = {}
    
    # Test 1: Health check
    results['Health Check'] = test_bobi_health()
    print()
    
    if not results['Health Check']:
        print_fail("Cannot proceed without healthy BOBI service")
        return False
    
    # Test 2: API endpoint
    pdf_path = create_test_pdf()
    if pdf_path:
        results['API Process Endpoint'] = test_api_process(pdf_path)
    else:
        results['API Process Endpoint'] = False
    print()
    
    # Test 3: Django integration
    results['Django Integration'] = test_django_integration()
    print()
    
    # Test 4: End-to-end (optional)
    try:
        results['End-to-End'] = test_end_to_end()
    except:
        results['End-to-End'] = False
        print_fail("End-to-end test failed (requires Django)")
    print()
    
    # Summary
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}  Test Summary{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed\n")
    
    if passed == total:
        print(f"{Colors.GREEN}All tests passed! ✓{Colors.RESET}\n")
        return True
    else:
        print(f"{Colors.RED}Some tests failed. See details above.{Colors.RESET}\n")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
