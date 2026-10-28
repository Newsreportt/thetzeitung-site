# Generates every page of the site. Run: python3 _build/build.py
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAV = [("index.html","Home"),("archive.html","Archives"),("about.html","About"),("advertise.html","Advertise"),
       ("subscribe.html","Subscriptions"),("contact.html","Contact")]

def shell(title, desc, body, extra_js=""):
    nav = "".join(f'<li><a href="{h}">{t}</a></li>' for h,t in NAV)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Raleway:wght@400;700;800&family=Open+Sans:wght@300;400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
  <link rel="icon" href="covers/favicon.png">
</head>
<body>

<header class="site-header">
  <span class="bsd">בס"ד</span>
  <a class="logo" href="index.html">
    <img src="covers/logo-yiddish.png" alt="Di Tzeitung — די צייטונג" width="1140" height="270">
    <img class="nr" src="covers/logo-newsreport.png" alt="News Report — The Yiddish Newspaper of Record" width="600" height="165">
  </a>
  <div class="tag">The Independent Yiddish Newspaper · 40 Years</div>
</header>
<nav class="nav">
  <button class="menu-btn" aria-label="Menu">☰ Menu</button>
  <ul>{nav}</ul>
</nav>

<div class="page">
{body}
</div>

<footer class="site-footer">
  <a class="top" href="#">Back To Top</a>
  <p>Di Tzeitung · News Report &nbsp;•&nbsp; 445 Park Avenue #202, Brooklyn, N.Y. 11205 &nbsp;•&nbsp; <a href="tel:7188516607">718-851-6607</a> &nbsp;•&nbsp; <a href="mailto:mk@thetzeitung.com">mk@thetzeitung.com</a></p>
  <div class="links"><a href="about.html">About</a><a href="advertise.html">Advertise</a><a href="subscribe.html">Subscribe</a><a href="contact.html">Contact</a></div>
  <p style="margin-top:14px;font-size:12px">© <span id="year"></span> Di Tzeitung. All rights reserved.</p>
</footer>

<script src="site.js"></script>{extra_js}
</body>
</html>
'''

def write(fname, html):
    open(os.path.join(ROOT, fname), "w", encoding="utf-8").write(html); print("wrote", fname)

SECTIONS = [
  ("sec-a.jpg", "Main Section — Di Tzeitung", "General news & politics, American and world news, the economy, and news from the heimishe community. The Yiddish newspaper of record, in stores every Wednesday morning."),
  ("sec-b.jpg", "Yiddishe Tzeit — אידישע צייט", "The weekly supplement of history, memoirs and heritage: the Jewish towns of yesteryear, great personalities, and stories passed down through generations."),
  ("sec-c.jpg", "Chassidishe Tzeit — חסידישע צייט", "Chassidishe news from around the world, with the popular picture section of Rebbes, chassidishe courts, simchos and events."),
]

# ---------------- HOME ----------------
sections_html = "".join(f'''
  <div class="section-item">
    <h3>{t}</h3>
    <a href="subscribe.html"><img src="covers/{img}" alt="{t}" loading="lazy"></a>
    <p class="desc">{d}</p>
  </div>''' for img,t,d in SECTIONS)

home = f'''
<section class="welcome"><div class="wrap grid">
  <div class="fan">
    <img src="covers/thumb-c.jpg" alt=""><img src="covers/thumb-a.jpg" alt=""><img src="covers/thumb-b.jpg" alt="">
  </div>
  <div>
    <h2>Welcome!</h2>
    <p>Di Tzeitung — <i>The Independent Yiddish Newspaper</i> — has been published every week in Brooklyn for 40 years. Known as <b>News Report, The Yiddish Newspaper of Record</b>, it is read by thousands of readers around the world — in Boro Park, Williamsburg, Kiryas Joel, Monsey and Lakewood, and across the United States, Canada, England, Belgium and Eretz Yisroel. A fresh edition is in stores every Wednesday morning.</p>
    <div class="btns"><a href="subscribe.html" class="btn green">Subscribe</a><a href="advertise.html" class="btn outline">Advertise</a></div>
  </div>
</div></section>

<section class="carousel"><div class="wrap">
  <div class="stage">
    <img src="covers/sec-a.jpg" class="on" alt="Main Section">
    <img src="covers/sec-b.jpg" alt="Yiddishe Tzeit">
    <img src="covers/sec-c.jpg" alt="Chassidishe Tzeit">
    <button class="arrow prev" aria-label="Previous">‹</button>
    <button class="arrow next" aria-label="Next">›</button>
  </div>
  <div class="thumbs">
    <img src="covers/thumb-a.jpg" class="on" data-i="0" alt="Main Section">
    <img src="covers/thumb-b.jpg" data-i="1" alt="Yiddishe Tzeit">
    <img src="covers/thumb-c.jpg" data-i="2" alt="Chassidishe Tzeit">
  </div>
</div></section>

<hr class="rule">

<section class="sections"><div class="wrap">
  {sections_html}
</div></section>
'''
write("index.html", shell("Di Tzeitung — News Report, The Yiddish Newspaper of Record",
  "Di Tzeitung (News Report) is the independent Yiddish weekly newspaper published in Brooklyn for 40 years, read by thousands around the world.", home))

# ---------------- ABOUT ----------------
about = '''
<section class="page-head"><div class="wrap"><h1>About</h1><p>The Independent Yiddish Newspaper — 40 years, thousands of readers around the world.</p></div></section>
<section class="page-body"><div class="wrap">
  <div class="stats">
    <div><b>40</b><span>Years in print</span></div>
    <div><b>1000s</b><span>Readers worldwide</span></div>
    <div><b>Wed.</b><span>In stores every week</span></div>
    <div><b>3</b><span>Sections weekly</span></div>
  </div>
  <div class="prose">
    <p>Di Tzeitung — <i>Di Zelbstshtendige Yiddishe Tzeitung</i>, the Independent Yiddish Newspaper — was founded in Brooklyn 40 years ago by Rabbi Avrohom Friedman, who continues to lead it today as founder and editor-in-chief. Published every week in the Yiddish language and in stores every Wednesday morning, and known in English as <b>News Report, The Yiddish Newspaper of Record</b>, it has grown into one of the prominent and historic institutions of the Yiddish printed word in America.</p>
    <h2>Who We Serve</h2>
    <p>Thousands of readers around the world turn to Di Tzeitung every week: the Yiddish-speaking communities of Brooklyn — Boro Park, Williamsburg and Flatbush — as well as Kiryas Joel, Monsey, Lakewood and other heimishe communities throughout the United States, along with readers in Canada, London, Belgium and Eretz Yisroel.</p>
    <h2>Our Approach</h2>
    <p>Our stated mission is to bring the news with an impartial eye. Di Tzeitung never involves itself in internal community disputes. We believe our readers deserve clear, accurate reporting — and nothing more. In general American politics the paper keeps a measured tone, with the goal of maintaining good relations with local, city and federal agencies for the benefit of the community.</p>
    <h2>What's Inside Every Week</h2>
    <p><b>Main Section</b> — General politics, American and world news, business and the economy, and news from the heimishe community.</p>
    <p><b>Yiddishe Tzeit (אידישע צייט)</b> — The beloved weekly supplement of history, memoirs and heritage: the Jewish towns of yesteryear, great personalities and the stories of generations past.</p>
    <p><b>Chassidishe Tzeit (חסידישע צייט)</b> — Chassidishe news from around the world, and the popular picture section featuring Rebbes, chassidishe courts, simchos and events.</p>
    <h2>Forty Years</h2>
    <p>Like every printed newspaper, Di Tzeitung has weathered rising paper and printing costs and the transformation of the media landscape. Through it all, it remains one of the enduring voices of the Yiddish-speaking community — and we are proud that you are part of it.</p>
  </div>
</div></section>
'''
write("about.html", shell("About — Di Tzeitung", "The history and mission of Di Tzeitung, the independent Yiddish newspaper, 40 years in print.", about))

# ---------------- SUBSCRIPTIONS ----------------
subscribe = '''
<section class="page-head"><div class="wrap"><h1>Subscriptions</h1><p>Receive Di Tzeitung every week, delivered to your home anywhere in the United States.</p></div></section>
<section class="page-body"><div class="wrap">
  <div class="promo" style="margin-bottom:50px"><img src="ads/promo-2.jpg" alt="יעדע וואך פונדאסניי — א פרישער געשמאק צום טיר! Subscribe to Di Tzeitung"></div>
  <div class="products">
    <div class="product">
      <div class="img"><img src="covers/sec-a.jpg" alt=""></div>
      <h3>Yearly Subscription — Mail</h3>
      <div class="price"><b>$400.00</b> every 12 months</div>
      <a href="#order" class="btn">Subscribe</a>
    </div>
    <div class="product">
      <div class="img"><img src="covers/sec-a.jpg" alt=""></div>
      <h3>Half Year Subscription — Mail</h3>
      <div class="price"><b>$200.00</b> every 6 months</div>
      <a href="#order" class="btn">Subscribe</a>
    </div>
  </div>
  <p class="center" style="margin:30px 0 60px;font-size:13px;color:var(--muted)">All subscriptions include the Main Section, Yiddishe Tzeit and Chassidishe Tzeit. For group rates for shuls, yeshivos and businesses, call <a href="tel:7188516607"><b>718-851-6607</b></a>.</p>

  <div class="two-col" id="order">
    <div>
      <h2 style="color:var(--accent);text-transform:uppercase;letter-spacing:2px;font-size:22px;margin-bottom:6px">Order Your Subscription</h2>
      <p style="margin-bottom:22px;color:var(--muted)">Complete the form and we will call you within 1–2 business days to finalize your order.</p>
      <form class="form" name="subscribe" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
        <input type="hidden" name="form-name" value="subscribe">
        <p style="display:none"><label>Don't fill this out: <input name="bot-field"></label></p>
        <div class="row"><div><label>Full name</label><input type="text" name="name" required></div><div><label>Phone</label><input type="tel" name="phone" required></div></div>
        <div><label>Email</label><input type="email" name="email"></div>
        <div><label>Delivery address</label><input type="text" name="address" placeholder="Street, City, State, ZIP" required></div>
        <div class="row">
          <div><label>Plan</label><select name="plan"><option>Yearly — $400</option><option>Half Year — $200</option></select></div>
          <div><label>How did you hear about us?</label><select name="source"><option>A friend</option><option>Saw the paper</option><option>Online</option><option>Other</option></select></div>
        </div>
        <div><label>Notes</label><textarea name="notes" style="min-height:90px"></textarea></div>
        <button class="btn green" type="submit">Submit Order</button>
      </form>
    </div>
    <aside class="aside">
      <h3>Prefer the phone?</h3>
      <p>Call us and we'll set you up in two minutes.</p>
      <p style="font-family:var(--sans);font-size:26px;font-weight:800"><a href="tel:7188516607">718-851-6607</a></p>
      <p>Billing questions: <a href="mailto:billing@thetzeitung.com"><b>billing@thetzeitung.com</b></a></p>
      <div class="line"></div>
      <h3>Where we deliver</h3>
      <p>Boro Park, Williamsburg, Flatbush, Kiryas Joel, Monsey, Lakewood — and by mail anywhere in the United States.</p>
      <div class="line"></div>
      <h3>Gift subscriptions</h3>
      <p>Send a year of Di Tzeitung to a chosson-kallah, parents or a friend. Note "gift" in the form and we'll include a card.</p>
    </aside>
  </div>
</div></section>
'''
write("subscribe.html", shell("Subscriptions — Di Tzeitung", "Subscribe to Di Tzeitung, delivered every week.", subscribe))

# ---------------- ADVERTISE ----------------
advertise = '''
<section class="page-head"><div class="wrap"><h1>Advertise</h1><p>The most direct way to reach thousands of heimishe households around the world every week — for 40 years.</p></div></section>
<section class="page-body"><div class="wrap">
  <div class="stats">
    <div><b>40</b><span>Years of trust</span></div>
    <div><b>1000s</b><span>Readers worldwide</span></div>
    <div><b>Wed.</b><span>In stores every week</span></div>
    <div><b>3</b><span>Sections weekly</span></div>
    <div><b>100%</b><span>Yiddish-speaking readers</span></div>
  </div>
  <div class="rates">
    <table>
      <thead><tr><th>Ad size</th><th>Dimensions (w × h)</th><th>Rate</th></tr></thead>
      <tbody>
        <tr><td>Full Page</td><td>9.7" × 11"</td><td>$1,200</td></tr>
        <tr><td>3/4 Page</td><td>7" × 8"</td><td>$750</td></tr>
        <tr><td>Half Page (landscape)</td><td>9.7" × 5.4"</td><td>$600</td></tr>
        <tr><td>Half Page (vertical)</td><td>4.7" × 11"</td><td>$600</td></tr>
        <tr><td>2/3 Page</td><td>5.2" × 8"</td><td>$500</td></tr>
        <tr><td>2/3 Page (short)</td><td>5.2" × 7"</td><td>$425</td></tr>
        <tr><td>Quarter Page</td><td>4.7" × 5.4"</td><td>$300</td></tr>
        <tr><td>Eighth Page</td><td>4.7" × 2.2"</td><td>$150 <small>(+$40 per additional inch of height)</small></td></tr>
        <tr><td>Business Card</td><td>4.7" × 1.4"</td><td>$75</td></tr>
        <tr><td>Classified</td><td>2.3" × 1"</td><td>$17</td></tr>
        <tr class="hl"><td>Front Strip</td><td>10" × 1"</td><td>$350</td></tr>
        <tr class="hl"><td>Front Strip (double)</td><td>10" × 2"</td><td>$550</td></tr>
        <tr class="hl"><td>Front Cover Box</td><td>2" × 2"</td><td>$150</td></tr>
      </tbody>
    </table>
    <p class="note"><b>No extra charge for color.</b> Ad deadline: Tuesday, 12:00 PM. &nbsp;·&nbsp; <a href="Di-Tzeitung-Ad-Rates.pdf" target="_blank">Download rate card (PDF) ↗</a></p>
  </div>
  <div class="two-col">
    <div>
      <h2 style="color:var(--accent);text-transform:uppercase;letter-spacing:2px;font-size:22px;margin-bottom:6px">Request Rates &amp; Deadlines</h2>
      <p style="margin-bottom:22px;color:var(--muted)">Tell us what you'd like to advertise and we'll confirm placement and specifications. Ad deadline: <b>Tuesday, 12:00 PM</b>.</p>
      <form class="form" name="advertise" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
        <input type="hidden" name="form-name" value="advertise">
        <p style="display:none"><label>Don't fill this out: <input name="bot-field"></label></p>
        <div class="row"><div><label>Name / Business</label><input type="text" name="name" required></div><div><label>Phone</label><input type="tel" name="phone" required></div></div>
        <div><label>Email</label><input type="email" name="email" required></div>
        <div class="row">
          <div><label>Size</label><select name="size"><option>Full page</option><option>Half page</option><option>Quarter page</option><option>Classified</option><option>Not sure yet</option></select></div>
          <div><label>How many weeks?</label><select name="weeks"><option>1 week</option><option>4 weeks</option><option>12 weeks</option><option>Full year</option></select></div>
        </div>
        <div><label>What would you like to advertise?</label><textarea name="message" required></textarea></div>
        <button class="btn green" type="submit">Send Request</button>
      </form>
    </div>
    <aside class="aside">
      <h3>Advertising Department</h3>
      <p><b>Phone:</b> <a href="tel:7188516607">718-851-6607</a></p>
      <p><b>Email:</b> <a href="mailto:mk@thetzeitung.com">mk@thetzeitung.com</a></p>
      <p><b>Billing:</b> <a href="mailto:billing@thetzeitung.com">billing@thetzeitung.com</a></p>
      <div class="line"></div>
      <h3>Why Di Tzeitung?</h3>
      <p>A newspaper that sits on the table all week — at home, in shul and in the store — not an ad that disappears in a second.</p>
      <div class="line"></div>
      <h3>Design help</h3>
      <p>Don't have a finished ad? Our design team can create one for you.</p>
    </aside>
  </div>
</div></section>
'''
write("advertise.html", shell("Advertise — Di Tzeitung", "Advertise in Di Tzeitung and reach thousands of Yiddish-speaking readers every week.", advertise))

# ---------------- CONTACT ----------------
contact = '''
<section class="page-head"><div class="wrap"><h1>Contact</h1><p>Editorial, letters to the editor, subscriptions, advertising — or to submit articles and photos.</p></div></section>
<section class="page-body"><div class="wrap two-col">
  <div>
    <form class="form" name="contact" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
      <input type="hidden" name="form-name" value="contact">
      <p style="display:none"><label>Don't fill this out: <input name="bot-field"></label></p>
      <div class="row"><div><label>Name</label><input type="text" name="name" required></div><div><label>Phone</label><input type="tel" name="phone"></div></div>
      <div><label>Email</label><input type="email" name="email" required></div>
      <div><label>Subject</label><select name="topic"><option>General</option><option>Letter to the Editor (בריוו)</option><option>Editorial / news tip</option><option>Submit an article</option><option>Submit photos</option><option>Subscription</option><option>Advertising</option><option>Correction</option></select></div>
      <div><label>Message</label><textarea name="message" required></textarea></div>
      <button class="btn green" type="submit">Send</button>
    </form>
  </div>
  <aside class="aside">
    <h3>Editorial &amp; Office</h3>
    <p><b>Di Tzeitung</b><br>445 Park Avenue #202<br>Brooklyn, NY 11205</p>
    <div class="line"></div>
    <p><b>Phone:</b> <a href="tel:7188516607">718-851-6607</a></p>
    <div class="line"></div>
    <p><b>General inquiries:</b><br><a href="mailto:mk@thetzeitung.com">mk@thetzeitung.com</a></p>
    <p><b>Editor &amp; Letters to the Editor (בריוו):</b><br><a href="mailto:yt@thetzeitung.com">yt@thetzeitung.com</a></p>
    <p><b>Billing &amp; subscriptions:</b><br><a href="mailto:billing@thetzeitung.com">billing@thetzeitung.com</a></p>
    <div class="line"></div>
    <p style="font-size:13px;color:var(--muted)">Office hours: Sunday–Thursday, 9:00 AM – 6:00 PM. Editorial deadline: Tuesday 12:00 PM.</p>
  </aside>
</div></section>
'''
write("contact.html", shell("Contact — Di Tzeitung", "Contact Di Tzeitung.", contact))

# ---------------- ARCHIVES ----------------
figs = "".join(f'<figure><a href="subscribe.html"><img src="covers/{img}" alt="{t}" loading="lazy"></a><figcaption>{t}</figcaption></figure>' for img,t,_ in SECTIONS)
archive = f'''
<section class="page-head"><div class="wrap"><h1>Archives</h1><p>Covers from recent editions — a new edition every Wednesday. Subscribers may request back issues from our office.</p></div></section>
<section class="page-body"><div class="wrap">
  <h2 style="color:var(--accent);text-transform:uppercase;letter-spacing:3px;font-size:16px;text-align:center;margin-bottom:26px">Vol. 40 · No. 6 — Week of October 28, 2026</h2>
  <div class="archive-grid">{figs}</div>
  <div class="aside" style="margin:50px auto 0;max-width:720px;text-align:center">
    <h3>Need a specific issue?</h3>
    <p>For back issues, special editions or a copy of a specific article, call <a href="tel:7188516607"><b>718-851-6607</b></a> or write to <a href="mailto:mk@thetzeitung.com"><b>mk@thetzeitung.com</b></a>.</p>
  </div>
</div></section>
'''
write("archive.html", shell("Archives — Di Tzeitung", "Archive of past editions of Di Tzeitung.", archive))

# ---------------- THANKS ----------------
thanks = '''
<section class="page-head"><div class="wrap"><h1>Thank You!</h1><p>We received your message and will be in touch shortly.</p></div></section>
<section class="page-body"><div class="wrap center"><a href="index.html" class="btn">Back to Home</a> &nbsp; <a href="subscribe.html" class="btn outline">Subscribe</a></div></section>
'''
write("thanks.html", shell("Thank You — Di Tzeitung", "Thank you.", thanks))
