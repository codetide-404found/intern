/* "Copy address" buttons. If the browser blocks copying, the address is selected so it can be copied by hand. */
(function () {
  document.querySelectorAll('[data-copy]').forEach(function (btn) {
    var label = btn.textContent;
    function done(text) { btn.textContent = text; setTimeout(function () { btn.textContent = label; }, 1800); }
    function select() {
      var el = document.getElementById(btn.getAttribute('data-target'));
      if (!el) return;
      var r = document.createRange(); r.selectNodeContents(el);
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      done('Selected, press copy');
    }
    btn.addEventListener('click', function () {
      try {
        navigator.clipboard.writeText(btn.getAttribute('data-copy')).then(function () { done('Copied'); }, select);
      } catch (e) { select(); }
    });
  });
})();
