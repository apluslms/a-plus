(function () {
  const set_language_url = document.currentScript ?
    document.currentScript.getAttribute('data-set-lang') :
    document.querySelectorAll('script')[document.querySelectorAll('script').length - 1].getAttribute('data-set-lang');

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('a.change-language').forEach(function (elem) {
      const target_lang = elem.getAttribute('data-target-lang');
      elem.addEventListener('click', function (event) {
        event.preventDefault();
        fetch(set_language_url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ language: target_lang })
        })
        .then(function (response) {
          if (response.ok) {
            const href = elem.getAttribute('href');
            if (href === '#') {
              window.location.reload();
            } else {
              window.location.href = href;
            }
          }
        });
      });
    });
  });
})();
