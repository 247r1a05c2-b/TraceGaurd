(() => {
  const syncUi = () => {
    const banner = document.querySelector('.error.banner');
    if (banner) banner.style.display = 'none';

    const crumb = document.querySelector('.crumb');
    const isOverview = /\/\s*OVERVIEW\s*$/i.test(crumb?.textContent || '');
    document.querySelectorAll('.top-actions > button.primary').forEach((button) => {
      button.style.display = isOverview ? '' : 'none';
    });
  };

  const observer = new MutationObserver(syncUi);
  const start = () => {
    if (!document.body) return;
    observer.observe(document.body, { childList: true, subtree: true });
    syncUi();
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
