(() => {
  const markAgents = () => {
    const nodes = [...document.querySelectorAll('#root *')].filter(el => el.children.length === 0 && el.textContent?.trim().toLowerCase() === 'complete');
    nodes.forEach(node => {
      if (node.dataset.agentVerified === '1') return;
      node.dataset.agentVerified = '1';
      node.textContent = '✓ Checked';
      node.classList.add('agent-check-status');
      const card = node.closest('[class*="card"], [class*="row"], section, article, div');
      if (card) card.classList.add('agent-verified-card');
    });
  };
  markAgents();
  new MutationObserver(markAgents).observe(document.getElementById('root') || document.body, {subtree:true, childList:true, characterData:true});
})();
