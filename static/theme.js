(function () {
  // Toggle and persist theme. The <html> root gets the 'light' class for light mode.
  const themeToggle = document.getElementById('themeToggle');

  const applyTheme = (theme) => {
    document.documentElement.classList.toggle('light', theme === 'light');
    if (themeToggle) {
      themeToggle.textContent = theme === 'light' ? '☀️ Light Mode' : '🌙 Dark Mode';
    }
    localStorage.setItem('aseed_theme', theme);
  };

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const next = document.documentElement.classList.contains('light') ? 'dark' : 'light';
      applyTheme(next);
    });
  }

  // Initialize with saved preference (default: dark)
  applyTheme(localStorage.getItem('aseed_theme') || 'dark');
})();
