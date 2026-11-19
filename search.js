// The archive search: a word, and the headlines it stands in — which week, which section of the
// paper, which page. The index holds the headlines and the words of every page; nothing else of
// an article is served, here or anywhere. From a result the reader goes to that edition and can
// buy its PDF.
(function () {
  'use strict';
  var FN = '/.netlify/functions/search-index?s=';
  var meta = null, slices = {}, pending = {}, years = {}, PER_PAGE = 25;
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var SECTION = { a: 'The main section', b: 'Yiddishe Tzeit', c: 'Chassidishe Tzeit', d: 'Yom Tov Tzeit', e: 'Section E', f: 'Section F', g: 'Section G', t: 'Torah Tzeit', k: 'Kehila Tzeit', sup: 'The supplement' };

  function el(tag, attrs, kids) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') e.textContent = attrs[k]; else if (k === 'html') e.innerHTML = attrs[k]; else e.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return e;
  }
  function niceDate(iso) { var p = iso.split('-'); return MONTHS[+p[1] - 1] + ' ' + (+p[2]) + ', ' + p[0]; }

  // ---- the same filing the index was built with ------------------------------------------
  function key(word) {
    var k = word.replace(/['’׳"״&.\-–\/]/g, '')
      .replace(/ך/g, 'כ').replace(/ם/g, 'מ').replace(/ן/g, 'נ').replace(/ף/g, 'פ').replace(/ץ/g, 'צ');
    return /^[\x00-\x7F]*$/.test(k) ? k.toLowerCase() : k;
  }
  function words(q) {
    var found = q.match(/[א-ת]+(?:['’׳"״][א-ת]+)*|[A-Za-z][A-Za-z'&.]+[A-Za-z]|\d{3,}(?:[-.–\/]\d{3,})*/g) || [];
    return found.map(function (w) { return { typed: w, k: key(w) }; })
      .filter(function (w) { return w.k.length >= 2; });
  }

  function get(s) {
    if (slices[s]) return Promise.resolve(slices[s]);
    if (pending[s]) return pending[s];
    var v = meta && meta.built ? '&v=' + encodeURIComponent(meta.built) : '';
    pending[s] = fetch(FN + encodeURIComponent(s) + v).then(function (r) { return r.json(); }).then(function (j) {
      slices[s] = j; delete pending[s]; return j;
    }, function () { delete pending[s]; return {}; });
    return pending[s];
  }

  /** The postings of one word: [{ed, n, nums}] — nums are headline ids, or pages in the body index. */
  function postings(slice, word) {
    var flat = slice[word]; if (!flat) return [];
    var out = [], i = 0, ed = 0;
    while (i < flat.length) {
      ed += flat[i++];
      var n = flat[i++], count = flat[i++], nums = [];
      for (var j = 0; j < count; j++) nums.push(flat[i++]);
      out.push({ ed: ed, n: n, nums: nums });
    }
    return out;
  }

  /** Every word in the slice that is, or is built on, what was typed. */
  function matches(slice, word, loose) {
    var exact = slice[word] ? [word] : [], grown = [];
    if (word.length >= 3) for (var k in slice) if (k !== word && k.indexOf(word) === 0) grown.push(k);
    var byLen = function (a, b) { return a.length - b.length; };
    grown.sort(byLen);
    var out = exact.concat(grown.slice(0, 80));
    if (!out.length && loose) {
      for (var k2 in slice) if (k2.indexOf(word) > 0) out.push(k2);
      out.sort(byLen); out = out.slice(0, 40);
    }
    return out;
  }

  /** Where the words stand: in headlines (`h`) or anywhere on a page (`w`). */
  function look(ws, kind) {
    var pre = kind === 'h' ? 'h:' : '';
    return Promise.all(ws.map(function (w) { return get(pre + w.k.slice(0, 2)); })).then(function (sl) {
      var per = ws.map(function (w, i) {
        var hit = matches(sl[i], w.k, ws.length === 1), by = {};
        hit.forEach(function (term) {
          postings(sl[i], term).forEach(function (p) {
            var cur = by[p.ed] || (by[p.ed] = { ed: p.ed, n: 0, nums: {} });
            cur.n += p.n; p.nums.forEach(function (x) { cur.nums[x] = true; });
          });
        });
        return { typed: w.typed, terms: hit, by: by };
      });
      var missing = per.filter(function (p) { return !p.terms.length; }).map(function (p) { return p.typed; });
      if (missing.length) return { per: per, rows: [], missing: missing };
      var eds = Object.keys(per[0].by).filter(function (e) { return per.every(function (p) { return p.by[e]; }); });
      var rows = [];
      eds.forEach(function (e) {
        // with more than one word, they must stand in one and the same headline
        var nums = Object.keys(per[0].by[e].nums);
        if (kind === 'h' && per.length > 1)
          nums = nums.filter(function (x) { return per.every(function (p) { return p.by[e].nums[x]; }); });
        if (!nums.length) return;
        var n = 0; per.forEach(function (p) { n += p.by[e].n; });
        rows.push({ ed: +e, n: n, nums: nums.map(Number).sort(function (a, b) { return a - b; }) });
      });
      rows.sort(function (a, b) { return b.ed - a.ed; });
      return { per: per, rows: rows };
    });
  }

  function sectionAt(sections, page) {
    for (var i = 0; i < (sections || []).length; i++)
      if (page >= sections[i][0] && page <= sections[i][1]) return sections[i][2];
    return '';
  }
  function sectionName(e, page) { return SECTION[sectionAt(e[6], page)] || 'The paper'; }

  // ---- what a result looks like -------------------------------------------------------------
  function yearOf(ed) { return meta.editions[ed][0].slice(0, 4); }

  /** The headlines of a year, fetched once and kept. */
  function yearHeads(y) {
    if (years[y]) return Promise.resolve(years[y]);
    return get('y:' + y).then(function (j) { years[y] = j || {}; return years[y]; });
  }

  function render(res, out, q) {
    out.innerHTML = '';
    if (res.error) { out.appendChild(el('p', { 'class': 'se-none', text: res.error })); return; }
    if (res.missing && res.missing.length) {
      out.appendChild(el('p', { 'class': 'se-none' }, ['No headline carries ', el('b', {}, [el('bdi', { text: res.missing.join(', ') })]), '.']));
      if (res.deeper) out.appendChild(res.deeper);
      return;
    }
    if (!res.rows.length) {
      out.appendChild(el('p', { 'class': 'se-none', text: 'Those words never stand in one and the same headline.' }));
      if (res.deeper) out.appendChild(res.deeper);
      return;
    }
    var heads = res.rows.reduce(function (a, r) { return a + r.nums.length; }, 0);
    var head = el('p', { 'class': 'se-count' }, [
      el('b', { text: String(heads) }), ' article' + (heads === 1 ? '' : 's') + ' in ',
      el('b', { text: String(res.rows.length) }), ' edition' + (res.rows.length === 1 ? '' : 's')]);
    if (res.per.length === 1 && res.per[0].terms.length > 1)
      head.appendChild(el('span', { 'class': 'se-forms' }, [' — counting ', el('bdi', { text: res.per[0].terms.slice(0, 8).join(', ') })]));
    out.appendChild(head);

    var list = el('ul', { 'class': 'se-list' });
    out.appendChild(list);
    var shown = 0;
    var more = el('button', { type: 'button', 'class': 'btn ghost se-more' });

    function draw() {
      var slice = res.rows.slice(shown, shown + PER_PAGE);
      if (!slice.length) { more.hidden = true; return; }
      var need = {}; slice.forEach(function (r) { need[yearOf(r.ed)] = true; });
      Promise.all(Object.keys(need).map(yearHeads)).then(function () {
        slice.forEach(function (r) { list.appendChild(row(r)); });
        shown += slice.length;
        more.hidden = shown >= res.rows.length;
        more.textContent = 'Show more (' + (res.rows.length - shown) + ' more editions)';
      });
    }

    function row(r) {
      var e = meta.editions[r.ed], date = e[0];
      var hs = (years[yearOf(r.ed)] || {})[date] || [];
      var li = el('li', {}, [
        el('a', { 'class': 'se-date', href: 'archive.html#e-' + date, text: niceDate(date) }),
        el('span', { 'class': 'se-ed' }, [el('bdi', { text: [e[3], e[4]].filter(Boolean).join(' · ') })]),
      ]);
      var ul = el('ul', { 'class': 'se-heads' });
      r.nums.forEach(function (id) {
        var h = hs[id]; if (!h) return;
        ul.appendChild(el('li', {}, [
          el('bdi', { 'class': 'se-head', text: h[1] }),
          el('span', { 'class': 'se-where', text: sectionName(e, h[0]) + ' · p. ' + h[0] }),
        ]));
      });
      li.appendChild(ul);
      li.appendChild(el('a', { 'class': 'se-buy', href: 'archive.html#e-' + date, text: 'See this edition' }));
      return li;
    }

    more.addEventListener('click', draw);
    out.appendChild(more);
    draw();
  }

  /** When no headline carries the word, the whole of the papers is still searched. */
  function deeperOffer(q, ws) {
    var p = el('p', { 'class': 'se-deeper' });
    var a = el('button', { type: 'button', 'class': 'se-deeper-go', text: 'Look inside the articles as well' });
    p.appendChild(a);
    a.addEventListener('click', function () {
      a.textContent = 'Looking…';
      look(ws, 'w').then(function (res) {
        p.innerHTML = '';
        if (!res.rows.length) { p.appendChild(document.createTextNode('Nothing anywhere in the papers either.')); return; }
        var n = res.rows.length;
        p.appendChild(el('b', { text: String(n) }));
        p.appendChild(document.createTextNode(' edition' + (n === 1 ? '' : 's') + ' carry it inside an article, where the headline does not say so:'));
        var ul = el('ul', { 'class': 'se-plain' });
        res.rows.slice(0, 60).forEach(function (r) {
          var e = meta.editions[r.ed];
          ul.appendChild(el('li', {}, [
            el('a', { href: 'archive.html#e-' + e[0], text: niceDate(e[0]) }),
            el('span', { 'class': 'se-where', text: r.nums.map(function (pg) { return sectionName(e, pg) + ' p. ' + pg; }).slice(0, 3).join(' · ') }),
          ]));
        });
        p.appendChild(ul);
      });
    });
    return p;
  }

  // ---- the page ------------------------------------------------------------------------------
  function start() {
    var form = document.getElementById('se-form'); if (!form) return;
    var input = document.getElementById('se-q'), out = document.getElementById('se-out');
    var status = document.getElementById('se-status');
    var stamp = form.getAttribute('data-v') || '';
    fetch(FN + 'meta' + (stamp ? '&b=' + encodeURIComponent(stamp) : '')).then(function (r) { return r.json(); }).then(function (j) {
      if (!j || !j.editions) throw new Error('no index');
      meta = j;
      status.textContent = ''; status.hidden = true;
      form.hidden = false;
      var q = new URLSearchParams(location.search).get('q');
      if (q) { input.value = q; run(q); }
    }).catch(function () {
      status.hidden = false;
      status.textContent = 'The archive search is still being built. Please try again later.';
    });

    function run(q) {
      var ws = words(q);
      if (!ws.length) { render({ error: 'Type a word of at least two Hebrew letters.' }, out); return; }
      out.innerHTML = '<p class="se-none">Looking…</p>';
      var kind = meta.headlines ? 'h' : 'w';
      look(ws, kind).then(function (res) {
        if (kind === 'h' && (!res.rows.length || (res.missing || []).length)) res.deeper = deeperOffer(q, ws);
        render(res, out, q);
      }, function () { out.innerHTML = '<p class="se-none">The search could not be run. Please try again.</p>'; });
    }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = input.value.trim(); if (!q) return;
      history.replaceState(null, '', 'search.html?q=' + encodeURIComponent(q));
      run(q);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
