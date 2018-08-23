(function ($) {
  const set_language_url = (document.currentScript ?
    $(document.currentScript) :
    $('script').last()) // Ugly solution for IE11
    .attr('data-set-lang');

  $(function () {
    $('a.change-language').each(function (i, elem) {
      const $elem = $(elem);
      const target_lang = $elem.attr('data-target-lang');
      $elem.on('click', function () {
        $.post(set_language_url, { language: target_lang })
          .done(function () {
            const href = $elem.attr('href');
            // href="#" means "this page, but in another language"
            if (href === '#') {
              window.location.reload();
            } else {
              window.location.href = href;
            }
          });
        return false;
      });
    });
  });
})(jQuery);
