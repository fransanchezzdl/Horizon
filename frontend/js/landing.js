const LANDING_REVEAL_SELECTOR = '.landing-reveal';

function initLandingThemeToggle() {
    const themeToggle = document.getElementById('landingThemeToggle');
    const themeLabel = document.getElementById('landingThemeLabel');
    const landingLogo = document.getElementById('landingLogo');

    if (!themeToggle) {
        return;
    }

    const syncThemeToggleState = () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        themeToggle.classList.toggle('is-dark', isDark);

        const nextThemeLabel = isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro';
        const currentThemeLabel = isDark ? 'Modo claro' : 'Modo oscuro';

        themeToggle.setAttribute('aria-label', nextThemeLabel);
        themeToggle.setAttribute('title', nextThemeLabel);

        if (themeLabel) {
            themeLabel.textContent = currentThemeLabel;
        }

        if (landingLogo) {
            const lightLogo = landingLogo.getAttribute('data-logo-light');
            const darkLogo = landingLogo.getAttribute('data-logo-dark');
            landingLogo.src = isDark ? darkLogo : lightLogo;
        }
    };

    syncThemeToggleState();

    themeToggle.addEventListener('click', () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const nextTheme = isDark ? 'light' : 'dark';

        if (window.setThemePreference) {
            window.setThemePreference(nextTheme);
        }

        syncThemeToggleState();
    });

    window.addEventListener('horizon:theme-changed', syncThemeToggleState);
}

function initLandingReveal() {
    const revealElements = document.querySelectorAll(LANDING_REVEAL_SELECTOR);
    if (!revealElements.length) {
        return;
    }

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) {
                return;
            }

            entry.target.classList.add('is-visible');
            obs.unobserve(entry.target);
        });
    }, {
        threshold: 0.14,
        rootMargin: '0px 0px -10% 0px',
    });

    revealElements.forEach((el) => observer.observe(el));
}

function animateCounter(counterElement, targetValue) {
    const durationMs = 850;
    const start = performance.now();

    const updateCounter = (now) => {
        const elapsed = now - start;
        const progress = Math.min(elapsed / durationMs, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const currentValue = Math.round(targetValue * eased);

        counterElement.textContent = String(currentValue);

        if (progress < 1) {
            requestAnimationFrame(updateCounter);
        }
    };

    requestAnimationFrame(updateCounter);
}

function initLandingLoadingState() {
    const loadingCards = document.querySelectorAll('[data-loading-card]');

    window.setTimeout(() => {
        loadingCards.forEach((card) => card.classList.remove('is-loading'));

        const counters = document.querySelectorAll('[data-counter]');
        counters.forEach((counterElement) => {
            const targetValue = Number(counterElement.getAttribute('data-counter') || '0');
            animateCounter(counterElement, targetValue);
        });
    }, 680);
}

function initLandingFaq() {
    const items = document.querySelectorAll('.landing-faq-item');

    items.forEach((item) => {
        const trigger = item.querySelector('.landing-faq-trigger');
        if (!trigger) {
            return;
        }

        trigger.addEventListener('click', () => {
            const isOpen = item.classList.contains('is-open');
            item.classList.toggle('is-open', !isOpen);
            trigger.setAttribute('aria-expanded', String(!isOpen));
        });
    });
}

function initLandingAnchorOffset() {
    const links = document.querySelectorAll('.landing-nav a[href^="#"]');

    links.forEach((link) => {
        link.addEventListener('click', (event) => {
            const hash = link.getAttribute('href');
            if (!hash || hash === '#') {
                return;
            }

            const section = document.querySelector(hash);
            if (!section) {
                return;
            }

            event.preventDefault();
            const y = section.getBoundingClientRect().top + window.scrollY - 92;
            window.scrollTo({ top: y, behavior: 'smooth' });
        });
    });
}

function initLandingPage() {
    initLandingThemeToggle();
    initLandingReveal();
    initLandingLoadingState();
    initLandingFaq();
    initLandingAnchorOffset();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLandingPage, { once: true });
} else {
    initLandingPage();
}
