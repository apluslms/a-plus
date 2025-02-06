document.addEventListener('aplus:translation-ready', function() {
  document.querySelectorAll('.js-copy').forEach(function(element) {
    element.addEventListener('click', function() {
      copyToClipboard('.js-copy', '#api-access-token');
    });
  });
});
