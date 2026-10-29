# Generates every page of the site. Run: python3 _build/build.py
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAV = [("index.html", "Home"), ("archive.html", "Archives"), ("about.html", "About"),
       ("advertise.html", "Advertise"), ("index.html#email", "Email list"), ("contact.html", "Contact")]

import glob
WALL = ",".join("covers/wall/" + os.path.basename(f) for f in sorted(glob.glob(os.path.join(ROOT, "covers", "wall", "*.jpg"))))

PHONE = '<a href="tel:7188516607">718-851-6607</a>'
ADDRESS = "445 Park Avenue, Suite 202<br>Brooklyn, NY 11205"

SECTIONS = [
  ("sec-a.jpg", "The main section", "די צייטונג",
   "General news and politics, news from America and around the world, business and the economy, and what is happening in the heimishe community."),
  ("sec-b.jpg", "Yiddishe Tzeit", "אידישע צייט",
   "The weekly supplement of history and heritage: the Jewish towns of yesteryear, great personalities, and memoirs passed down through the generations."),
  ("sec-c.jpg", "Chassidishe Tzeit", "חסידישע צייט",
   "Chassidishe news from around the world, with the popular picture section of Rebbes, chassidishe courts, simchos and events."),
]

SITE = "https://thetzeitung.com/"

ORG_JSONLD = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "NewsMediaOrganization",
  "name": "The Tzeitung",
  "alternateName": ["Di Tzeitung", "Dee Tzeitung", "The Tzeitung Newspaper", "News Report", "The Yiddish Newspaper of Record", "די צייטונג", "די זעלבסטשטענדיגע אידישע צייטונג"],
  "url": "https://thetzeitung.com/",
  "logo": "https://thetzeitung.com/covers/favicon.png",
  "image": "https://thetzeitung.com/covers/sec-a.jpg",
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
  <meta property="og:image" content="{SITE}covers/sec-a.jpg">
  <meta name="twitter:card" content="summary_large_image">
  {ORG_JSONLD}
  <meta name="theme-color" content="#0E7C3F">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500;1,600&family=Jost:wght@400;500&family=Frank+Ruhl+Libre:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
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

<div class="lightbox" role="dialog" aria-label="Cover preview"><img src="" alt=""></div>
<script src="site.js"></script>
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
slides_html = "".join(f'''
        <a class="slide{" on" if i==0 else ""}" href="covers/{img}" data-zoom="covers/{img}" data-i="{i}" aria-label="{t}">
          <img src="covers/{img}" alt="{t}" width="1064" height="1158"{"" if i==0 else ' loading="lazy"'}>
        </a>''' for i, (img, t, heb, _) in enumerate(SECTIONS))

picker_html = "".join(f'''
        <button class="pick{" on" if i==0 else ""}" data-i="{i}" type="button">
          <b>{t}</b><span class="heb">{heb}</span>
          <i class="bar"></i>
        </button>''' for i, (img, t, heb, _) in enumerate(SECTIONS))

inside_html = "".join(f'''
      <article>
        <h3>{t}</h3>
        <span class="heb">{heb}</span>
        <p>{d}</p>
      </article>''' for _, t, heb, d in SECTIONS)

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
      <p>Volume 40, number 6, for the week of October 28, 2026</p>
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
      <img src="covers/sec-a.jpg" alt="" width="1064" height="1158">
      <div>
        <h3>One year</h3>
        <div class="price"><b>$400</b><span>every 12 months</span></div>
        <a href="#order" class="btn">Choose this plan</a>
      </div>
    </div>
    <div class="plan">
      <img src="covers/sec-a.jpg" alt="" width="1064" height="1158">
      <div>
        <h3>Half a year</h3>
        <div class="price"><b>$200</b><span>every 6 months</span></div>
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
      <div class="line"></div>
      <h3>Need an ad designed?</h3>
      <p>Our design team can create one for you. Mention it in your request.</p>
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
figs = "".join(f'<figure><a href="covers/{img}" data-zoom="covers/{img}"><img src="covers/{img}" alt="{t}" width="1064" height="1158" loading="lazy"></a><figcaption>{t}<span>{heb}</span></figcaption></figure>' for img, t, heb, _ in SECTIONS)
archive = band("Archives", "Covers from recent editions. Anyone may request back issues or a copy of a past article from the office.") + f'''
<section class="page-body surface parchment"><div class="wrap">
  <div class="sec-head"><h2>Volume 40, number 6</h2><p>The week of October 28, 2026</p></div>
  <div class="archive-grid">{figs}</div>
  <div class="aside" style="margin:70px auto 0;max-width:720px;text-align:center">
    <h3>Looking for a particular issue?</h3>
    <p>For back issues, special editions or a copy of a specific article, call {PHONE} or write to <a href="mailto:mk@thetzeitung.com"><b>mk@thetzeitung.com</b></a>.</p>
  </div>
</div></section>
'''
write("archive.html", shell("Archives — The Tzeitung", "Covers from recent editions of The Tzeitung.", archive, page="archive.html"))

# ======================= THANKS =======================
thanks = band("Thank you", "We received your message and will be in touch shortly.") + '''
<section class="page-body surface parchment"><div class="wrap">
  <div class="btn-row"><a href="index.html" class="btn">Back to the home page</a><a href="subscribe.html" class="btn ghost-dark">See subscriptions</a></div>
</div></section>
'''
write("thanks.html", shell("Thank you — The Tzeitung", "Thank you.", thanks, page="thanks.html"))
