// ===== די צײַטונג — shared scripts =====
(function () {
  var d = new Date();
  var days = ['זונטאג','מאנטאג','דינסטאג','מיטוואך','דאנערשטאג','פרייטאג','שבת'];
  var months = ['יאנואר','פעברואר','מערץ','אפריל','מאי','יוני','יולי','אויגוסט','סעפטעמבער','אקטאבער','נאוועמבער','דעצעמבער'];

  var civil = days[d.getDay()] + ', ' + d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
  var hebrew = '';
  try {
    hebrew = new Intl.DateTimeFormat('he-u-ca-hebrew', { day: 'numeric', month: 'long', year: 'numeric' }).format(d);
  } catch (e) {}

  var c = document.getElementById('civil-date'); if (c) c.textContent = civil;
  var h = document.getElementById('hebrew-date'); if (h) h.textContent = hebrew;
  var y = document.getElementById('year'); if (y) y.textContent = d.getFullYear();

  // mobile menu
  var btn = document.querySelector('.menu-btn');
  var ul = document.querySelector('.nav ul');
  if (btn && ul) btn.addEventListener('click', function () { ul.classList.toggle('open'); });

  // mark active nav link
  var here = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav a').forEach(function (a) {
    var href = a.getAttribute('href');
    if (href === here || (here === 'index.html' && href === '/')) a.classList.add('active');
  });
})();
