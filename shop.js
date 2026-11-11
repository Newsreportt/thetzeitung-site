// The PDF shop: a "PDF · $5" button on every edition of the archive that exists as a PDF, a
// "whole year" button on every such year, a checkout that takes the card through Sola's iFields
// (the card number never touches this site), and the "your downloads" list on pdfs.html.
// Nothing shows until /.netlify/functions/shop-config says the shop is switched on.
(function () {
  'use strict';
  var FN = '/.netlify/functions/';
  var cfg = null, catalog = null, pdfs = null, ifieldsReady = null;

  function money(n) { return '$' + (Math.round(n * 100) / 100).toFixed(2).replace(/\.00$/, ''); }
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  function niceDate(iso) { var p = iso.split('-'); return MONTHS[+p[1] - 1] + ' ' + (+p[2]) + ', ' + p[0]; }
  function bdi(text) { return el('bdi', { text: text }); }
  function tierPrice(hy, tiers) {
    var age = (catalog.current_hy || 0) - Number(hy);
    tiers = tiers || catalog.issue_tiers || [{ max_age: 999, price: catalog.issue }];
    for (var i = 0; i < tiers.length; i++) if (age <= tiers[i].max_age) return tiers[i].price;
    return tiers[tiers.length - 1].price;
  }
  function issuePrice(date) { var ed = catalog.editions[date] || {}; return tierPrice(ed.hy); }
  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'html') e.innerHTML = attrs[k]; else if (k === 'text') e.textContent = attrs[k]; else e.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return e;
  }
  function getJSON(url) { return fetch(url, { cache: 'no-store' }).then(function (r) { return r.json(); }); }

  // ---- buttons in the archive -------------------------------------------------------------
  function decorateArchive() {
    var years = {};
    Object.keys(pdfs).forEach(function (date) {
      var ed = document.getElementById('e-' + date); if (!ed) return;
      var head = ed.querySelector('.ed-head'); if (!head) return;
      var b = el('button', { type: 'button', 'class': 'pdf-btn', 'data-item': date, title: 'Buy this edition as a PDF' },
                 [el('span', { text: 'PDF' }), ' ', el('b', { text: money(issuePrice(date)) })]);
      head.appendChild(b);
      var y = ed.closest('.year'); if (y) (years[y.id] = years[y.id] || []).push(date);
    });
    if (catalog.year_tiers) Object.keys(years).forEach(function (yid) {
      var meta = catalog.editions[years[yid][0]]; if (!meta) return;
      if (years[yid].length < (catalog.year_min_issues || 1)) return;
      var y = document.getElementById(yid), head = y && y.querySelector('.year-head'); if (!head) return;
      var b = el('button', { type: 'button', 'class': 'pdf-btn year', 'data-item': 'year:' + meta.hy, title: 'Buy every edition of this year as PDFs' },
                 [el('span', { text: 'All ' + years[yid].length + ' PDFs of this year' }), ' ', el('b', { text: money(tierPrice(meta.hy, catalog.year_tiers)) })]);
      head.appendChild(b);
    });
    var note = document.querySelector('.pdf-note'); if (note) note.hidden = false;
    document.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('.pdf-btn'); if (!b) return;
      e.preventDefault(); openCheckout(b.getAttribute('data-item'));
    });
  }

  function describe(item) {
    if (/^year:/.test(item)) {
      var hy = item.slice(5), yr = catalog.years[hy], n = Object.keys(pdfs).filter(function (d) { return catalog.editions[d] && String(catalog.editions[d].hy) === hy; }).length;
      return { title: 'Every edition of ' + (yr ? yr.label : hy) + ' as PDFs', sub: n + ' editions, each a full PDF of the paper', amount: tierPrice(hy, catalog.year_tiers) };
    }
    var ed = catalog.editions[item] || {};
    return { title: 'The edition of ' + niceDate(item) + ' as a PDF', sub: [ed.parsha, ed.hdate, ed.no ? 'No. ' + ed.no : ''].filter(Boolean).join(' · '), amount: issuePrice(item) };
  }

  // ---- iFields (Sola): the card number and CVV live in Sola's iframes --------------------
  function loadIfields() {
    if (ifieldsReady) return ifieldsReady;
    ifieldsReady = new Promise(function (ok, bad) {
      var s = document.createElement('script');
      s.src = 'https://cdn.cardknox.com/ifields/' + cfg.ifieldsVersion + '/ifields.min.js';
      s.onload = function () { try { window.setAccount(cfg.ifieldsKey, 'thetzeitung.com', '1.0'); ok(); } catch (e) { bad(e); } };
      s.onerror = function () { bad(new Error('iFields did not load')); };
      document.head.appendChild(s);
    });
    return ifieldsReady;
  }

  // ---- the checkout dialog -----------------------------------------------------------------
  var dlg = null;
  function openCheckout(item) {
    var d = describe(item);
    if (!dlg) {
      dlg = el('div', { 'class': 'checkout', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': 'co-title' });
      document.body.appendChild(dlg);
      dlg.addEventListener('click', function (e) { if (e.target === dlg) closeCheckout(); });
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && dlg.classList.contains('on')) closeCheckout(); });
    }
    var src = 'https://cdn.cardknox.com/ifields/' + cfg.ifieldsVersion + '/ifield.htm';
    dlg.innerHTML =
      '<form class="co-box" novalidate>' +
      '<button type="button" class="co-close" aria-label="Close">&times;</button>' +
      '<h3 id="co-title">' + d.title + '</h3><p class="co-sub"><bdi>' + d.sub + '</bdi></p>' +
      '<div class="co-price"><span>Total</span><b>' + money(d.amount) + '</b></div>' +
      '<label>Name on the card<input name="name" autocomplete="cc-name" required></label>' +
      '<label>Email for the receipt and the download link<input name="email" type="email" autocomplete="email" required></label>' +
      '<label>Card number<span class="co-frame"><iframe data-ifields-id="card-number" data-ifields-placeholder="Card number" src="' + src + '" title="Card number"></iframe></span></label>' +
      '<div class="co-row"><label>Expiry (MM/YY)<input name="exp" inputmode="numeric" autocomplete="cc-exp" placeholder="MM/YY" maxlength="5" required></label>' +
      '<label>CVV<span class="co-frame"><iframe data-ifields-id="cvv" data-ifields-placeholder="CVV" src="' + src + '" title="CVV"></iframe></span></label>' +
      '<label>Billing ZIP<input name="zip" inputmode="numeric" autocomplete="postal-code" maxlength="10"></label></div>' +
      '<input data-ifields-id="card-number-token" name="xCardNum" type="hidden"><input data-ifields-id="cvv-token" name="xCVV" type="hidden">' +
      '<p class="co-err" data-ifields-id="card-data-error" aria-live="polite"></p>' +
      '<button type="submit" class="btn gold co-pay">Pay ' + money(d.amount) + '</button>' +
      '<p class="co-fine">Secure card payment by Sola. The PDF is for your own use; it may not be reprinted or posted. Questions: call the office, 718-851-6607.</p>' +
      '</form>';
    dlg.classList.add('on'); document.body.classList.add('co-open');
    var form = dlg.querySelector('form'), err = dlg.querySelector('.co-err'), pay = dlg.querySelector('.co-pay');
    dlg.querySelector('.co-close').addEventListener('click', closeCheckout);
    form.exp.addEventListener('input', function () {
      var v = form.exp.value.replace(/\D/g, '').slice(0, 4);
      form.exp.value = v.length > 2 ? v.slice(0, 2) + '/' + v.slice(2) : v;
    });
    loadIfields().then(function () {
      var style = { border: '1px solid #c9bfa8', 'border-radius': '4px', padding: '10px 12px', width: '100%', 'box-sizing': 'border-box', 'font-size': '16px', 'font-family': 'Jost, Arial, sans-serif', background: '#fff' };
      try { window.setIfieldStyle('card-number', style); window.setIfieldStyle('cvv', style); window.enableAutoFormatting(' '); } catch (e) {}
      setTimeout(function () { form.name.focus(); }, 50);
    }).catch(function () { err.textContent = 'The card form could not be loaded. Please try again in a moment.'; });

    form.addEventListener('submit', function (e) {
      e.preventDefault(); err.textContent = '';
      var exp = form.exp.value.replace(/\D/g, '');
      if (!form.name.value.trim()) { err.textContent = 'Please give the name on the card.'; return; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.value.trim())) { err.textContent = 'Please give an email address.'; return; }
      if (!/^(0[1-9]|1[0-2])\d{2}$/.test(exp)) { err.textContent = 'The expiry date should be MM/YY.'; return; }
      pay.disabled = true; pay.textContent = 'Checking the card…';
      window.getTokens(function () {
        pay.textContent = 'Charging…';
        var body = { item: item, cardToken: form.xCardNum.value, cvvToken: form.xCVV.value, exp: exp,
                     name: form.name.value.trim(), email: form.email.value.trim(), zip: form.zip.value.trim() };
        fetch(FN + 'buy', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
          .then(function (r) { return r.json(); })
          .then(function (res) {
            if (!res.ok) { err.textContent = res.error || 'The payment did not go through.'; pay.disabled = false; pay.textContent = 'Pay ' + money(d.amount); return; }
            showReceipt(res);
          })
          .catch(function () { err.textContent = 'No answer from the server. If your card was charged, call the office with the time of the payment.'; pay.disabled = false; pay.textContent = 'Pay ' + money(d.amount); });
      }, function () {
        if (!err.textContent) err.textContent = 'Please check the card number and CVV.';
        pay.disabled = false; pay.textContent = 'Pay ' + money(d.amount);
      }, 30000);
    });
  }
  function closeCheckout() { if (dlg) { dlg.classList.remove('on'); dlg.innerHTML = ''; } document.body.classList.remove('co-open'); }

  function linkList(links) {
    var ul = el('ul', { 'class': 'dl-list' });
    links.forEach(function (l) {
      var size = l.bytes ? ' (' + (l.bytes / 1048576).toFixed(0) + ' MB)' : '';
      ul.appendChild(el('li', {}, [el('a', { href: l.url, 'class': 'btn ghost-dark', download: '' }, ['Download']), ' ', el('span', { 'class': 'dl-label' }, [bdi(l.label), size])]));
    });
    return ul;
  }

  function showReceipt(res) {
    var box = dlg.querySelector('.co-box'); box.innerHTML = '';
    box.appendChild(el('button', { type: 'button', 'class': 'co-close', 'aria-label': 'Close', html: '&times;' })).addEventListener('click', closeCheckout);
    box.appendChild(el('h3', { text: 'Thank you — your PDF' + (res.links.length > 1 ? 's are' : ' is') + ' ready' }));
    box.appendChild(el('p', { 'class': 'co-sub' }, [bdi(res.label), ' · ' + money(+res.amount) + ' charged to the card ending ' + res.card.slice(-4) + ' · ref. ' + res.refnum]));
    box.appendChild(linkList(res.links));
    var keep = el('p', { 'class': 'co-fine' }, ['Each link works for a day. To download again within ' + res.days + ' days, keep the address of your downloads page: ',
      el('a', { href: res.downloads, text: res.downloads.replace(/^https?:\/\//, '') }), ' ']);
    var copy = el('button', { type: 'button', 'class': 'co-mini', text: 'Copy the address' });
    copy.addEventListener('click', function () {
      (navigator.clipboard ? navigator.clipboard.writeText(res.downloads) : Promise.reject()).then(function () { copy.textContent = 'Copied'; }, function () { prompt('Copy this address:', res.downloads); });
    });
    var mail = el('a', { 'class': 'co-mini', text: 'Email it to myself', href: 'mailto:' + encodeURIComponent(res.email || '') + '?subject=' + encodeURIComponent('The Tzeitung — your PDF downloads') + '&body=' + encodeURIComponent('Your downloads (' + res.label + '): ' + res.downloads + '\n\nRef. ' + res.refnum) });
    keep.appendChild(copy); keep.appendChild(document.createTextNode(' ')); keep.appendChild(mail);
    box.appendChild(keep);
  }

  // ---- pdfs.html?t=... : the buyer's downloads ---------------------------------------------
  function showDownloads() {
    var out = document.getElementById('your-downloads'); if (!out) return;
    var t = new URLSearchParams(location.search).get('t'); if (!t) return;
    out.hidden = false; out.innerHTML = '<p>Fetching your downloads…</p>';
    getJSON(FN + 'downloads?t=' + encodeURIComponent(t)).then(function (res) {
      out.innerHTML = '';
      if (!res.ok) { out.appendChild(el('p', { 'class': 'co-err', text: res.error })); return; }
      out.appendChild(el('h2', { text: 'Your downloads' }));
      out.appendChild(el('p', {}, [bdi(res.label), ' · ref. ' + res.refnum + ' · this page works until ' + new Date(res.until * 1000).toLocaleDateString()]));
      out.appendChild(linkList(res.links));
    }).catch(function () { out.innerHTML = '<p class="co-err">The downloads could not be fetched. Please try again.</p>'; });
  }

  // ---- start ---------------------------------------------------------------------------------
  getJSON(FN + 'shop-config').then(function (c) {
    cfg = c;
    if (!c.enabled) return;
    return Promise.all([getJSON('shop-catalog.json'), getJSON('pdfs.json')]).then(function (r) {
      catalog = r[0]; pdfs = r[1];
      if (document.querySelector('.archive')) decorateArchive();
      showDownloads();
    });
  }).catch(function () {});
})();
