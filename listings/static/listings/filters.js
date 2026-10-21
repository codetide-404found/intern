/* Optional: submit the filter form as soon as a dropdown changes. The page works without this. */
(function () {
  var form = document.getElementById('filters');
  if (!form) return;
  document.documentElement.classList.add('js');
  form.querySelectorAll('select').forEach(function (s) {
    s.addEventListener('change', function () { form.submit(); });
  });
})();
