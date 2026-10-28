// ===== Di Tzeitung — shared scripts =====
(function () {
  var y = document.getElementById('year'); if (y) y.textContent = new Date().getFullYear();

  // mobile menu
  var btn = document.querySelector('.menu-btn'), ul = document.querySelector('.nav ul');
  if (btn && ul) btn.addEventListener('click', function () { ul.classList.toggle('open'); });

  // active nav
  var here = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav a').forEach(function (a) { if (a.getAttribute('href') === here) a.classList.add('active'); });

  // carousel
  var stage = document.querySelector('.carousel .stage');
  if (stage) {
    var imgs = stage.querySelectorAll('img'), thumbs = document.querySelectorAll('.carousel .thumbs img'), i = 0;
    function show(n) {
      i = (n + imgs.length) % imgs.length;
      imgs.forEach(function (im, k) { im.classList.toggle('on', k === i); });
      thumbs.forEach(function (t, k) { t.classList.toggle('on', k === i); });
    }
    stage.querySelector('.prev').addEventListener('click', function () { show(i - 1); });
    stage.querySelector('.next').addEventListener('click', function () { show(i + 1); });
    thumbs.forEach(function (t) { t.addEventListener('click', function () { show(+t.dataset.i); }); });
  }
})();
