(() => {
  const key = 'tracegaurd-theme'
  const apply = (theme) => {
    document.documentElement.dataset.theme = theme
    const button = document.querySelector('[data-tracegaurd-theme]')
    if (button) {
      const light = theme === 'light'
      button.setAttribute('aria-label', light ? 'Switch to dark theme' : 'Switch to light theme')
      button.setAttribute('title', light ? 'Switch to dark theme' : 'Switch to light theme')
      button.innerHTML = light ? '<span aria-hidden="true">☾</span><b>Dark</b>' : '<span aria-hidden="true">☀</span><b>Light</b>'
    }
  }

  const initial = localStorage.getItem(key) || 'dark'
  apply(initial)

  const mount = () => {
    if (document.querySelector('[data-tracegaurd-theme]')) return
    const button = document.createElement('button')
    button.type = 'button'
    button.dataset.tracegaurdTheme = 'true'
    button.className = 'theme-toggle'
    button.addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light'
      localStorage.setItem(key, next)
      apply(next)
    })
    document.body.appendChild(button)
    apply(document.documentElement.dataset.theme || initial)
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount)
  else mount()
})()
