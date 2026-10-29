# Generates every page of the site. Run: python3 _build/build.py
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAV = [("index.html", "Home"), ("archive.html", "Archives"), ("about.html", "About"),
       ("advertise.html", "Advertise"), ("index.html#email", "Email list"), ("contact.html", "Contact")]

import glob
WALL = ",".join("covers/wall/" + os.path.basename(f) for f in sorted(glob.glob(os.path.join(ROOT, "covers", "wall", "*.jpg"))))

# Editions come from _build/editions.json (filled by _build/import_covers.py).
import json, re
from datetime import date, timedelta
EDITIONS = json.load(open(os.path.join(ROOT, "_build", "editions.json"), encoding="utf-8"))
EDITION_KEYS = sorted(EDITIONS, reverse=True)          # newest first
LATEST = EDITIONS[EDITION_KEYS[0]]

def nice_date(iso):
    y, m, d = map(int, iso.split("-")); return date(y, m, d).strftime("%B %-d, %Y")
def week_of(iso):                                        # the Wednesday the paper reaches the stores
    y, m, d = map(int, iso.split("-")); return (date(y, m, d) - timedelta(days=2)).strftime("%B %-d, %Y")
def parsha_html(ed):
    p = (ed.get("parsha") or "").replace(", ", "-")
    return f'<span class="heb">{p}</span>' if p else ""

EDITION_VOL, EDITION_NO = LATEST["vol"], LATEST["no"]
EDITION_PARSHA = (LATEST.get("parsha") or "").replace(", ", "-")
EDITION_DATE = week_of(LATEST["date"])
LATEST_COVER = LATEST["covers"].get("a") or next(iter(LATEST["covers"].values()))

PHONE = '<a href="tel:7188516607">718-851-6607</a>'
ADDRESS = "445 Park Avenue, Suite 202<br>Brooklyn, NY 11205"

SECTIONS = [
  ("a", "The main section", "די צייטונג",
   "General news and politics, news from America and around the world, business and the economy, and what is happening in the heimishe community."),
  ("b", "Yiddishe Tzeit", "אידישע צייט",
   "The weekly supplement of history and heritage: the Jewish towns of yesteryear, great personalities, and memoirs passed down through the generations."),
  ("c", "Chassidishe Tzeit", "חסידישע צייט",
   "Chassidishe news from around the world, with the popular picture section of Rebbes, chassidishe courts, simchos and events."),
  ("d", "Yom Tov Tzeit", "יום טוב צייט",
   "The yom tov supplement: longer reading for the days of yom tov."),
  ("t", "Torah Tzeit", "תורה צייט",
   "The yom tov supplement of Torah and history: the gedolim and the seforim, the minhagim and the memories of yom tov."),
  ("k", "Kehila Tzeit", "קהלה צייט",
   "The yom tov supplement about the kehilos: mosdos, askonim and the people who build the community."),
]
REGULAR = [sec for sec in SECTIONS if sec[0] in ("a", "b", "c")]   # what every edition carries

SITE = "https://thetzeitung.com/"

# a short fingerprint of the stylesheet and script, so browsers fetch fresh copies after every change
import hashlib
def _fp(name):
    return hashlib.md5(open(os.path.join(ROOT, name), "rb").read()).hexdigest()[:8]
CSS_V, JS_V = _fp("style.css"), _fp("site.js")

ORG_JSONLD = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "NewsMediaOrganization",
  "name": "The Tzeitung",
  "alternateName": ["Di Tzeitung", "Dee Tzeitung", "The Tzeitung Newspaper", "News Report", "The Yiddish Newspaper of Record", "די צייטונג", "די זעלבסטשטענדיגע אידישע צייטונג"],
  "url": "https://thetzeitung.com/",
  "logo": "https://thetzeitung.com/covers/favicon.png",
  "image": "https://thetzeitung.com/""" + LATEST_COVER + """",
  "description": "The Tzeitung (Di Tzeitung, News Report) is the independent Yiddish weekly newspaper, published every week for forty years and read by thousands around the world.",
  "telephone": "+1-718-851-6607",
  "email": "mk@thetzeitung.com",
  "address": {"@type": "PostalAddress", "streetAddress": "445 Park Avenue, Suite 202", "addressLocality": "Brooklyn", "addressRegion": "NY", "postalCode": "11205", "addressCountry": "US"},
  "areaServed": "Worldwide",
  "knowsLanguage": ["yi", "en"]
}
</script>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "The Tzeitung",
  "alternateName": ["TheTzeitung.com", "Di Tzeitung", "די צייטונג"],
  "url": "https://thetzeitung.com/",
  "inLanguage": "en",
  "publisher": {"@type": "NewsMediaOrganization", "name": "The Tzeitung", "url": "https://thetzeitung.com/"}
}
</script>"""

def shell(title, desc, body, page="index.html"):
    nav = "".join(f'<li><a href="{h}">{t}</a></li>' for h, t in NAV)
    url = SITE if page == "index.html" else SITE + page
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="The Tzeitung">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE}{LATEST_COVER}">
  <meta name="twitter:card" content="summary_large_image">
  {ORG_JSONLD}
  <meta name="theme-color" content="#0E7C3F">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500;1,600&family=Jost:wght@400;500&family=Frank+Ruhl+Libre:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css?v={CSS_V}">
  <link rel="icon" href="covers/favicon.png">
</head>
<body>

<header class="top">
  <span class="bsd">בס"ד</span>
  <div class="wrap">
    <a class="brand" href="index.html">
      <img src="covers/logo-yiddish.png" alt="The Tzeitung — די צייטונג" width="1140" height="270">
      <span>News Report<br>Independent for forty years</span>
    </a>
    <button class="menu-btn" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav id="nav">
      <ul>{nav}<li><a class="cta" href="subscribe.html">Subscribe</a></li></ul>
    </nav>
  </div>
</header>

{body}

<footer class="site-footer">
  
  <div class="wrap">
    <div class="grid">
      <div>
        <a class="wordmark" href="index.html"><img src="covers/logo-yiddish.png" alt="The Tzeitung" width="1140" height="270"></a>
        <img class="nr" src="covers/logo-newsreport.png" alt="News Report — The Yiddish Newspaper of Record" width="600" height="165">
        <p style="margin-top:18px">The independent Yiddish newspaper. Published every week for forty years, read by thousands of families around the world.</p>
      </div>
      <div>
        <h4>Call us</h4>
        <p>{ADDRESS}<br><span class="em">{PHONE}</span></p>
      </div>
      <div>
        <h4>Write to us</h4>
        <p>General inquiries<br><a class="em" href="mailto:mk@thetzeitung.com">mk@thetzeitung.com</a></p>
        <p>Editor and letters<br><a class="em" href="mailto:yt@thetzeitung.com">yt@thetzeitung.com</a></p>
        <p>Billing<br><a class="em" href="mailto:billing@thetzeitung.com">billing@thetzeitung.com</a></p>
      </div>
    </div>
    <div class="bottom">
      <span>© <span id="year"></span> The Tzeitung · TheTzeitung.com</span>
      <span><a href="advertise.html">Advertise</a> &nbsp;&nbsp; <a href="subscribe.html">Subscribe</a> &nbsp;&nbsp; <a href="index.html#email">Email list</a> &nbsp;&nbsp; <a href="contact.html">Contact</a></span>
    </div>
  </div>
</footer>

<div class="lightbox" role="dialog" aria-modal="true" aria-label="Cover preview">
  <button class="lb-close" type="button" aria-label="Close">&times;</button>
  <button class="lb-prev" type="button" aria-label="Previous cover">&#8249;</button>
  <figure><img src="" alt=""><figcaption></figcaption></figure>
  <button class="lb-next" type="button" aria-label="Next cover">&#8250;</button>
</div>
<script src="site.js?v={JS_V}"></script>
</body>
</html>
'''

def write(fname, html):
    open(os.path.join(ROOT, fname), "w", encoding="utf-8").write(html); print("wrote", fname)

def band(h1, p):
    return f'''<section class="band">
  <div class="wall" data-wall="{WALL}" data-rows="1" aria-hidden="true"></div>
  <div class="veil"></div>
  <div class="wrap"><h1>{h1}</h1><p>{p}</p></div>
</section>'''

CONTACT_ASIDE = f'''<aside class="aside">
  <h3>The office</h3>
  <p>{ADDRESS}</p>
  <p class="big">{PHONE}</p>
  <div class="line"></div>
  <p>General inquiries<br><a href="mailto:mk@thetzeitung.com"><b>mk@thetzeitung.com</b></a></p>
  <p>Editor and letters to the editor<br><a href="mailto:yt@thetzeitung.com"><b>yt@thetzeitung.com</b></a></p>
  <p>Billing and subscriptions<br><a href="mailto:billing@thetzeitung.com"><b>billing@thetzeitung.com</b></a></p>
  <div class="line"></div>
  <p>Office hours are Sunday to Thursday, 9 AM to 6 PM. Material for the coming edition is due Tuesday at 12 PM.</p>
</aside>'''


EMAIL_BAND = '''
<section class="emaillist" id="email">
  <div class="wrap grid">
    <div>
      <h2>Join our email list</h2>
      <p>This week's covers, news from The Tzeitung and the occasional announcement, straight to your inbox. Free, and you can leave any time.</p>
    </div>
    <form class="mc" action="https://thetzeitung.us19.list-manage.com/subscribe/post?u=32d4918dafef1c115c1d3f6bc&amp;id=cd1d1ef5a7" method="post" target="_blank" rel="noopener" novalidate>
      <div class="row">
        <div><label for="mc-fname">First name</label><input id="mc-fname" type="text" name="FNAME" autocomplete="given-name"></div>
        <div><label for="mc-email">Email address</label><input id="mc-email" type="email" name="EMAIL" autocomplete="email" required></div>
      </div>
      <div style="position:absolute;left:-5000px" aria-hidden="true"><input type="text" name="b_32d4918dafef1c115c1d3f6bc_cd1d1ef5a7" tabindex="-1" value=""></div>
      <button class="btn gold" type="submit" name="subscribe">Join the list</button>
      <span class="note">You'll get one email asking you to confirm.</span>
    </form>
  </div>
</section>
'''

HONEYPOT = '<p style="display:none"><label>Leave this empty: <input name="bot-field"></label></p>'

# ======================= HOME =======================
LATEST_SECTIONS = [(k, t, heb, d) for k, t, heb, d in SECTIONS if k in LATEST["covers"]]
slides_html = "".join(f'''
        <a class="slide{" on" if i==0 else ""}" href="{LATEST["covers"][k]}" data-zoom="{LATEST["covers"][k]}" data-i="{i}" aria-label="{t}">
          <img src="{LATEST["covers"][k]}" alt="{t}" width="900" height="980"{"" if i==0 else ' loading="lazy"'}>
        </a>''' for i, (k, t, heb, _) in enumerate(LATEST_SECTIONS))

picker_html = "".join(f'''
        <button class="pick{" on" if i==0 else ""}" data-i="{i}" type="button">
          <b>{t}</b><span class="heb">{heb}</span>
          <i class="bar"></i>
        </button>''' for i, (k, t, heb, _) in enumerate(LATEST_SECTIONS))

inside_html = "".join(f'''
      <article>
        <h3>{t}</h3>
        <span class="heb">{heb}</span>
        <p>{d}</p>
      </article>''' for _, t, heb, d in REGULAR)

home = f'''
<section class="hero">
  <div class="wall" data-wall="{WALL}" data-rows="2" aria-hidden="true"></div>
  <div class="veil"></div>
  
  <div class="wrap"><div class="inner">
    <div class="wordmark"><img src="covers/logo-yiddish.png" alt="The Tzeitung — די צייטונג" width="1140" height="270"></div>
    <img class="nr" src="covers/logo-newsreport.png" alt="News Report — The Yiddish Newspaper of Record" width="600" height="165">
    <h1>The Yiddish newspaper of record.</h1>
    <p>Independent since the first edition, The Tzeitung has been published every week for forty years and is read by thousands of families around the world. A fresh edition reaches the stores every Wednesday morning.</p>
    <div class="btn-row"><a class="btn gold" href="subscribe.html">Subscribe</a><a class="btn ghost" href="advertise.html">Advertise with us</a></div>
  </div></div>
</section>

<section class="section surface parchment">
  <div class="wrap">
    <div class="sec-head">
      <h2>This week's edition</h2>
      <p>Volume {EDITION_VOL}, number {EDITION_NO}, <span class="heb">{EDITION_PARSHA}</span>, for the week of {EDITION_DATE}. <a href="archive.html">Past editions</a></p>
    </div>
    <div class="showcase" id="showcase">
      <div class="stage">{slides_html}
      </div>
      <div class="picker">{picker_html}
        <p class="pick-note">Each section, every week. Tap a cover to see it full size.</p>
      </div>
    </div>
  </div>
</section>

<section class="statement">
  
  <div class="wrap">
    <div class="rule"></div>
    <p>Forty years in print. Thousands of readers around the world. A fresh edition in the stores every Wednesday morning.</p>
    <div class="rule"></div>
  </div>
</section>

<section class="section surface ivory">
  <div class="wrap">
    <div class="sec-head">
      <h2>Inside every edition</h2>
      <p>Three sections, one newspaper</p>
    </div>
    <div class="inside">{inside_html}
    </div>
  </div>
</section>

<section class="section surface parchment subscribe" id="subscribe">
  <div class="wrap grid">
    <div>
      <h2>Have it delivered every week.</h2>
      <p class="lead">Every edition, with both supplements, mailed to your home anywhere in the United States.</p>
      <ul class="prices">
        <li><b>$400</b><span>for a year</span></li>
        <li><b>$200</b><span>for half a year</span></li>
      </ul>
      <p class="call">Prefer to order by phone? Call <b>{PHONE}</b></p>
    </div>
    <div class="panel">
      <h3>Order a subscription</h3>
      <p class="hint">We will call you within two business days to confirm.</p>
      <form class="form" name="subscribe" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
        <input type="hidden" name="form-name" value="subscribe">{HONEYPOT}
        <div class="row">
          <div><label for="s-name">Full name</label><input id="s-name" type="text" name="name" required></div>
          <div><label for="s-phone">Phone</label><input id="s-phone" type="tel" name="phone" required></div>
        </div>
        <div><label for="s-email">Email</label><input id="s-email" type="email" name="email"></div>
        <div><label for="s-address">Delivery address</label><input id="s-address" type="text" name="address" required></div>
        <div><label for="s-plan">Plan</label><select id="s-plan" name="plan"><option>One year, $400</option><option>Half a year, $200</option></select></div>
        <button class="btn" type="submit">Order subscription</button>
      </form>
    </div>
  </div>
</section>
{EMAIL_BAND}
'''
write("index.html", shell("The Tzeitung (Di Tzeitung, די צייטונג) — News Report, the Yiddish newspaper of record",
  "The Tzeitung, also written Di Tzeitung or Dee Tzeitung (די צייטונג), is News Report, the independent Yiddish weekly newspaper, published every week for forty years and read by thousands around the world. Subscriptions, advertising and this week's covers.", home))

# ======================= ABOUT =======================
about = band("About The Tzeitung", "Forty years of the independent Yiddish newspaper.") + f'''
<section class="page-body surface parchment"><div class="wrap two-col">
  <div class="prose">
    <p class="lead">The Tzeitung, written in Yiddish as די צייטונג and often spelled Di Tzeitung or Dee Tzeitung, is Di Zelbstshtendige Yiddishe Tzeitung, the independent Yiddish newspaper. It was founded forty years ago by Rabbi Avrohom Friedman, who leads it to this day as founder and editor-in-chief.</p>
    <p>Published every week in Yiddish and known in English as News Report, The Yiddish Newspaper of Record, it has become one of the enduring institutions of the Yiddish printed word in America. A fresh edition reaches the stores every Wednesday morning.</p>
    <h2>Who reads it</h2>
    <p>Thousands of readers around the world: the Yiddish-speaking communities of Brooklyn, in Boro Park, Williamsburg and Flatbush, together with Kiryas Joel, Monsey, Lakewood and other heimishe communities across the United States, and readers in Canada, London, Belgium and Eretz Yisroel.</p>
    <h2>How we report</h2>
    <p>Our mission is to bring the news with an impartial eye. The Tzeitung does not take sides in internal community disputes. Readers deserve clear, accurate reporting, and nothing more. In general American politics the paper keeps a measured tone, with the aim of maintaining good relations with local, city and federal agencies for the benefit of the community.</p>
    <h2>Inside every edition</h2>
    <p><b>The main section.</b> General news and politics, news from America and around the world, business and the economy, and what is happening in the heimishe community.</p>
    <p><b>Yiddishe Tzeit.</b> The weekly supplement of history and heritage: the Jewish towns of yesteryear, great personalities, and memoirs passed down through the generations.</p>
    <p><b>Chassidishe Tzeit.</b> Chassidishe news from around the world, with the popular picture section of Rebbes, chassidishe courts, simchos and events.</p>
    <h2>Forty years</h2>
    <p>Like every printed newspaper, The Tzeitung has weathered rising paper and printing costs and a changing media landscape. Through it all it remains one of the enduring voices of the Yiddish-speaking community, and we are grateful that you are part of it.</p>
  </div>
  {CONTACT_ASIDE}
</div></section>
'''
write("about.html", shell("About — The Tzeitung", "The history and mission of The Tzeitung, the independent Yiddish newspaper, forty years in print.", about, page="about.html"))

# ======================= SUBSCRIPTIONS =======================
subscribe = band("Subscriptions", "Every edition, with both supplements, mailed to your home anywhere in the United States.") + f'''
<section class="page-body surface parchment"><div class="wrap">
  <div class="promo"><img src="ads/promo-2.jpg" alt="יעדע וואך פונדאסניי, א פרישער געשמאק צום טיר. Subscribe to The Tzeitung." width="1155" height="1173"></div>
  <div class="plans">
    <div class="plan">
      <img src="{LATEST_COVER}" alt="" width="900" height="980">
      <div>
        <h3>One year</h3>
        <div class="price"><b>$400</b><span>renews every 12 months</span></div>
        <a href="#order" class="btn">Choose this plan</a>
      </div>
    </div>
    <div class="plan">
      <img src="{LATEST_COVER}" alt="" width="900" height="980">
      <div>
        <h3>Half a year</h3>
        <div class="price"><b>$200</b><span>renews every 6 months</span></div>
        <a href="#order" class="btn ghost-dark">Choose this plan</a>
      </div>
    </div>
  </div>

  <div class="two-col" id="order">
    <div class="panel">
      <h3>Order a subscription</h3>
      <p class="hint">We will call you within two business days to confirm your order and arrange payment.</p>
      <form class="form" name="subscribe" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
        <input type="hidden" name="form-name" value="subscribe">{HONEYPOT}
        <div class="row">
          <div><label for="name">Full name</label><input id="name" type="text" name="name" required></div>
          <div><label for="phone">Phone</label><input id="phone" type="tel" name="phone" required></div>
        </div>
        <div><label for="email">Email</label><input id="email" type="email" name="email"></div>
        <div><label for="address">Delivery address</label><input id="address" type="text" name="address" placeholder="Street, city, state, ZIP" required></div>
        <div class="row">
          <div><label for="plan">Plan</label><select id="plan" name="plan"><option>One year, $400</option><option>Half a year, $200</option></select></div>
          <div><label for="gift">Is this a gift?</label><select id="gift" name="gift"><option>No</option><option>Yes, include a card</option></select></div>
        </div>
        <div><label for="notes">Notes</label><textarea id="notes" name="notes" style="min-height:80px"></textarea></div>
        <button class="btn" type="submit">Order subscription</button>
      </form>
    </div>
    <aside class="aside">
      <h3>Prefer to call?</h3>
      <p>We can set you up in two minutes.</p>
      <p class="big">{PHONE}</p>
      <div class="line"></div>
      <h3>Where we deliver</h3>
      <p>Boro Park, Williamsburg, Flatbush, Kiryas Joel, Monsey and Lakewood, and by mail anywhere in the United States.</p>
      <div class="line"></div>
      <h3>Shuls, yeshivos and businesses</h3>
      <p>Special rates for multiple copies. Call the office or write to <a href="mailto:billing@thetzeitung.com"><b>billing@thetzeitung.com</b></a>.</p>
    </aside>
  </div>
</div></section>
{EMAIL_BAND}
'''
write("subscribe.html", shell("Subscriptions — The Tzeitung", "Subscribe to The Tzeitung and have every edition delivered to your home.", subscribe, page="subscribe.html"))

# ======================= ADVERTISE =======================
advertise = band("Advertise", "Reach thousands of heimishe households around the world every week, in a newspaper that stays on the table all week long.") + f'''
<section class="page-body surface parchment"><div class="wrap">
  <div class="rates">
    <table>
      <thead><tr><th>Size</th><th>Dimensions, width by height</th><th>Rate</th></tr></thead>
      <tbody>
        <tr><td>Full page</td><td>9.7" × 11"</td><td>$1,200</td></tr>
        <tr><td>Three-quarter page</td><td>7" × 8"</td><td>$750</td></tr>
        <tr><td>Half page, landscape</td><td>9.7" × 5.4"</td><td>$600</td></tr>
        <tr><td>Half page, vertical</td><td>4.7" × 11"</td><td>$600</td></tr>
        <tr><td>Two-thirds page</td><td>5.2" × 8"</td><td>$500</td></tr>
        <tr><td>Two-thirds page, short</td><td>5.2" × 7"</td><td>$425</td></tr>
        <tr><td>Quarter page</td><td>4.7" × 5.4"</td><td>$300</td></tr>
        <tr><td>Eighth page</td><td>4.7" × 2.2"</td><td>$150 <small>plus $40 per additional inch of height</small></td></tr>
        <tr><td>Business card</td><td>4.7" × 1.4"</td><td>$75</td></tr>
        <tr><td>Classified</td><td>2.3" × 1"</td><td>$17</td></tr>
        <tr class="hl"><td>Front strip</td><td>10" × 1"</td><td>$350</td></tr>
        <tr class="hl"><td>Front strip, double</td><td>10" × 2"</td><td>$550</td></tr>
        <tr class="hl"><td>Front cover box</td><td>2" × 2"</td><td>$150</td></tr>
      </tbody>
    </table>
    <p class="note">Color is included at no extra charge. Ads are due Tuesday at 12 PM for that week's edition. <a href="The-Tzeitung-Ad-Rates.pdf" target="_blank">Download the rate card</a></p>
  </div>

  <div class="two-col">
    <div class="panel">
      <h3>Reserve space</h3>
      <p class="hint">Tell us what you would like to advertise and we will confirm placement and specifications.</p>
      <form class="form" name="advertise" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
        <input type="hidden" name="form-name" value="advertise">{HONEYPOT}
        <div class="row">
          <div><label for="a-name">Name or business</label><input id="a-name" type="text" name="name" required></div>
          <div><label for="a-phone">Phone</label><input id="a-phone" type="tel" name="phone" required></div>
        </div>
        <div><label for="a-email">Email</label><input id="a-email" type="email" name="email" required></div>
        <div class="row">
          <div><label for="a-size">Size</label><select id="a-size" name="size"><option>Full page</option><option>Three-quarter page</option><option>Half page</option><option>Two-thirds page</option><option>Quarter page</option><option>Eighth page</option><option>Business card</option><option>Classified</option><option>Front strip</option><option>Front cover box</option><option>Not sure yet</option></select></div>
          <div><label for="a-weeks">How many weeks</label><select id="a-weeks" name="weeks"><option>One week</option><option>Four weeks</option><option>Twelve weeks</option><option>A full year</option></select></div>
        </div>
        <div><label for="a-msg">What would you like to advertise?</label><textarea id="a-msg" name="message" required></textarea></div>
        <button class="btn" type="submit">Send request</button>
      </form>
    </div>
    <aside class="aside">
      <h3>Advertising</h3>
      <p class="big">{PHONE}</p>
      <p><a href="mailto:mk@thetzeitung.com"><b>mk@thetzeitung.com</b></a></p>
      <p>Billing: <a href="mailto:billing@thetzeitung.com"><b>billing@thetzeitung.com</b></a></p>
      <div class="line"></div>
      <h3>Why The Tzeitung</h3>
      <p>A newspaper that stays on the table all week, at home, in shul and in the store, read by thousands of families around the world.</p>
    </aside>
  </div>
</div></section>
'''
write("advertise.html", shell("Advertise — The Tzeitung", "Advertising rates and sizes for The Tzeitung, read by thousands of Yiddish-speaking families every week.", advertise, page="advertise.html"))

# ======================= CONTACT =======================
contact = band("Contact", "For the editor, letters, subscriptions and advertising, or to send in articles and photos.") + f'''
<section class="page-body surface parchment"><div class="wrap two-col">
  <div class="panel">
    <h3>Send a message</h3>
    <p class="hint">We read everything and reply as soon as we can.</p>
    <form class="form" name="contact" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
      <input type="hidden" name="form-name" value="contact">{HONEYPOT}
      <div class="row">
        <div><label for="c-name">Name</label><input id="c-name" type="text" name="name" required></div>
        <div><label for="c-phone">Phone</label><input id="c-phone" type="tel" name="phone"></div>
      </div>
      <div><label for="c-email">Email</label><input id="c-email" type="email" name="email" required></div>
      <div><label for="c-topic">This is about</label><select id="c-topic" name="topic"><option>A general question</option><option>A letter to the editor</option><option>A news tip</option><option>Sending in an article</option><option>Sending in photos</option><option>My subscription</option><option>Advertising</option><option>A correction</option></select></div>
      <div><label for="c-msg">Message</label><textarea id="c-msg" name="message" required></textarea></div>
      <button class="btn" type="submit">Send message</button>
    </form>
  </div>
  {CONTACT_ASIDE}
</div></section>
'''
write("contact.html", shell("Contact — The Tzeitung", "Contact The Tzeitung.", contact, page="contact.html"))

# ======================= ARCHIVES =======================
# Grouped by Hebrew year, then by month; an edition is headed by its Hebrew date
# (a yom tov edition by the yom tov), with the parsha, the civil date and its number.
from pyluach import dates as hdates
SECTION_NAME = {k: (t, heb) for k, t, heb, _ in SECTIONS}

def heb_year_of(key):
    # the year of the Tuesday after: an edition that comes out for Rosh Hashana belongs to the new year
    y, m, d = map(int, key.split("-"))
    return hdates.HebrewDate.from_pydate(date(y, m, d) + timedelta(days=4)).year
def heb_month_of(key):
    y, m, d = map(int, key.split("-"))
    hd = hdates.HebrewDate.from_pydate(date(y, m, d))
    return hd.month_name(hebrew=True)
YOMIM_TOVIM = [(7, 1, "ראש השנה"), (7, 10, "יום כיפור"), (7, 15, "סוכות"), (1, 15, "פסח"), (3, 6, "שבועות")]
def yomtov_of(key):
    """The yom tov this edition comes out for: one falling between the Wednesday the paper
    appears and the Tuesday after, e.g. ערב סוכות; the calendar's own holiday for that Shabbos
    (chol hamoed, a yom tov on Shabbos) is in the parsha field already."""
    y, m, d = map(int, key.split("-"))
    f = date(y, m, d)
    found = None
    for off in range(-1, 5):            # the Thursday before through the Tuesday after; the later yom tov wins
        hd = hdates.HebrewDate.from_pydate(f + timedelta(days=off))
        for mo, da, name in YOMIM_TOVIM:
            if hd.month == mo and hd.day == da: found = (name, hd.hebrew_date_string().split()[-1])
    return found

def heb_year_label(key):
    return hdates.HebrewDate.from_pydate(date(*map(int, key.split("-"))) + timedelta(days=4)).hebrew_date_string().split()[-1]

def edition_block(ed):
    figs = "".join(f"""
      <figure data-k="{k}" data-s="{search_blob(ed, k).replace('"', "&quot;")}">
        <a href="{ed["covers"][k]}" data-zoom="{ed["covers"][k]}" aria-label="{SECTION_NAME[k][0]}, {nice_date(ed["date"])}"><img src="{ed["covers"][k]}" alt="{SECTION_NAME[k][0]}, {nice_date(ed["date"])}" width="900" height="980" loading="lazy"></a>
        <figcaption>{SECTION_NAME[k][0]}<span class="heb">{SECTION_NAME[k][1]}</span></figcaption>
      </figure>""" for k, _, _, _ in SECTIONS if k in ed["covers"])
    number = f'<span class="no">No. {ed["no"]}</span>' if ed.get("no") else ""
    parsha = ed.get("parsha") or ""
    hdate = ed.get("hdate") or ""
    yt = yomtov_of(ed["date"])
    yomtov = yt[0] if yt else (parsha if parsha and not parsha.startswith("פ'") else None)
    if yomtov and hdate:
        # a yom tov edition is headed by the yom tov and its year, e.g. סוכות תשפ״ז
        heading = f'<span class="heb">{yomtov} {yt[1] if yt else (ed.get("hyear") or hdate.split()[-1])}</span>'
        meta = [f'<span class="heb">{hdate}</span>', parsha_html(ed) if parsha.startswith("פ'") else "", nice_date(ed["date"])]
    else:
        heading = f'<span class="heb">{hdate}</span>' if hdate else nice_date(ed["date"])
        meta = [parsha_html(ed), nice_date(ed["date"])]
    return f"""
  <section class="edition" id="e-{ed["date"]}" data-has="{"".join(sorted(ed["covers"]))}">
    <div class="ed-head"><h3>{heading}</h3><p>{", ".join(x for x in meta if x)}{number}</p></div>
    <div class="ed-covers" data-n="{len(ed["covers"])}">{figs}
    </div>
  </section>"""

# words that appear on most covers of a section are masthead boilerplate, not worth searching
from collections import Counter
def _norm(w): return re.sub(r"[\"״׳']", "", w.lower())
_freq = {k: Counter() for k, _, _, _ in SECTIONS}; _count = {k: 0 for k, _, _, _ in SECTIONS}
for ed in EDITIONS.values():
    for sec, txt in ed.get("texts", {}).items():
        if sec in _freq:
            _count[sec] += 1; _freq[sec].update(set(_norm(w) for w in txt.split()))
BOILER = {sec: {w for w, n in _freq[sec].items() if _count[sec] >= 5 and n > 0.4 * _count[sec]} for sec in _freq}

def search_blob(ed, sec):
    words = [w for w in ed.get("texts", {}).get(sec, "").split() if _norm(w) not in BOILER[sec]][:160]
    y, m, d = map(int, ed["date"].split("-"))
    bits = [SECTION_NAME[sec][0], SECTION_NAME[sec][1], nice_date(ed["date"]), ed["date"], date(y, m, d).strftime("%b %Y"),
            ed.get("hdate", ""), ed.get("hyear", ""), heb_month_of(ed["date"]),
            (ed.get("parsha") or "").replace(", ", "-"), (ed.get("parsha") or "").replace("פ' ", ""), " ".join(yomtov_of(ed["date"]) or ()),
            f"number {ed['no']} no {ed['no']} #{ed['no']}" if ed.get("no") else ""]
    return " ".join(bits + words)

# years, newest first; months within a year in reading order (newest first too)
YEARS = []
for k in EDITION_KEYS:
    hy = heb_year_of(k)
    if not YEARS or YEARS[-1][0] != hy: YEARS.append((hy, heb_year_label(k), []))
    YEARS[-1][2].append(k)

def span_of(keys):
    a, b = date(*map(int, keys[-1].split("-"))), date(*map(int, keys[0].split("-")))
    if a.year == b.year:
        return f"{a.strftime('%B')} to {b.strftime('%B %Y')}" if a.month != b.month else b.strftime("%B %Y")
    return f"{a.strftime('%B %Y')} to {b.strftime('%B %Y')}"

def year_block(hy, label, keys):
    months = []
    for k in keys:
        mn = heb_month_of(k)
        if not months or months[-1][0] != mn: months.append((mn, []))
        months[-1][1].append(k)
    body = "".join(f"""
    <div class="month">
      <div class="month-rule"><span class="heb">{mn}</span></div>{"".join(edition_block(EDITIONS[k]) for k in mk)}
    </div>""" for mn, mk in months)
    n = len(keys)
    return f"""
  <div class="year" id="y-{hy}">
    <div class="year-head"><h2 class="heb">{label}</h2><p>{n} edition{"s" if n != 1 else ""}, {span_of(keys)}</p></div>{body}
  </div>"""

archive_body = "".join(year_block(hy, label, keys) for hy, label, keys in YEARS)
year_links = "".join(f'<a href="#y-{hy}" class="heb">{label}</a>' for hy, label, _ in YEARS)
total_covers = sum(len(e["covers"]) for e in EDITIONS.values())
FIRST_KEY, LAST_KEY = EDITION_KEYS[-1], EDITION_KEYS[0]

archive = band("Archives", f'The covers of every edition since <span class="heb">{heb_year_label(FIRST_KEY)}</span>, by year and date. You may request back issues or a copy of a past article from the office.') + f"""
<section class="page-body surface parchment archive"><div class="wrap">
  <div class="finder">
    <div class="archive-search">
      <input id="cover-search" type="search" placeholder="Find a cover: a date, a parsha, a yom tov, a headline, a name" autocomplete="off" aria-label="Search the covers">
      <span class="hits" id="search-hits"></span>
    </div>
    <div class="archive-tools">
      <div class="filters" role="group" aria-label="Show">
        <button class="on" data-k="all" type="button">All sections</button>
        {"".join(f'<button data-k="{k}" type="button">{t}</button>' for k, t, _, _ in SECTIONS)}
      </div>
    </div>
  </div>
  <nav class="years" aria-label="Jump to a year"><span class="lbl">Year</span>{year_links}</nav>
  <p class="none">No cover matches that. Try a parsha, a yom tov, a month or a year, or a word from a headline.</p>
  {archive_body}
  <div class="aside" style="margin:70px auto 0;max-width:720px;text-align:center">
    <h3>Looking for a particular issue?</h3>
    <p>For back issues, special editions or a copy of a specific article, call {PHONE} or write to <a href="mailto:mk@thetzeitung.com"><b>mk@thetzeitung.com</b></a>.</p>
  </div>
</div></section>
"""
write("archive.html", shell("Archives — The Tzeitung", f"The covers of every edition of The Tzeitung since {heb_year_label(FIRST_KEY)}, by Hebrew year and date, with a search of every cover.", archive, page="archive.html"))

# ======================= THANKS =======================
thanks = band("Thank you", "We received your message and will be in touch shortly.") + '''
<section class="page-body surface parchment"><div class="wrap">
  <div class="btn-row"><a href="index.html" class="btn">Back to the home page</a><a href="subscribe.html" class="btn ghost-dark">See subscriptions</a></div>
</div></section>
'''
write("thanks.html", shell("Thank you — The Tzeitung", "Thank you.", thanks, page="thanks.html"))
