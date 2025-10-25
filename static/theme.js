(function () {
    const themeToggle = document.getElementById('themeToggle');
    const applyTheme = (theme) => {
        document.documentElement.classList.toggle('light', theme === 'light');
        if (themeToggle) themeToggle.textContent = theme === 'light' ? '☀️ Light Mode' : '🌙 Dark Mode';
        localStorage.setItem('aseed_theme', theme);
    };
    if (themeToggle) {
        themeToggle.addEventListener('click', () => applyTheme(document.documentElement.classList.contains('light') ? 'dark' : 'light'));
    }
    applyTheme(localStorage.getItem('aseed_theme') || 'dark');
})();