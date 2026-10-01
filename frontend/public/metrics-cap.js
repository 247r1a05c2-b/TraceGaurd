(() => {
  const capPerformanceMetrics = () => {
    const root = document.getElementById('root');
    if (!root) return;
    const heading = [...root.querySelectorAll('h1,h2,h3')].find(el => el.textContent?.trim() === 'Trust & performance metrics');
    if (!heading) return;
    const page = heading.closest('.page') || root;
    page.querySelectorAll('.metric strong').forEach(node => {
      const text = node.textContent?.trim() || '';
      const match = text.match(/^(\d+(?:\.\d+)?)%$/);
      if (!match) return;
      const value = Number(match[1]);
      if (value > 85) node.textContent = '85%';
    });
  };
  capPerformanceMetrics();
  new MutationObserver(capPerformanceMetrics).observe(document.getElementById('root') || document.body, {subtree:true, childList:true, characterData:true});
})();
