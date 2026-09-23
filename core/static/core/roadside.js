/* Progressive enhancement: all fields and submit remain available without JavaScript. */
(() => {
    const form = document.getElementById('assistance-form');
    if (!form) return;
    const panels = [...form.querySelectorAll('[data-rescue-panel]')];
    const steps = [...form.querySelectorAll('[data-rescue-step]')];
    const next = form.querySelector('[data-rescue-next]');
    const back = form.querySelector('[data-rescue-back]');
    const submit = document.getElementById('rescue-submit');
    const problem = document.getElementById('problem_description');
    const location = document.getElementById('location_details');
    const latitude = document.getElementById('customer_latitude');
    const longitude = document.getElementById('customer_longitude');
    const gpsButton = document.getElementById('detect-gps-btn');
    const clearGPS = document.getElementById('clear-gps-btn');
    const gpsStatus = document.getElementById('gps-status-box');
    let current = 0;
    let generatedLocation = '';
    const selected = name => form.querySelector(`input[name="${name}"]:checked`);
    const validateText = () => {
        problem.setCustomValidity(problem.value.trim().length >= 10 ? '' : 'Please describe the problem in at least 10 characters.');
        location.setCustomValidity(location.value.trim().length >= 5 ? '' : 'Please enter a location or landmark with at least 5 characters.');
    };
    function updateSummary() {
        const vehicle = selected('vehicle');
        const type = selected('assistance_type');
        document.getElementById('rescue-summary-vehicle').textContent = vehicle ? `${vehicle.dataset.vehicleName} · ${vehicle.dataset.vehicleReg}` : 'Select your vehicle';
        document.getElementById('rescue-summary-type').textContent = type ? type.value : 'Choose the help you need';
        const locationText = location.value.trim();
        document.getElementById('rescue-summary-location').textContent = locationText || (latitude.value && longitude.value ? 'GPS coordinates attached' : 'Your location goes here');
        const ready = [Boolean(vehicle), Boolean(type && problem.value.trim().length >= 10), locationText.length >= 5];
        steps.forEach((step, index) => step.classList.toggle('is-complete', ready[index]));
        const count = ready.filter(Boolean).length;
        document.getElementById('rescue-completion').value = count;
        document.getElementById('rescue-completion-text').textContent = `${count} of 3 ready`;
        validateText();
    }
    function showStep(index, focus = true) {
        current = index;
        panels.forEach((panel, i) => { panel.hidden = i !== index; });
        steps.forEach((step, i) => {
            if (i === index) step.setAttribute('aria-current', 'step');
            else step.removeAttribute('aria-current');
        });
        back.hidden = index === 0;
        next.hidden = index === panels.length - 1;
        submit.hidden = index !== panels.length - 1;
        document.getElementById('rescue-step-caption').textContent = `STEP ${index + 1} OF 3`;
        if (focus) {
            const legend = panels[index].querySelector('legend');
            legend.tabIndex = -1;
            legend.focus({ preventScroll: true });
            panels[index].scrollIntoView({ behavior: 'auto', block: 'nearest' });
        }
    }
    function firstInvalid(panel) {
        validateText();
        return [...panel.querySelectorAll('input, textarea')].find(input => !input.validity.valid);
    }
    function goTo(index) {
        if (index > current) {
            for (let i = 0; i < index; i++) {
                const invalid = firstInvalid(panels[i]);
                if (invalid) { showStep(i); invalid.reportValidity(); return; }
            }
        }
        showStep(index);
    }
    form.noValidate = true;
    form.querySelector('.rescue-location-control').hidden = false;
    form.querySelector('.rescue-steps').hidden = false;
    document.querySelector('.rescue-completion').hidden = false;
    steps.forEach((step, index) => step.addEventListener('click', () => goTo(index)));
    next.addEventListener('click', () => goTo(current + 1));
    back.addEventListener('click', () => goTo(current - 1));
    form.addEventListener('input', updateSummary);
    form.addEventListener('change', updateSummary);
    form.addEventListener('submit', event => {
        if (current < panels.length - 1) { event.preventDefault(); goTo(current + 1); return; }
        for (let i = 0; i < panels.length; i++) {
            const invalid = firstInvalid(panels[i]);
            if (invalid) { event.preventDefault(); showStep(i); invalid.reportValidity(); return; }
        }
        submit.disabled = true;
        submit.textContent = 'Sending your request…';
    });
    window.addEventListener('pageshow', () => {
        submit.disabled = false;
        submit.textContent = 'Request roadside help ↗';
    });
    function gpsMessage(message, error = false) {
        gpsStatus.hidden = false;
        gpsStatus.dataset.error = String(error);
        gpsStatus.textContent = message;
    }
    gpsButton.addEventListener('click', () => {
        if (!navigator.geolocation) {
            gpsMessage('Location detection is unavailable in this browser. Enter your location or a nearby landmark below.', true);
            return;
        }
        gpsButton.disabled = true;
        gpsButton.textContent = 'Finding your location…';
        gpsMessage('Waiting for your browser’s location permission…');
        navigator.geolocation.getCurrentPosition(position => {
            latitude.value = position.coords.latitude;
            longitude.value = position.coords.longitude;
            gpsMessage(`GPS attached · ${position.coords.latitude.toFixed(5)}, ${position.coords.longitude.toFixed(5)}. Add a landmark below if it will help your technician.`);
            if (!location.value.trim()) {
                generatedLocation = `GPS location: ${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`;
                location.value = generatedLocation;
            }
            gpsButton.disabled = false;
            gpsButton.textContent = 'Refresh location ↗';
            clearGPS.hidden = false;
            updateSummary();
        }, error => {
            const messages = {
                1: 'Location permission was denied. You can still enter a road name or landmark below.',
                2: 'Your location could not be found. Try again or enter a road name or landmark below.',
                3: 'Location detection timed out. Try again or enter your location below.'
            };
            gpsMessage(messages[error.code] || 'Could not detect your location. Please enter it below.', true);
            gpsButton.disabled = false;
            gpsButton.textContent = 'Try location again ↗';
        }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 });
    });
    clearGPS.addEventListener('click', () => {
        latitude.value = '';
        longitude.value = '';
        if (generatedLocation && location.value === generatedLocation) location.value = '';
        generatedLocation = '';
        clearGPS.hidden = true;
        gpsButton.textContent = 'Use my location ↗';
        gpsMessage('GPS coordinates removed. Enter your location or landmark below.');
        updateSummary();
    });
    clearGPS.hidden = !(latitude.value && longitude.value);
    updateSummary();
    showStep(0, false);
})();
