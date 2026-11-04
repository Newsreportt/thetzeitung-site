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
    var dims = {};
    var list = wall.getAttribute('data-wall').split(',').filter(Boolean).map(function (e) {
      var p = e.split('|'); if (p[1]) { var wh = p[1].split('x'); dims[p[0]] = (+wh[0]) / (+wh[1]); }
      return p[0];
    });
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

    // every picture gets its shape up front, so the rows are laid out and start drifting at once;
    // each cover fades in as it arrives, so nothing jumps while the pictures load
    for (var r = 0; r < rows; r++) {
      var seq = deal(24);
      var row = document.createElement('div'); row.className = 'row';
      var track = document.createElement('div'); track.className = 'track';
      track.style.setProperty('--dur', Math.round(230 + r * 60 + Math.random() * 20) + 's');
      seq.concat(seq).forEach(function (src, i) {       // twice over, so the loop never jumps
        var im = new Image(); im.alt = ''; im.decoding = 'async';
        im.setAttribute('fetchpriority', r === 0 && i < 10 ? 'high' : 'low');   // what is on screen first comes first
        if (dims[src]) im.style.aspectRatio = dims[src];
        im.onload = function () { im.classList.add('in'); };
        im.src = src; if (im.complete && im.naturalWidth) im.classList.add('in');
        track.appendChild(im);
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

  // archive: section filter + search box work together
  var filters = document.querySelector('.filters'), search = document.getElementById('cover-search');
  if (filters || search) {
    var hits = document.getElementById('search-hits');
    var norm = function (s) { return s.toLowerCase().replace(/[\u0591-\u05c7]/g, '').replace(/["\u05f4\u05f3'\u2019\u201c\u201d]/g, ''); };
    var figs = Array.prototype.slice.call(document.querySelectorAll('.edition figure')).map(function (f) {
      return { el: f, k: f.dataset.k, s: '' };
    });
    // the words on every cover live in a separate index, fetched the first time someone searches
    var index = null, loading = null;
    function loadIndex() {
      if (index || loading || !search) return loading;
      loading = fetch(search.dataset.index).then(function (r) { return r.json(); }).then(function (list) {
        index = list; figs.forEach(function (f, i) { f.s = norm(list[i] || ''); }); apply();
      }).catch(function () { loading = null; });
      return loading;
    }
    var kind = 'all';
    function apply() {
      var q = search ? norm(search.value.trim()) : '';
      var terms = q ? q.split(/\s+/) : [];
      if (terms.length && !index) { loadIndex(); return; }
      var shown = 0;
      figs.forEach(function (f) {
        var ok = (kind === 'all' || f.k === kind) && terms.every(function (t) { return f.s.indexOf(t) !== -1; });
        f.el.classList.toggle('hide', !ok); if (ok) shown++;
      });
      document.querySelectorAll('.edition').forEach(function (ed) { ed.classList.toggle('hide', !ed.querySelector('figure:not(.hide)')); });
      document.querySelectorAll('.month').forEach(function (m) { m.classList.toggle('hide', !m.querySelector('.edition:not(.hide)')); });
      document.querySelectorAll('.year').forEach(function (v) { v.classList.toggle('hide', !v.querySelector('.edition:not(.hide)')); });
      var years = document.querySelector('.years');
      if (years) years.querySelectorAll('a').forEach(function (a) {
        var y = document.getElementById(a.getAttribute('href').slice(1));
        a.classList.toggle('dim', !!(y && y.classList.contains('hide')));
      });
      if (hits) hits.textContent = terms.length ? (shown ? shown + (shown === 1 ? ' cover' : ' covers') : 'No covers match') : '';
      var page = document.querySelector('.archive'); if (page) page.classList.toggle('empty', shown === 0);
    }
    if (filters) filters.addEventListener('click', function (e) {
      var btn = e.target.closest('button'); if (!btn) return;
      kind = btn.dataset.k;
      filters.querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b === btn); });
      apply();
    });
    // jump to a year from the sticky bar, and a button back to the top once the page is scrolled
    var jump = document.getElementById('year-jump');
    if (jump) jump.addEventListener('change', function () {
      var y = jump.value && document.getElementById(jump.value);
      if (y) y.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    var toTop = document.querySelector('.to-top');
    if (toTop) {
      var tick = false;
      window.addEventListener('scroll', function () {
        if (tick) return; tick = true;
        requestAnimationFrame(function () { toTop.classList.toggle('on', window.scrollY > 700); tick = false; });
      }, { passive: true });
      toTop.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'instant' }); if (jump) jump.value = ''; });
    }
    if (search) {
      var wait = null;
      search.addEventListener('focus', loadIndex);
      search.addEventListener('input', function () { clearTimeout(wait); wait = setTimeout(apply, 120); });
      search.addEventListener('keydown', function (e) { if (e.key === 'Escape') { search.value = ''; apply(); } });
    }
  }

  // no copying or cutting of the page text (the forms stay usable)
  function inField(el) { return el && el.closest && el.closest('input, textarea, select'); }
  ['copy', 'cut', 'selectstart'].forEach(function (ev) {
    document.addEventListener(ev, function (e) { if (!inField(e.target)) e.preventDefault(); });
  });

  // the covers are for looking at, not for saving: no context menu or dragging on them
  var GUARD = '.ed-covers, .stage, .wall, .lightbox, .showcase';
  document.addEventListener('contextmenu', function (e) { if (e.target.closest && e.target.closest(GUARD)) e.preventDefault(); });
  document.addEventListener('dragstart', function (e) { if (e.target.closest && e.target.closest(GUARD)) e.preventDefault(); });

  // cover lightbox: opens a cover full size; arrows, keys and swipes move through the others;
  // a click (or tap) zooms in on that spot, drag or scroll moves around, pinch zooms on a phone
  var box = document.querySelector('.lightbox');
  if (box) {
    var big = box.querySelector('img'), cap = box.querySelector('figcaption'), pic = box.querySelector('.lb-pic'), shield = box.querySelector('.shield');
    var items = Array.prototype.slice.call(document.querySelectorAll('[data-zoom]')).map(function (a) {
      var im = a.querySelector('img');
      return { src: a.getAttribute('data-zoom'), hi: a.getAttribute('data-big'), title: a.getAttribute('aria-label') || (im ? im.alt : '') };
    });
    var cur = 0;
    var scale = 1, tx = 0, ty = 0, MAX = 4;

    function place() {
      pic.style.transform = scale === 1 ? '' : 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')';
      pic.classList.toggle('zoomed', scale !== 1);
    }
    function reset() { scale = 1; tx = 0; ty = 0; place(); }
    function clampPan() {
      var r = pic.getBoundingClientRect(), vw = window.innerWidth, vh = window.innerHeight;
      // keep the picture covering the screen while it is bigger than it, centred otherwise
      var w = r.width, h = r.height;
      var minX = Math.min(0, vw - w) / 2, maxX = -minX, minY = Math.min(0, vh - h) / 2, maxY = -minY;
      tx = Math.max(minX, Math.min(maxX, tx)); ty = Math.max(minY, Math.min(maxY, ty));
    }
    function zoomAt(factor, cx, cy) {
      var next = Math.max(1, Math.min(MAX, scale * factor));
      if (next === scale) return;
      var r = pic.getBoundingClientRect();
      // the point under the cursor stays under the cursor
      var ox = cx - (r.left + r.width / 2), oy = cy - (r.top + r.height / 2);
      var k = next / scale;
      tx = tx - ox * (k - 1); ty = ty - oy * (k - 1);
      scale = next;
      if (scale === 1) { tx = 0; ty = 0; }
      if (scale > 1 && items[cur].hi && big.getAttribute('src') !== items[cur].hi) big.src = items[cur].hi;   // the sharper copy
      place(); clampPan(); place();
    }

    function render() {
      var it = items[cur];
      reset();
      big.src = it.src; big.alt = it.title;
      cap.textContent = it.title;
      var nx = new Image(); nx.src = items[(cur + 1) % items.length].src;   // warm the next one
    }
    function open(i) { cur = i; render(); box.classList.add('on'); document.body.style.overflow = 'hidden'; document.dispatchEvent(new Event('lightbox:open')); }
    function close() { box.classList.remove('on'); document.body.style.overflow = ''; reset(); document.dispatchEvent(new Event('lightbox:close')); }
    function step(d) { cur = (cur + d + items.length) % items.length; render(); }

    document.querySelectorAll('[data-zoom]').forEach(function (a, i) {
      a.addEventListener('click', function (e) { e.preventDefault(); open(i); });
    });
    box.querySelector('.lb-prev').addEventListener('click', function (e) { e.stopPropagation(); step(-1); });
    box.querySelector('.lb-next').addEventListener('click', function (e) { e.stopPropagation(); step(1); });
    box.querySelector('.lb-close').addEventListener('click', function (e) { e.stopPropagation(); close(); });
    var zin = box.querySelector('.lb-in'), zout = box.querySelector('.lb-out');
    if (zin) zin.addEventListener('click', function (e) { e.stopPropagation(); zoomAt(1.6, window.innerWidth / 2, window.innerHeight / 2); });
    if (zout) zout.addEventListener('click', function (e) { e.stopPropagation(); zoomAt(1 / 1.6, window.innerWidth / 2, window.innerHeight / 2); });
    box.addEventListener('click', function (e) { if (e.target === box) close(); });

    // mouse: click zooms in on the spot (or back out when already close), drag pans, wheel zooms
    var drag = null, moved = false;
    shield.addEventListener('mousedown', function (e) { if (e.button !== 0) return; drag = { x: e.clientX, y: e.clientY, tx: tx, ty: ty }; moved = false; e.preventDefault(); });
    window.addEventListener('mousemove', function (e) {
      if (!drag) return;
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
      if (scale > 1) { tx = drag.tx + dx; ty = drag.ty + dy; clampPan(); place(); }
    });
    window.addEventListener('mouseup', function (e) {
      if (!drag) return; drag = null;
      if (moved) return;
      e.stopPropagation();
      if (scale >= MAX - 0.01) reset(); else zoomAt(scale === 1 ? 2.5 : 1.6, e.clientX, e.clientY);
    });
    shield.addEventListener('click', function (e) { e.stopPropagation(); });
    box.addEventListener('wheel', function (e) {
      if (!box.classList.contains('on')) return;
      e.preventDefault();
      zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX, e.clientY);
    }, { passive: false });

    // touch: one finger pans (or swipes to the next cover when not zoomed), two fingers pinch, double tap zooms
    var t0 = null, pinch = null, lastTap = 0;
    box.addEventListener('touchstart', function (e) {
      if (e.touches.length === 2) {
        var a = e.touches[0], b = e.touches[1];
        pinch = { d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), s: scale, cx: (a.clientX + b.clientX) / 2, cy: (a.clientY + b.clientY) / 2 };
        t0 = null;
      } else if (e.touches.length === 1) {
        t0 = { x: e.touches[0].clientX, y: e.touches[0].clientY, tx: tx, ty: ty, moved: false, t: Date.now() };
      }
    }, { passive: true });
    box.addEventListener('touchmove', function (e) {
      if (pinch && e.touches.length === 2) {
        e.preventDefault();
        var a = e.touches[0], b = e.touches[1];
        var d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        var want = Math.max(1, Math.min(MAX, pinch.s * d / pinch.d));
        zoomAt(want / scale, pinch.cx, pinch.cy);
      } else if (t0 && e.touches.length === 1) {
        var dx = e.touches[0].clientX - t0.x, dy = e.touches[0].clientY - t0.y;
        if (Math.abs(dx) + Math.abs(dy) > 6) t0.moved = true;
        if (scale > 1) { e.preventDefault(); tx = t0.tx + dx; ty = t0.ty + dy; clampPan(); place(); }
      }
    }, { passive: false });
    box.addEventListener('touchend', function (e) {
      if (pinch) { if (e.touches.length < 2) pinch = null; return; }
      if (!t0) return;
      var dx = e.changedTouches[0].clientX - t0.x, dy = e.changedTouches[0].clientY - t0.y;
      var tap = !t0.moved && Date.now() - t0.t < 350;
      var s = t0; t0 = null;
      if (tap) {
        var now = Date.now();
        if (now - lastTap < 320) { if (scale > 1) reset(); else zoomAt(2.5, e.changedTouches[0].clientX, e.changedTouches[0].clientY); lastTap = 0; }
        else lastTap = now;
        return;
      }
      if (scale === 1 && Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) step(dx < 0 ? 1 : -1);
    }, { passive: true });

    document.addEventListener('keydown', function (e) {
      if (!box.classList.contains('on')) return;
      if (e.key === 'Escape') { if (scale > 1) reset(); else close(); }
      else if (e.key === 'ArrowRight') step(1);
      else if (e.key === 'ArrowLeft') step(-1);
      else if (e.key === '+' || e.key === '=') zoomAt(1.6, window.innerWidth / 2, window.innerHeight / 2);
      else if (e.key === '-') zoomAt(1 / 1.6, window.innerWidth / 2, window.innerHeight / 2);
    });
  }
})();
