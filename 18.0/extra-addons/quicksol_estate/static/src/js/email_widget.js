/** @odoo-module **/

// Email normalization - applied via DOM events
document.addEventListener('DOMContentLoaded', function() {
    applyEmailNormalization();
});

// Also applies when Odoo dynamically loads new elements
if (typeof window.addEventListener !== 'undefined') {
    window.addEventListener('load', function() {
        setTimeout(applyEmailNormalization, 500);
        
        // Reapply when there are DOM changes (editable list view)
        let debounceTimer = null;
        const observer = new MutationObserver(function(mutations) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                applyEmailNormalization();
            }, 200);
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
}

function applyEmailNormalization() {
    // Find all email inputs in the PropertyEmail model
    const emailInputs = document.querySelectorAll('div[name="email"] input.o_input, td[name="email"] input.o_input');
    
    emailInputs.forEach(function(input) {
        // Avoid applying multiple times to the same input
        if (input.dataset.emailNormalizationApplied) return;
        input.dataset.emailNormalizationApplied = 'true';
        
        // Add CSS to display in lowercase (visual only)
        input.style.textTransform = 'lowercase';
        
        // Block whitespace characters
        input.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which || e.keyCode);
            if (char === ' ') {
                e.preventDefault();
                return false;
            }
        });
        
        // Normalize email when leaving the field (blur)
        // Remove spaces and convert to lowercase only when user finishes typing
        input.addEventListener('blur', function(e) {
            if (e.target.value) {
                // Remove spaces and convert to lowercase
                const normalizedEmail = e.target.value.trim().toLowerCase();
                
                if (e.target.value !== normalizedEmail) {
                    e.target.value = normalizedEmail;
                    
                    // Trigger change event for Odoo to detect the change
                    const event = new Event('change', { bubbles: true });
                    e.target.dispatchEvent(event);
                }
            }
        });
        
        // Normalize existing email (on load)
        if (input.value) {
            input.value = input.value.trim().toLowerCase();
        }
    });
}
