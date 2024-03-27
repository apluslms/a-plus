(function ($) {

  function showExtras(event) {
    event.preventDefault();
    const extras = $("#login-box-row").find(".extra-login");
    extras.show();
    $(".show-extra-login-btn").hide();
    extras.find(":input:visible").first().focus(); // focus for keyboard navigation
  }
  
  document.addEventListener('DOMContentLoaded', function() {
    var loginLink = document.getElementById('loginLink');
    if (loginLink) {
      loginLink.addEventListener('click', function(event) {
			  if (!window.location.pathname.includes("/logout")) {
          event.preventDefault();
      	  var currentUrl = window.location.href;
          var loginUrl = this.getAttribute('href') + '?next=' + encodeURIComponent(currentUrl);
      	  window.location.href = loginUrl;
			  }
      });
    }
  });

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
