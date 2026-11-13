document.querySelectorAll('form[data-endpoint]').forEach(function (form) {
  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var status = form.querySelector('.form-status');
    var endpoint = form.getAttribute('data-endpoint');
    if (form.website && form.website.value) return; // bot trap
    if (!endpoint) { status.textContent = 'Submissions open soon. Thanks for your patience.'; return; }
    var btn = form.querySelector('button[type=submit]');
    btn.disabled = true; status.textContent = 'Sending…';
    var data = new URLSearchParams(new FormData(form));
    data.append('page', location.pathname);
    fetch(endpoint, { method: 'POST', body: data, mode: 'no-cors' })
      .then(function () { location.href = '/thanks/'; })
      .catch(function () { status.textContent = 'Something went wrong. Please try again.'; btn.disabled = false; });
  });
});
