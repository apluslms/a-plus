(function ($) {

  function showExtras(event) {
    event.preventDefault();
    const extras = $("#login-box-row").find(".extra-login");
    extras.show();
    $(".show-extra-login-btn").hide();
    extras.find(":input:visible").first().focus(); // focus for keyboard navigation
  }

  $(function () {
    const row = $("#login-box-row");
    const normal = row.find(".login-box").not(".extra-login");
    const errors = row.find(".extra-login").find(".alert");
    // if any of the extra logins have errors, none of them are hidden
    if (normal.length > 0 && errors.length == 0) {
      row.find(".extra-login").hide();
      $(".show-extra-login-btn").on("click", showExtras).show();

      if (normal.length % 2 == 0) {
        normal.last().after('<div class="clearfix visible-sm-block"></div>');
      }
    }
  });

}(jQuery));
