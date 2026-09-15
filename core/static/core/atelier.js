/* Progressive interface enhancements; every essential action is still a link or form. */
document.addEventListener('DOMContentLoaded', () => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const menu = document.querySelector('.menu-toggle');
    const nav = document.querySelector('.primary-nav');
    const closeMenu = () => { nav?.classList.remove('is-open'); menu?.setAttribute('aria-expanded', 'false'); };
    menu?.addEventListener('click', () => {
        const open = menu.getAttribute('aria-expanded') !== 'true';
        menu.setAttribute('aria-expanded', String(open));
        nav.classList.toggle('is-open', open);
    });
    nav?.querySelectorAll('a').forEach(link => {
        const url = new URL(link.href);
        if (url.pathname === location.pathname && !url.hash) link.setAttribute('aria-current', 'page');
        link.addEventListener('click', closeMenu);
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            if (menu?.getAttribute('aria-expanded') === 'true') { closeMenu(); menu.focus(); }
            document.querySelectorAll('.account-menu[open]').forEach(element => { element.open = false; element.querySelector('summary').focus(); });
        }
    });
    document.addEventListener('click', event => {
        if (!event.target.closest('.site-header')) closeMenu();
        document.querySelectorAll('.account-menu[open]').forEach(element => { if (!element.contains(event.target)) element.open = false; });
    });

    if (!reducedMotion && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver(entries => entries.forEach(entry => {
            if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); }
        }), { threshold: .08 });
        document.querySelectorAll('[data-reveal]').forEach(element => { element.classList.add('reveal-ready'); observer.observe(element); });
    }
    if (!reducedMotion && window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
        document.querySelectorAll('[data-tilt]').forEach(element => {
            let frame;
            element.addEventListener('pointermove', event => {
                const bounds = element.getBoundingClientRect();
                const x = (event.clientX - bounds.left) / bounds.width - .5;
                const y = (event.clientY - bounds.top) / bounds.height - .5;
                cancelAnimationFrame(frame);
                frame = requestAnimationFrame(() => { element.style.transform = `perspective(1200px) rotateY(${x * 4}deg) rotateX(${-y * 3}deg)`; });
            });
            element.addEventListener('pointerleave', () => { cancelAnimationFrame(frame); element.style.transform = ''; });
        });
    }
    const inspection = {
        engine: ['01', 'A healthy heart. A better drive.', 'Engine diagnostics, oil changes, and the details that keep you moving.'],
        tires: ['02', 'Confidence at every corner.', 'Tyre care, brake inspections, and alignment for the road ahead.'],
        care: ['03', 'The small things matter.', 'Routine maintenance and careful checks, from the cabin to the bonnet.'],
    };
    document.querySelectorAll('[data-inspect]').forEach(button => button.addEventListener('click', () => {
        const detail = inspection[button.dataset.inspect];
        if (!detail) return;
        ['inspection-number', 'inspection-title', 'inspection-copy'].forEach((id, i) => { document.getElementById(id).textContent = detail[i]; });
        document.querySelectorAll('[data-inspect]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    }));
    document.querySelectorAll('[data-paint]').forEach(button => button.addEventListener('click', () => {
        button.closest('.vehicle-showcase').style.setProperty('--car-paint', button.dataset.paint);
        document.querySelectorAll('[data-paint]').forEach(item => { item.classList.toggle('is-selected', item === button); item.setAttribute('aria-pressed', String(item === button)); });
    }));
    const search = document.querySelector('[data-garage-search]');
    search?.addEventListener('input', () => {
        const query = search.value.trim().toLocaleLowerCase();
        let visible = 0;
        document.querySelectorAll('[data-vehicle-card]').forEach(card => { card.hidden = !card.dataset.vehicleCard.toLocaleLowerCase().includes(query); if (!card.hidden) visible++; });
        const status = document.getElementById('garage-search-status');
        if (status) status.textContent = visible ? `${visible} vehicle${visible === 1 ? '' : 's'} shown` : 'No vehicles match. Try a registration, brand, or model.';
    });

    // Staff Dashboard: Multi-Criteria Filter & Real-Time Search System
    const stageTabs = document.querySelectorAll('.stage-tab[data-filter], .pipeline-step[data-filter]');
    const resetFilterBtn = document.getElementById('pipeline-filter-all');
    const clearFilterLink = document.getElementById('pipeline-clear-filter');
    const resetAllBtn = document.getElementById('reset-all-filters-btn');
    const filterBanner = document.getElementById('pipeline-filter-banner');
    const currentFilterLabel = document.getElementById('pipeline-current-filter');
    const emptyNotice = document.getElementById('job-filtered-empty');
    const jobCards = document.querySelectorAll('.job-menu[data-job-status]');
    const searchInput = document.getElementById('staff-search-input');
    const searchCounter = document.getElementById('staff-search-count');
    const kpiTriggers = document.querySelectorAll('[data-pipeline-trigger]');

    if (jobCards.length > 0) {
        let currentStage = 'ALL';
        let currentSearch = '';

        const applyFilters = () => {
            let visibleCount = 0;
            const query = currentSearch.trim().toLowerCase();

            jobCards.forEach(card => {
                const status = card.dataset.jobStatus;
                const haystack = (card.dataset.searchHaystack || card.textContent).toLowerCase();

                const matchStage = (currentStage === 'ALL' || status === currentStage);
                const matchSearch = (!query || haystack.includes(query));

                const isVisible = matchStage && matchSearch;
                card.style.display = isVisible ? '' : 'none';
                if (isVisible) visibleCount++;
            });

            if (emptyNotice) {
                emptyNotice.style.display = (visibleCount === 0) ? 'block' : 'none';
            }

            if (searchCounter) {
                searchCounter.textContent = `${visibleCount} order${visibleCount === 1 ? '' : 's'}`;
            }

            stageTabs.forEach(tab => {
                const isSelected = (tab.dataset.filter === currentStage);
                tab.classList.toggle('is-selected', isSelected);
                tab.setAttribute('aria-selected', String(isSelected));
            });

            if (filterBanner && currentFilterLabel) {
                if (currentStage === 'ALL' && !query) {
                    filterBanner.style.display = 'none';
                } else {
                    filterBanner.style.display = 'flex';
                    let labelText = currentStage;
                    if (currentStage === 'ALL') labelText = 'All Stages';
                    else if (currentStage === 'PENDING') labelText = 'Awaiting Appointment';
                    else if (currentStage === 'CONFIRMED') labelText = 'Scheduled';
                    else if (currentStage === 'IN_PROGRESS') labelText = 'In Progress';
                    
                    if (query) {
                        labelText += ` (matching "${query}")`;
                    }
                    currentFilterLabel.textContent = labelText;
                }
            }
        };

        stageTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const filter = tab.dataset.filter || 'ALL';
                currentStage = filter;
                applyFilters();
            });
        });

        kpiTriggers.forEach(kpi => {
            kpi.addEventListener('click', () => {
                const filter = kpi.dataset.pipelineTrigger;
                if (filter) {
                    currentStage = filter;
                    applyFilters();
                    document.getElementById('active-jobs')?.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });

        searchInput?.addEventListener('input', () => {
            currentSearch = searchInput.value;
            applyFilters();
        });

        const resetAll = () => {
            currentStage = 'ALL';
            currentSearch = '';
            if (searchInput) searchInput.value = '';
            applyFilters();
        };

        resetFilterBtn?.addEventListener('click', resetAll);
        clearFilterLink?.addEventListener('click', resetAll);
        resetAllBtn?.addEventListener('click', resetAll);
    }

    // Kinetic Road Runway: Accelerate / Rev Engine
    document.querySelectorAll('.kinetic-road-stage').forEach(stage => {
        const revBtn = stage.querySelector('.road-rev-btn');
        const speedElem = stage.querySelector('.speedometer-reading');
        const modeElem = stage.querySelector('.mode-label');
        let revTimer = null;

        const triggerAccelerate = () => {
            stage.classList.add('is-accelerating');
            if (modeElem) modeElem.textContent = 'Full Throttle';
            if (revBtn) revBtn.textContent = 'Boost Active! 🔥';

            let current = 64;
            const target = 118;
            const interval = setInterval(() => {
                if (current < target) {
                    current += 6;
                    if (speedElem) speedElem.textContent = String(current);
                } else {
                    clearInterval(interval);
                }
            }, 30);

            clearTimeout(revTimer);
            revTimer = setTimeout(() => {
                stage.classList.remove('is-accelerating');
                if (modeElem) modeElem.textContent = 'Cruising';
                if (revBtn) revBtn.textContent = 'Accelerate ⚡';
                if (speedElem) speedElem.textContent = '64';
            }, 3200);
        };

        revBtn?.addEventListener('click', triggerAccelerate);
    });
});


