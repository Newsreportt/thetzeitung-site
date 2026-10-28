// ===== The Tzeitung — shared scripts =====
(function () {
  var y = document.getElementById('year'); if (y) y.textContent = new Date().getFullYear();

  // mobile menu
  var btn = document.querySelector('.menu-btn'), nav = document.querySelector('.top nav');
  if (btn && nav) btn.addEventListener('click', function () {
    var open = nav.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  // active link
  var here = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.top nav a').forEach(function (a) {
    if (a.getAttribute('href') === here && !a.classList.contains('cta')) a.classList.add('active');
  });

  // cover lightbox
  var box = document.querySelector('.lightbox');
  if (box) {
    var big = box.querySelector('img');
    document.querySelectorAll('[data-zoom]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        big.src = a.getAttribute('data-zoom');
        big.alt = a.querySelector('img') ? a.querySelector('img').alt : '';
        box.classList.add('on');
      });
    });
    box.addEventListener('click', function () { box.classList.remove('on'); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') box.classList.remove('on'); });
  }
})();
