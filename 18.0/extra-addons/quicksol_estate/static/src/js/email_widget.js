/** @odoo-module **/

// Normalização de e-mail - aplicada via DOM events
document.addEventListener('DOMContentLoaded', function() {
    applyEmailNormalization();
});

// Também aplica quando o Odoo carrega novos elementos dinamicamente
if (typeof window.addEventListener !== 'undefined') {
    window.addEventListener('load', function() {
        setTimeout(applyEmailNormalization, 500);
        
        // Reaplica quando há mudanças no DOM (list view editable)
        const observer = new MutationObserver(function(mutations) {
            applyEmailNormalization();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
}

function applyEmailNormalization() {
    // Busca todos os inputs de email no modelo PropertyEmail
    const emailInputs = document.querySelectorAll('div[name="email"] input.o_input, td[name="email"] input.o_input');
    
    emailInputs.forEach(function(input) {
        // Evita aplicar múltiplas vezes no mesmo input
        if (input.dataset.emailNormalizationApplied) return;
        input.dataset.emailNormalizationApplied = 'true';
        
        // Bloqueia espaços em branco
        input.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which || e.keyCode);
            if (char === ' ') {
                e.preventDefault();
                return false;
            }
        });
        
        // Força minúsculas enquanto digita
        input.addEventListener('keydown', function(e) {
            // Se for uma letra maiúscula (A-Z)
            if (e.key && e.key.length === 1 && e.key >= 'A' && e.key <= 'Z' && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                // Insere a letra minúscula no lugar
                const start = e.target.selectionStart;
                const end = e.target.selectionEnd;
                const value = e.target.value;
                e.target.value = value.substring(0, start) + e.key.toLowerCase() + value.substring(end);
                e.target.selectionStart = e.target.selectionEnd = start + 1;
                
                // Dispara evento input para o Odoo detectar
                const inputEvent = new Event('input', { bubbles: true });
                e.target.dispatchEvent(inputEvent);
            }
        });
        
        // Normaliza o email ao sair do campo (blur)
        input.addEventListener('blur', function(e) {
            if (e.target.value) {
                // Remove espaços e converte para minúsculas
                const normalizedEmail = e.target.value.trim().toLowerCase();
                
                if (e.target.value !== normalizedEmail) {
                    e.target.value = normalizedEmail;
                    
                    // Dispara evento change para o Odoo detectar a mudança
                    const event = new Event('change', { bubbles: true });
                    e.target.dispatchEvent(event);
                }
            }
        });
        
        // Normaliza email existente (ao carregar)
        if (input.value) {
            input.value = input.value.trim().toLowerCase();
        }
    });
}
