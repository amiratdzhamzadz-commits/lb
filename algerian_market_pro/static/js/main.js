/* سوق الماكينات الجزائري PRO - Main JavaScript (Vanilla JS) */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Algerian Market PRO initialized.');

    // ===== LANGUAGE SWITCHER =====
    const langSwitchers = document.querySelectorAll('.lang-switcher > a.nav-link');
    langSwitchers.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const menu = this.nextElementSibling;
            if (menu && menu.classList.contains('dropdown-menu')) {
                // Close others
                document.querySelectorAll('.dropdown-menu.show').forEach(m => {
                    if (m !== menu) m.classList.remove('show');
                });
                // Toggle this
                menu.classList.toggle('show');
            }
        });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.lang-switcher')) {
            document.querySelectorAll('.lang-switcher .dropdown-menu').forEach(m => {
                m.classList.remove('show');
            });
        }
        if (!e.target.closest('.theme-switcher')) {
            document.querySelectorAll('.theme-dropdown').forEach(m => {
                m.classList.remove('show');
            });
        }
    });

    // Close dropdown when clicking a language option
    document.querySelectorAll('.lang-switcher .dropdown-item').forEach(function(item) {
        item.addEventListener('click', function() {
            document.querySelectorAll('.lang-switcher .dropdown-menu').forEach(m => m.classList.remove('show'));
        });
    });

    // ===== THEME SWITCHER =====
    const THEME_STORAGE_KEY = 'algerian_market_theme';
    const themeToggleBtn = document.querySelector('.theme-toggle-btn');
    const themeDropdown = document.querySelector('.theme-dropdown');
    const themeOptions = document.querySelectorAll('.theme-option');

    function getHour() { return new Date().getHours(); }
    function isNightTime() { const h = getHour(); return h >= 19 || h < 7; }

    function applyTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else if (theme === 'light') {
            document.documentElement.removeAttribute('data-theme');
        } else if (theme === 'auto') {
            if (isNightTime()) {
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.removeAttribute('data-theme');
            }
        }
    }

    function updateThemeButton(theme) {
        if (!themeToggleBtn) return;
        const icon = themeToggleBtn.querySelector('.theme-icon');
        const label = themeToggleBtn.querySelector('.theme-label');
        if (!icon || !label) return;

        const darkLabel = themeToggleBtn.getAttribute('data-dark-label') || 'Dark';
        const lightLabel = themeToggleBtn.getAttribute('data-light-label') || 'Light';
        const autoLabel = themeToggleBtn.getAttribute('data-auto-label') || 'Auto';

        icon.classList.remove('fa-sun', 'fa-moon', 'fa-circle-half-stroke');

        if (theme === 'dark') {
            icon.classList.add('fa-moon');
            label.textContent = darkLabel;
        } else if (theme === 'light') {
            icon.classList.add('fa-sun');
            label.textContent = lightLabel;
        } else if (theme === 'auto') {
            icon.classList.add('fa-circle-half-stroke');
            label.textContent = autoLabel;
        }
    }

    function updateActiveOption(theme) {
        themeOptions.forEach(opt => {
            if (opt.getAttribute('data-theme-value') === theme) {
                opt.classList.add('active');
            } else {
                opt.classList.remove('active');
            }
        });
    }

    function setTheme(theme) {
        localStorage.setItem(THEME_STORAGE_KEY, theme);
        applyTheme(theme);
        updateThemeButton(theme);
        updateActiveOption(theme);
    }

    function initTheme() {
        let savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
        if (!savedTheme) {
            savedTheme = 'auto';
            localStorage.setItem(THEME_STORAGE_KEY, savedTheme);
        }
        applyTheme(savedTheme);
        updateThemeButton(savedTheme);
        updateActiveOption(savedTheme);
    }

    // Theme dropdown toggle
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (themeDropdown) {
                // Close others
                document.querySelectorAll('.theme-dropdown.show, .lang-switcher .dropdown-menu.show').forEach(m => m.classList.remove('show'));
                themeDropdown.classList.toggle('show');
            }
        });
    }

    // Theme option click
    themeOptions.forEach(function(opt) {
        opt.addEventListener('click', function(e) {
            e.preventDefault();
            const theme = this.getAttribute('data-theme-value');
            setTheme(theme);
            if (themeDropdown) themeDropdown.classList.remove('show');
        });
    });

    // Auto-switch check
    function autoThemeCheck() {
        const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
        if (savedTheme === 'auto') {
            applyTheme('auto');
            // Update icon to reflect actual state
            if (themeToggleBtn) {
                const icon = themeToggleBtn.querySelector('.theme-icon');
                if (icon) {
                    icon.classList.remove('fa-sun', 'fa-moon', 'fa-circle-half-stroke');
                    if (isNightTime()) {
                        icon.classList.add('fa-moon');
                    } else {
                        icon.classList.add('fa-sun');
                    }
                }
            }
        }
    }

    setInterval(autoThemeCheck, 60000);
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) autoThemeCheck();
    });

    // Initialize
    initTheme();

    // ===== NOTIFICATION POLLING =====
    function updateUnreadCount() {
        fetch('/notifications/unread-count')
            .then(res => res.json())
            .then(data => {
                const badge = document.querySelector('.notification-badge');
                const count = data.count;
                const bellIcon = document.querySelector('.fa-bell');
                
                if (count > 0) {
                    if (badge) {
                        badge.textContent = count;
                    } else if (bellIcon) {
                        const newBadge = document.createElement('span');
                        newBadge.className = 'badge bg-danger notification-badge';
                        newBadge.textContent = count;
                        bellIcon.parentElement.appendChild(newBadge);
                    }
                } else {
                    if (badge) badge.remove();
                }
            })
            .catch(err => console.error('Notification error:', err));
    }
    
    if (typeof fetch !== 'undefined') {
        setInterval(updateUnreadCount, 30000);
    }

    // Auto-dismiss alerts
    setTimeout(function() {
        document.querySelectorAll('.alert-dismissible').forEach(alert => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        });
    }, 5000);

    // Tooltip init (Bootstrap 5)
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            new bootstrap.Tooltip(el);
        });
    }

    // Confirm dialogs
    document.querySelectorAll('a[onclick^="return confirm"]').forEach(link => {
        link.addEventListener('click', function(e) {
            const msg = this.getAttribute('data-confirm-message') || 'هل أنت متأكد؟';
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });
});

// Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/sw.js').then(reg => {
            console.log('SW registered:', reg.scope);
        }).catch(err => {
            console.log('SW error:', err);
        });
    });
}