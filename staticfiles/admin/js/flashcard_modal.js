/**
 * Flashcard PDF Processing Modal
 * Shows a beautiful modal during PDF processing from Flask BOBI service
 */

document.addEventListener('DOMContentLoaded', function() {
    // Create modal HTML
    const modalHTML = `
        <div class="pdf-processing-overlay" id="pdfProcessingOverlay">
            <div class="pdf-processing-modal">
                <div class="pdf-spinner"></div>
                <h2>PDF Processing</h2>
                <p>
                    PDF conversion for <span class="pdf-filename" id="pdfFilename">file.pdf</span> is going on<br>
                    Please wait...
                </p>
            </div>
        </div>
    `;
    
    // Inject modal into page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    const overlay = document.getElementById('pdfProcessingOverlay');
    const filenameSpan = document.getElementById('pdfFilename');
    
    // Get the form
    const form = document.querySelector('form');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            const pdfInput = document.querySelector('input[name="pdf_file"]');
            
            if (pdfInput && pdfInput.files && pdfInput.files.length > 0) {
                const filename = pdfInput.files[0].name;
                
                // Only show modal if it's a PDF
                if (filename.toLowerCase().endsWith('.pdf')) {
                    filenameSpan.textContent = filename;
                    overlay.classList.add('active');
                    
                    // Disable all interactions on the page
                    document.body.style.overflow = 'hidden';
                }
            }
        });
    }
    
    // Listen for completion (when images are created and page reloads or redirects)
    // The modal will disappear when the page reloads after processing
    // If you want to handle it via AJAX, you can emit an event from Django response
    
    // For now, modal will stay visible during the entire save process
    // and disappear when Django completes the save and redirects
});
