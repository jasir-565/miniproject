/**
 * AutoNexa Vehicle Service Center JavaScript Helpers
 */

window.AutoNexa = {
    popup(title, detail = '') {
        const element = document.createElement('div');
        const heading = document.createElement('strong');
        heading.textContent = title;
        element.append(heading, document.createElement('br'), document.createTextNode(detail));
        return element;
    },
    hasCoordinates(lat, lng) {
        return lat !== null && lng !== null && lat !== '' && lng !== '' && Number.isFinite(Number(lat)) &&
            Number.isFinite(Number(lng)) && Math.abs(Number(lat)) <= 90 && Math.abs(Number(lng)) <= 180;
    },
};

// One device watcher shared by all active request cards.
(() => {
    const subscribers = new Set();
    let watchId = null;
    AutoNexa.watchGPS = (success, failure) => {
        const subscriber = { success, failure };
        subscribers.add(subscriber);
        if (!navigator.geolocation) {
            failure({ message: 'GPS is not supported by this browser.' });
        } else if (watchId === null) {
            watchId = navigator.geolocation.watchPosition(
                position => subscribers.forEach(item => item.success(position)),
                error => subscribers.forEach(item => item.failure(error)),
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 3000 },
            );
        }
        return () => {
            subscribers.delete(subscriber);
            if (!subscribers.size && watchId !== null) {
                navigator.geolocation.clearWatch(watchId);
                watchId = null;
            }
        };
    };
})();

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
