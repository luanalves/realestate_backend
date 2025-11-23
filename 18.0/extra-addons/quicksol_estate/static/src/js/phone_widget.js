/** @odoo-module **/

// Máscara de telefone brasileiro - aplicada via DOM events
document.addEventListener('DOMContentLoaded', function() {
    applyPhoneMask();
});

// Também aplica quando o Odoo carrega novos elementos dinamicamente
if (typeof window.addEventListener !== 'undefined') {
    window.addEventListener('load', function() {
        setTimeout(applyPhoneMask, 500);
        
        // Reaplica quando há mudanças no DOM (list view editable)
        let debounceTimer;
        const observer = new MutationObserver(function(mutations) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(applyPhoneMask, 150);
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Cleanup on page unload to prevent memory leaks
        window.addEventListener('beforeunload', function() {
            observer.disconnect();
        });
    });
}

function applyPhoneMask() {
    // Busca todos os inputs de telefone no modelo PropertyPhone
    // O input está dentro de uma div com name="phone"
    const phoneInputs = document.querySelectorAll('div[name="phone"] input.o_input, td[name="phone"] input.o_input');
    
    phoneInputs.forEach(function(input) {
        // Remove listeners antigos para evitar duplicação
        if (input.dataset.phoneMaskApplied) return;
        input.dataset.phoneMaskApplied = 'true';
        
        // Bloqueia caracteres não numéricos
        input.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which || e.keyCode);
            if (!/^[0-9]$/.test(char)) {
                e.preventDefault();
                return false;
            }
        });
        
        // Aplica máscara ao digitar
        input.addEventListener('input', function(e) {
            let value = e.target.value;
            
            // Remove tudo que não é número
            value = value.replace(/\D/g, '');
            
            // Limita a 11 dígitos
            value = value.substring(0, 11);
            
            // Aplica a máscara conforme o tamanho
            if (value.length <= 2) {
                value = value.replace(/^(\d{0,2})/, '($1');
            } else if (value.length <= 6) {
                value = value.replace(/^(\d{2})(\d{0,4})/, '($1) $2');
            } else if (value.length <= 10) {
                value = value.replace(/^(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3');
            } else {
                value = value.replace(/^(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3');
            }
            
            e.target.value = value;
            
            // Dispara evento change para o Odoo detectar a mudança
            const event = new Event('change', { bubbles: true });
            e.target.dispatchEvent(event);
        });
        
        // Formata valor inicial se já existir
        if (input.value && !/[()-]/.test(input.value)) {
            const digits = input.value.replace(/\D/g, '');
            if (digits.length === 11) {
                input.value = digits.replace(/^(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
            } else if (digits.length === 10) {
                input.value = digits.replace(/^(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
            }
        }
    });
}
