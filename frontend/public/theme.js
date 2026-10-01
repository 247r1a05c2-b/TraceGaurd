(() => {
  const key = 'tg_theme'
  const legacyKey = 'tracegaurd-theme'
  const initial = localStorage.getItem(key) || localStorage.getItem(legacyKey) || 'dark'
  document.documentElement.dataset.theme = initial
  localStorage.setItem(key, initial)
})()
