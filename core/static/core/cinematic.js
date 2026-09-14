document.addEventListener('DOMContentLoaded', () => {
    const hero = document.querySelector('.cinema-hero');
    if (!hero) return;
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const toggle = hero.querySelector('[data-cinema-toggle]');
    const replay = hero.querySelector('[data-cinema-replay]');
    const image = hero.querySelector('.cinema-car');
    let completed = false;
    const start = () => {
        hero.classList.remove('is-running', 'is-paused');
        completed = false;
        toggle.textContent = 'Pause reveal';
        toggle.hidden = replay.hidden = motion.matches;
        if (motion.matches) return;
        void hero.offsetWidth;
        hero.classList.add('is-running');
    };
    toggle.addEventListener('click', () => {
        const paused = hero.classList.toggle('is-paused');
        toggle.textContent = paused ? 'Resume reveal' : 'Pause reveal';
    });
    replay.addEventListener('click', start);
    hero.querySelector('.cinema-progress').addEventListener('animationend', () => {
        completed = true;
        toggle.hidden = true;
    });
    document.addEventListener('visibilitychange', () => {
        if (document.hidden && !completed && hero.classList.contains('is-running')) {
            hero.classList.add('is-paused');
            toggle.textContent = 'Resume reveal';
        }
    });
    motion.addEventListener('change', start);
    // Start immediately in black; the asset can decode during the first lighting cue.
    start();
    image.addEventListener('error', () => {
        hero.classList.remove('is-running');
        toggle.hidden = replay.hidden = true;
    });
});
