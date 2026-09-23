document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click', () => window.print()));
    const form = document.getElementById('estimate-form');
    if (!form) return;
    const totalForms = form.querySelector('[name="lines-TOTAL_FORMS"]');
    const add = document.getElementById('add-estimate-line');
    add.hidden = false;
    add.addEventListener('click', () => {
        const index = Number(totalForms.value);
        if (index >= 20) return;
        const fragment = document.getElementById('estimate-line-template').content.cloneNode(true);
        fragment.querySelectorAll('[name],[id],[for]').forEach(element => {
            for (const attr of ['name', 'id', 'for']) {
                if (element.hasAttribute(attr)) element.setAttribute(attr, element.getAttribute(attr).replaceAll('__prefix__', index));
            }
        });
        document.getElementById('estimate-lines').appendChild(fragment);
        totalForms.value = index + 1;
        add.disabled = index + 1 >= 20;
    });
    form.addEventListener('input', () => {
        let cents = 0;
        form.querySelectorAll('#estimate-lines .estimate-line').forEach(line => {
            if (line.querySelector('[name$="-DELETE"]').checked) return;
            const quantity = Number(line.querySelector('[name$="-quantity"]').value);
            const price = Number(line.querySelector('[name$="-unit_price"]').value);
            if (Number.isFinite(quantity) && Number.isFinite(price)) cents += quantity * Math.round(price * 100);
        });
        document.getElementById('estimate-preview').textContent = `Estimated total: ₹${(cents / 100).toFixed(2)}`;
    });
});
