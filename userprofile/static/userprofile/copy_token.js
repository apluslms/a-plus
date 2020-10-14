(function ($) {
  $(document).on('aplus:translation-ready', function() {

    $(".js-copy").click(function () {
      copyToClipboard('.js-copy', '#api-access-token');
    });
  });

})(jQuery);
