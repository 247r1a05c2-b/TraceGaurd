(() => {
  const token = localStorage.getItem('tg_token');
  if (!token) return;
  fetch('/api/v1/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store'
  }).then((response) => {
    if (response.status === 401) {
      localStorage.removeItem('tg_token');
      localStorage.removeItem('tg_email');
      window.location.reload();
    }
  }).catch(() => {
    // Do not log the user out for a transient network failure.
  });
})();
