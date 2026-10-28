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

  // cover wall: rows of shuffled covers drifting right-to-left behind the text
  document.querySelectorAll('.wall[data-wall]').forEach(function (wall) {
    var list = wall.getAttribute('data-wall').split(',').filter(Boolean);
    if (!list.length) return;
    var rows = +wall.getAttribute('data-rows') || 1;

    function shuffle(a) {
      for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
      return a;
    }
    for (var r = 0; r < rows; r++) {
      var seq = [];
      while (seq.length < 16) {                       // enough covers to span any screen
        var batch = shuffle(list.slice());
        if (seq.length && batch[0] === seq[seq.length - 1]) batch.push(batch.shift());
        seq = seq.concat(batch);
      }
      var row = document.createElement('div'); row.className = 'row';
      var track = document.createElement('div'); track.className = 'track';
      track.style.setProperty('--dur', Math.round(110 + r * 35 + Math.random() * 20) + 's');
      seq.concat(seq).forEach(function (src) {          // twice over, so the loop never jumps
        var im = new Image(); im.src = src; im.alt = ''; im.decoding = 'async'; track.appendChild(im);
      });
      row.appendChild(track); wall.appendChild(row);
    }
  });

  // cover showcase: fades from one cover to the next on its own
  var showcase = document.getElementById('showcase');
  if (showcase) {
    var slides = showcase.querySelectorAll('.slide');
    var picks = showcase.querySelectorAll('.pick');
    var at = 0, timer = null;
    var HOLD = 5000;
    var still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function show(n) {
      at = (n + slides.length) % slides.length;
      slides.forEach(function (s, k) { s.classList.toggle('on', k === at); });
      picks.forEach(function (p, k) {
        p.classList.remove('on');
        if (k === at) { void p.offsetWidth; p.classList.add('on'); }
      });
    }
    function play() { stop(); if (!still) timer = setInterval(function () { show(at + 1); }, HOLD); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }

    picks.forEach(function (p) {
      p.addEventListener('click', function () { show(+p.dataset.i); play(); });
    });

    // pause while the reader is hovering or has the tab in the background
    showcase.addEventListener('mouseenter', stop);
    showcase.addEventListener('mouseleave', play);
    document.addEventListener('visibilitychange', function () { document.hidden ? stop() : play(); });

    show(0); play();
  }

  // cover lightbox
  var box = document.querySelector('.lightbox');
  if (box) {
    var big = box.querySelector('img');
    document.querySelectorAll('[data-zoom]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        big.src = a.getAttribute('data-zoom');
        var inner = a.querySelector('img');
        big.alt = inner ? inner.alt : '';
        box.classList.add('on');
      });
    });
    box.addEventListener('click', function () { box.classList.remove('on'); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') box.classList.remove('on'); });
  }
})();
