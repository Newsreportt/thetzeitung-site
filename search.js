// The archive search: a word, and every issue it stands in — which week, which section, which
// page, how many times. The index holds words and page numbers only; no article text is served,
// here or anywhere. From a result the reader goes to that edition, and can buy its PDF.
(function () {
  'use strict';
  var FN = '/.netlify/functions/search-index?s=';
  var meta = null, shards = {}, pending = {};
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var SECTION = { a: 'The main section', b: 'Yiddishe Tzeit', c: 'Chassidishe Tzeit', d: 'Yom Tov Tzeit', t: 'Torah Tzeit', k: 'Kehila Tzeit' };
  var SECTION_YI = { a: 'די צייטונג', b: 'אידישע צייט', c: 'חסידישע צייט', d: 'יום טוב צייט', t: 'תורה צייט', k: 'קהלה צייט' };

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
  function key(word) { return word.replace(/['’׳"״]/g, '').replace(/ך/g, 'כ').replace(/ם/g, 'מ').replace(/ן/g, 'נ').replace(/ף/g, 'פ').replace(/ץ/g, 'צ'); }
  function words(q) {
    return (q.match(/[א-ת]+(?:['’׳"״][א-ת]+)*/g) || [])
      .map(function (w) { return { typed: w, k: key(w) }; })
      .filter(function (w) { return w.k.length >= 2; });
  }

  function get(s) {
    if (shards[s]) return Promise.resolve(shards[s]);
    if (pending[s]) return pending[s];
    pending[s] = fetch(FN + encodeURIComponent(s)).then(function (r) { return r.json(); }).then(function (j) {
      shards[s] = j; delete pending[s]; return j;
    }, function () { delete pending[s]; return {}; });
    return pending[s];
  }

  /** The postings of one word, unpacked: [{ed, n, pages}] */
  function postings(shard, word) {
    var flat = shard[word]; if (!flat) return [];
    var out = [], i = 0, ed = 0;
    while (i < flat.length) {
      ed += flat[i++];
      var n = flat[i++], count = flat[i++], pages = [];
      for (var j = 0; j < count; j++) pages.push(flat[i++]);
      out.push({ ed: ed, n: n, pages: pages });
    }
    return out;
  }

  /** Every word in the shard that starts with, or contains, what was typed. */
  function matches(shard, word, loose) {
    if (shard[word]) return [word];
    var out = [];
    for (var k in shard) if (k.indexOf(word) === 0) out.push(k);
    if (!out.length && loose) for (var k2 in shard) if (k2.indexOf(word) > 0) out.push(k2);
    return out.sort(function (a, b) { return a.length - b.length; }).slice(0, 40);
  }

  function search(q) {
    var ws = words(q);
    if (!ws.length) return Promise.resolve({ error: 'Type a word of at least two Hebrew letters.' });
    return Promise.all(ws.map(function (w) { return get(w.k.slice(0, 2)); })).then(function (sh) {
      var per = ws.map(function (w, i) {
        var hit = matches(sh[i], w.k, ws.length === 1);
        var by = {};
        hit.forEach(function (term) {
          postings(sh[i], term).forEach(function (p) {
            var cur = by[p.ed] || (by[p.ed] = { ed: p.ed, n: 0, pages: {} });
            cur.n += p.n; p.pages.forEach(function (pg) { cur.pages[pg] = true; });
          });
        });
        return { word: w.k, typed: w.typed, terms: hit, by: by };
      });
      if (per.some(function (p) { return !p.terms.length; }))
        return { ws: ws, per: per, rows: [], missing: per.filter(function (p) { return !p.terms.length; }).map(function (p) { return p.typed; }) };
      // every word must stand in the issue
      var eds = Object.keys(per[0].by).filter(function (e) { return per.every(function (p) { return p.by[e]; }); });
      var rows = eds.map(function (e) {
        var pages = {}, n = 0;
        per.forEach(function (p) { n += p.by[e].n; Object.keys(p.by[e].pages).forEach(function (pg) { pages[pg] = true; }); });
        return { ed: +e, n: n, pages: Object.keys(pages).map(Number).sort(function (a, b) { return a - b; }) };
      });
      rows.sort(function (a, b) { return b.ed - a.ed; });
      return { ws: ws, per: per, rows: rows };
    });
  }

  // ---- what a result looks like -------------------------------------------------------------
  function sectionAt(sections, page) {
    for (var i = 0; i < (sections || []).length; i++)
      if (page >= sections[i][0] && page <= sections[i][1]) return sections[i][2];
    return '';
  }
  function pageList(e, pages) {
    var secs = {}, order = [];
    pages.forEach(function (p) {
      var s = sectionAt(e[6], p) || '';
      if (!secs[s]) { secs[s] = []; order.push(s); }
      secs[s].push(p);
    });
    return order.map(function (s) {
      return { section: s, name: SECTION[s] || 'The paper', yiddish: SECTION_YI[s] || '', pages: secs[s] };
    });
  }

  function render(res, out, q) {
    out.innerHTML = '';
    if (res.error) { out.appendChild(el('p', { 'class': 'se-none', text: res.error })); return; }
    if (res.missing && res.missing.length) {
      out.appendChild(el('p', { 'class': 'se-none' }, ['Nothing in the archive for ', el('b', {}, [el('bdi', { text: res.missing.join(', ') })]), '.']));
      return;
    }
    if (!res.rows.length) { out.appendChild(el('p', { 'class': 'se-none', text: 'Those words never stand in one and the same edition.' })); return; }
    var total = res.rows.reduce(function (a, r) { return a + r.n; }, 0);
    var head = el('p', { 'class': 'se-count' }, [
      el('b', { text: String(total) }), ' mention' + (total === 1 ? '' : 's') + ' in ',
      el('b', { text: String(res.rows.length) }), ' edition' + (res.rows.length === 1 ? '' : 's')]);
    if (res.per.length === 1 && res.per[0].terms.length > 1)
      head.appendChild(el('span', { 'class': 'se-forms' }, [' — as ', el('bdi', { text: res.per[0].terms.slice(0, 8).join(', ') })]));
    out.appendChild(head);

    var byYear = {}, years = [];
    res.rows.forEach(function (r) {
      var y = meta.editions[r.ed][0].slice(0, 4);
      if (!byYear[y]) { byYear[y] = []; years.push(y); }
      byYear[y].push(r);
    });
    years.forEach(function (y) {
      var sec = el('section', { 'class': 'se-year' }, [el('h3', { text: y + ' · ' + byYear[y].length + ' edition' + (byYear[y].length === 1 ? '' : 's') })]);
      var ul = el('ul', { 'class': 'se-list' });
      byYear[y].forEach(function (r) {
        var e = meta.editions[r.ed], date = e[0];
        var where = pageList(e, r.pages).map(function (g) {
          return el('span', { 'class': 'se-where' }, [el('b', { text: g.name }), ' p. ' + g.pages.join(', ')]);
        });
        var li = el('li', {}, [
          el('a', { 'class': 'se-date', href: 'archive.html#e-' + date, text: niceDate(date) }),
          el('span', { 'class': 'se-ed' }, [el('bdi', { text: [e[3], e[4]].filter(Boolean).join(' · ') })]),
          el('span', { 'class': 'se-n', text: r.n + '×' }),
        ]);
        var w = el('div', { 'class': 'se-wheres' }); where.forEach(function (x) { w.appendChild(x); });
        li.appendChild(w);
        li.appendChild(el('a', { 'class': 'se-buy', href: 'archive.html#e-' + date, text: 'See this edition' }));
        ul.appendChild(li);
      });
      sec.appendChild(ul); out.appendChild(sec);
    });
  }

  // ---- the page ------------------------------------------------------------------------------
  function start() {
    var form = document.getElementById('se-form'); if (!form) return;
    var input = document.getElementById('se-q'), out = document.getElementById('se-out');
    var status = document.getElementById('se-status');
    fetch(FN + 'meta').then(function (r) { return r.json(); }).then(function (j) {
      if (!j || !j.editions) throw new Error('no index');
      meta = j;
      status.textContent = j.editions.length + ' editions, ' + (j.terms ? j.terms.toLocaleString() + ' different words' : '') + ' — searching the pages themselves.';
      form.hidden = false;
      var q = new URLSearchParams(location.search).get('q');
      if (q) { input.value = q; run(q); }
    }).catch(function () {
      status.textContent = 'The archive search is still being built. Please try again later.';
    });

    function run(q) {
      out.innerHTML = '<p class="se-none">Looking…</p>';
      search(q).then(function (res) { render(res, out, q); },
                     function () { out.innerHTML = '<p class="se-none">The search could not be run. Please try again.</p>'; });
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
