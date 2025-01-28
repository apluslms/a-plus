document.getElementById('cookie-notice-dismiss').addEventListener('click', function() {
  document.getElementById('cookie-notice').style.display = 'none';

  document.cookie = "cookiesConfirmed=true; max-age=" + (60 * 60 * 24 * 365);
});


if (document.cookie.includes('cookiesConfirmed')) {
  document.getElementById('cookie-notice').style.display = 'none';
}
