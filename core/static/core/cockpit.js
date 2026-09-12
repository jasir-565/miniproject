/**
 * AutoNexa Vehicle Service Center JavaScript Helpers
 */

document.addEventListener('DOMContentLoaded', () => {
    // Accordion details toggle enhancements
    const detailsElements = document.querySelectorAll('details');
    detailsElements.forEach(detail => {
        detail.addEventListener('toggle', () => {
            if (detail.open) {
                // Smooth scroll to opened detail card if needed
            }
        });
    });
});
