(function () {

  function showExtras(event) {
    event.preventDefault();
    const extras = document.querySelectorAll("#login-box-row .extra-login");
    extras.forEach(extra => extra.style.display = 'block');
    document.querySelector(".show-extra-login-btn").style.display = 'none';
    const firstVisibleInput = extras[0].querySelector(":input:visible");
    if (firstVisibleInput) {
      firstVisibleInput.focus(); // focus for keyboard navigation
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const row = document.getElementById("login-box-row");
    const normal = Array.from(row.querySelectorAll(".login-box")).filter(box => !box.classList.contains("extra-login"));
    const errors = row.querySelectorAll(".extra-login .alert");
    // if any of the extra logins have errors, none of them are hidden
    if (normal.length > 0 && errors.length === 0) {
      row.querySelectorAll(".extra-login").forEach(extra => extra.style.display = 'none');
      const showExtraLoginBtn = document.querySelector(".show-extra-login-btn");
      showExtraLoginBtn.addEventListener("click", showExtras);
      showExtraLoginBtn.style.display = 'block';

      if (normal.length % 2 === 0) {
        const clearfix = document.createElement('div');
        clearfix.className = 'clearfix visible-sm-block';
        normal[normal.length - 1].after(clearfix);
      }
    }
  });

}());
