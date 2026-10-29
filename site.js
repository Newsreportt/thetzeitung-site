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

  // cover wall: rows of covers drifting right-to-left behind the text.
  // Covers are grouped by section (file name starts with a-, b- or c-) and
  // dealt out so that two covers of the same section never sit side by side.
  document.querySelectorAll('.wall[data-wall]').forEach(function (wall) {
    var list = wall.getAttribute('data-wall').split(',').filter(Boolean);
    if (!list.length) return;
    var rows = +wall.getAttribute('data-rows') || 1;

    function shuffle(a) {
      for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
      return a;
    }
    function kind(src) { return src.split('/').pop().charAt(0); }

    var groups = {};
    list.forEach(function (src) { (groups[kind(src)] = groups[kind(src)] || []).push(src); });
    var kinds = Object.keys(groups);

    function deal(count) {
      var queues = {}, seq = [], last = null;
      kinds.forEach(function (k) { queues[k] = shuffle(groups[k].slice()); });
      for (var n = 0; n < count; n++) {
        var cands = kinds.length > 1 ? kinds.filter(function (k) { return k !== last; }) : kinds;
        // weight by how many are still waiting, so every section gets its turn
        var total = 0; cands.forEach(function (k) { total += queues[k].length || groups[k].length; });
        var r = Math.random() * total, pick = cands[cands.length - 1];
        for (var c = 0; c < cands.length; c++) {
          r -= queues[cands[c]].length || groups[cands[c]].length;
          if (r < 0) { pick = cands[c]; break; }
        }
        if (!queues[pick].length) queues[pick] = shuffle(groups[pick].slice());
        seq.push(queues[pick].shift()); last = pick;
      }
      // the track loops, so the last cover meets the first: keep those apart too
      while (seq.length > 2 && kind(seq[0]) === kind(seq[seq.length - 1])) seq.pop();
      return seq;
    }

    for (var r = 0; r < rows; r++) {
      var seq = deal(24);
      var row = document.createElement('div'); row.className = 'row';
      var track = document.createElement('div'); track.className = 'track';
      track.style.setProperty('--dur', Math.round(230 + r * 60 + Math.random() * 20) + 's');
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
    var HOLD = 3000;
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

    // keep cycling; only rest while the tab is in the background
    document.addEventListener('visibilitychange', function () { document.hidden ? stop() : play(); });
    document.addEventListener('lightbox:open', stop);
    document.addEventListener('lightbox:close', play);

    show(0); play();
  }

  // archive filters: show one section's covers, or all
  var filters = document.querySelector('.filters');
  if (filters) {
    filters.addEventListener('click', function (e) {
      var btn = e.target.closest('button'); if (!btn) return;
      var k = btn.dataset.k;
      filters.querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b === btn); });
      document.querySelectorAll('.edition').forEach(function (ed) {
        var any = false;
        ed.querySelectorAll('figure').forEach(function (f) {
          var show = k === 'all' || f.dataset.k === k; f.classList.toggle('hide', !show); any = any || show;
        });
        ed.classList.toggle('hide', !any);
      });
    });
  }

  // cover lightbox: opens a cover full size; arrows, keys and swipes move through the others
  var box = document.querySelector('.lightbox');
  if (box) {
    var big = box.querySelector('img'), cap = box.querySelector('figcaption');
    var items = Array.prototype.slice.call(document.querySelectorAll('[data-zoom]')).map(function (a) {
      var im = a.querySelector('img');
      return { src: a.getAttribute('data-zoom'), title: a.getAttribute('aria-label') || (im ? im.alt : '') };
    });
    var cur = 0;

    function render() {
      var it = items[cur];
      big.src = it.src; big.alt = it.title;
      cap.innerHTML = it.title + '<small>' + (cur + 1) + ' of ' + items.length + '</small>';
      // warm the next one so the flip is instant
      var nx = new Image(); nx.src = items[(cur + 1) % items.length].src;
    }
    function open(i) { cur = i; render(); box.classList.add('on'); document.body.style.overflow = 'hidden'; document.dispatchEvent(new Event('lightbox:open')); }
    function close() { box.classList.remove('on'); document.body.style.overflow = ''; document.dispatchEvent(new Event('lightbox:close')); }
    function step(d) { cur = (cur + d + items.length) % items.length; render(); }

    document.querySelectorAll('[data-zoom]').forEach(function (a, i) {
      a.addEventListener('click', function (e) { e.preventDefault(); open(i); });
    });
    box.querySelector('.lb-prev').addEventListener('click', function (e) { e.stopPropagation(); step(-1); });
    box.querySelector('.lb-next').addEventListener('click', function (e) { e.stopPropagation(); step(1); });
    box.querySelector('.lb-close').addEventListener('click', function (e) { e.stopPropagation(); close(); });
    big.addEventListener('click', function (e) { e.stopPropagation(); close(); });
    box.addEventListener('click', function (e) { if (e.target === box) close(); });
    document.addEventListener('keydown', function (e) {
      if (!box.classList.contains('on')) return;
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowRight') step(1);
      else if (e.key === 'ArrowLeft') step(-1);
    });
    // swipe
    var x0 = null;
    box.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    box.addEventListener('touchend', function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0; x0 = null;
      if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1);
    }, { passive: true });
  }
})();
