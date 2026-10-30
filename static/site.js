(() => {
  const root = document.documentElement;
  const toggle = document.querySelector('.theme-toggle');
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  let savedTheme = null;
  try { savedTheme = localStorage.getItem('theme'); } catch (_) { /* Storage may be unavailable. */ }
  if (savedTheme === 'light' || savedTheme === 'dark') root.dataset.theme = savedTheme;
  const updateThemeButton = () => {
    const dark = root.dataset.theme ? root.dataset.theme === 'dark' : media.matches;
    toggle.textContent = dark ? 'پوسته روشن' : 'پوسته تیره';
    toggle.setAttribute('aria-pressed', String(dark));
  };
  if (toggle) {
    updateThemeButton();
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      const dark = root.dataset.theme ? root.dataset.theme === 'dark' : media.matches;
      root.dataset.theme = dark ? 'light' : 'dark';
      try { localStorage.setItem('theme', root.dataset.theme); } catch (_) { /* Preference lasts for this page. */ }
      updateThemeButton();
    });
    media.addEventListener('change', updateThemeButton);
  }


})();
