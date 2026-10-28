# Generates the inner pages from shared header/footer. Run: python3 _build/build.py
import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

index = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
head_end = index.index("<!-- ===== HERO ===== -->")
foot_start = index.index("<!-- ===== FOOTER ===== -->")
HEADER = index[:head_end]
FOOTER = index[foot_start:]

def page(fname, title, desc, h1, lede, body):
    h = HEADER.replace("<title>די צייטונג — די זעלבסטשטענדיגע אידישע צייטונג</title>", f"<title>{title} — די צייטונג</title>")
    h = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{desc}">', h)
    h = h.replace('href="#sections"', 'href="index.html#sections"')
    html = f'''{h}<section class="page-head"><div class="wrap"><h1>{h1}</h1><p>{lede}</p></div></section>
<section class="page-body"><div class="wrap">
{body}
</div></section>

{FOOTER.replace('href="#sections"', 'href="index.html#sections"').replace('href="#subscribe"', 'href="index.html#subscribe"')}'''
    open(os.path.join(ROOT, fname), "w", encoding="utf-8").write(html)
    print("wrote", fname)

CONTACT_ASIDE = '''<aside class="aside">
  <h3>רעדאקציע און אפיס</h3>
  <p><b>די צייטונג</b><br>1281 49th Street<br>Brooklyn, NY 11219</p>
  <div class="line"></div>
  <p><b>טעלעפאן:</b> <a href="tel:7188516607">718-851-6607</a></p>
  <p><b>אימעיל:</b> <a href="mailto:mail@ditzeitung.com">mail@ditzeitung.com</a></p>
  <div class="line"></div>
  <p class="small muted">אפיס שעות: זונטאג–דאנערשטאג, 9:00–6:00. דעדליין פאר מאטעריאל: מאנטאג 5:00 נאכמיטאג.</p>
</aside>'''

# ---------- about ----------
page("about.html", "וועגן אונז", "די געשיכטע און שיטה פון די צייטונג, די זעלבסטשטענדיגע אידישע צייטונג, געגרינדעט 1988 אין בארא פארק.",
 "וועגן די צייטונג", "די זעלבסטשטענדיגע אידישע צייטונג — זינט תשמ״ח, יעדע מיטוואך, אן א וואך פארפעלט.",
 f'''<div class="two-col">
<div class="prose">
<p class="dropcap" style="font-family:var(--serif);font-size:21px;line-height:1.55">די צייטונג איז געגרינדעט געווארן אין יאר 1988 אין בארא פארק, ברוקלין, דורך הרב אברהם פרידמאן, וועלכער פירט עס ביז היינט אלס מייסד און הויפט רעדאקטאר. פון דעמאלט אן ערשיינט זי יעדע מיטוואך אויף דער אידישער שפראך, און באדינט די אידיש-רעדנדע קהילות אין בארא פארק, וויליאמסבורג, קרית יואל, מאנסי, לעיקוואד און אנדערע חרדי'שע ישובים איבער אמעריקע.</p>

<h2>אונזער שיטה</h2>
<p>אונזער דערקלערטע מיסיע איז צו ברענגען נייעס מיט אן אומפארטייאישן בליק. די צייטונג מישט זיך קיינמאל נישט אריין אין אינערליכע חסידישע מחלוקת'ן אדער קהילה קריגערייען. מיר גלייבן אז דער לייענער פארדינט קלארע, ריכטיגע נייעס — און נישט מער.</p>
<p>אין דער אלגעמיינער אמעריקאנער פאליטיק האלט די רעדאקציע א מעסיגן טאן, מיט'ן ציל צו האלטן גוטע באציאונגען מיט די לאקאלע, שטאטישע און פעדעראלע רעגירונגס אינסטאנצן לטובת הכלל.</p>

<h2>וואס מיר ברענגען יעדע וואך</h2>
<h3>הויפט אפטיילונג</h3>
<p>אלגעמיינע פאליטיק, אמעריקאנער נייעס, וועלט נייעס, עקאנאמיע, און נייעס פונעם היימישן ציבור — אלץ אויף א רייכן און ריינעם אידיש.</p>
<h3>דער אידישער צייט</h3>
<p>דער באליבטער וואכנטליכער מוסף וואס קומט מיט די צייטונג, מיט היסטארישע ארטיקלען, חסידישע מעשיות, תורני'שע קולומס און השקפה ארטיקלען.</p>
<h3>בילדער אפטיילונג</h3>
<p>די פאפולערע גאלעריעס פון רבי'ס, חסידישע הויפן, שמחות און אירועים פון איבער דער וועלט.</p>

<h2>37 יאר שפעטער</h2>
<p>ווי אלע געדרוקטע נייעס מעדיעס, האט די צייטונג איבער די יארן געמוזט שטיין קעגן די העכערונגען אין פאפיר און דרוקעריי פרייזן און די ענדערונגען אינעם מארקעט. טראץ אלעם בלייבט זי איינע פון די בולטע און היסטארישע אינסטיטוציעס אינעם אידיש-געדרוקטן ווארט אין אמעריקע — און מיר זענען שטאלץ אז איר זענט א טייל דערפון.</p>
</div>
{CONTACT_ASIDE}
</div>''')

# ---------- subscribe ----------
page("subscribe.html", "אבאנירט זיך", "באקומט די צייטונג יעדע מיטוואך אהיים — היים צושטעלונג אין ברוקלין און איבער אמעריקע.",
 "אבאנירט זיך", "באקומט די צייטונג יעדע מיטוואך גלייך צו אייער טיר — מיט אלע מוספים.",
 '''<div class="plans">
  <div class="plan">
    <div class="pname">חודש'ליך</div>
    <div class="price">$18 <small>/ חודש</small></div>
    <ul><li>4–5 אויסגאבעס א חודש</li><li>אלע מוספים אריינגערעכנט</li><li>היים צושטעלונג אין ברוקלין</li><li>אפשטעלן ווען איר ווילט</li></ul>
    <a href="#form" class="btn ghost">קלייבט דעם פלאן</a>
  </div>
  <div class="plan featured">
    <span class="ribbon">מערסט פאפולער</span>
    <div class="pname">יערליך</div>
    <div class="price">$180 <small>/ יאר</small></div>
    <ul><li>52 אויסגאבעס — 2 חדשים אומזיסט</li><li>אלע מוספים אריינגערעכנט</li><li>היים צושטעלונג איבער אמעריקע</li><li>ערשטע צו באקומען ספעציעלע אויסגאבעס</li></ul>
    <a href="#form" class="btn">קלייבט דעם פלאן</a>
  </div>
  <div class="plan">
    <div class="pname">מתנה</div>
    <div class="price">$180 <small>/ יאר</small></div>
    <ul><li>שיקט א יאר צייטונג אלס מתנה</li><li>א שיינע באגריסונג קארטל</li><li>פאר א חתן-כלה, עלטערן, אדער א פריינד</li><li>מיר שטעלן צו אומעטום אין אמעריקע</li></ul>
    <a href="#form" class="btn ghost">קלייבט דעם פלאן</a>
  </div>
</div>
<p class="small muted" style="margin:14px 0 40px">* פרייזן זענען א דוגמא און קענען געענדערט ווערן. רופט <a href="tel:7188516607"><b>718-851-6607</b></a> פאר די אקטועלע פרייזן און גרופע אבאנעמענטן פאר מוסדות און געשעפטן.</p>

<div class="two-col" id="form">
  <div>
    <h2 class="serif" style="font-size:30px;margin-bottom:6px">באשטעלט אייער אבאנעמענט</h2>
    <p class="muted" style="margin-bottom:22px">פילט אויס די פארעם און מיר רופן אייך צוריק אין 1–2 ביזנעס טעג צו ענדיגן די באשטעלונג.</p>
    <form class="form" name="subscribe" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
      <input type="hidden" name="form-name" value="subscribe">
      <p style="display:none"><label>Don't fill this out: <input name="bot-field"></label></p>
      <div class="row">
        <div><label>פולער נאמען</label><input type="text" name="name" required></div>
        <div><label>טעלעפאן</label><input type="tel" name="phone" required></div>
      </div>
      <div><label>אימעיל</label><input type="email" name="email"></div>
      <div><label>אדרעס פאר צושטעלונג</label><input type="text" name="address" placeholder="גאס, שטאט, סטעיט, זיפ" required></div>
      <div class="row">
        <div><label>פלאן</label><select name="plan"><option>יערליך — $180</option><option>חודש'ליך — $18</option><option>מתנה — $180</option></select></div>
        <div><label>ווי האט איר געהערט פון אונז?</label><select name="source"><option>א פריינד</option><option>געזען די צייטונג</option><option>אינטערנעט</option><option>אנדערש</option></select></div>
      </div>
      <div><label>הערות</label><textarea name="notes" style="min-height:90px"></textarea></div>
      <button class="btn red" type="submit">שיקט די באשטעלונג</button>
    </form>
  </div>
  <aside class="aside">
    <h3>ליבערשט אויפן טעלעפאן?</h3>
    <p>רופט אונז און מיר שטעלן אייך אויף אין צוויי מינוט.</p>
    <p style="font-family:var(--serif);font-size:28px;font-weight:900"><a href="tel:7188516607">718-851-6607</a></p>
    <div class="line"></div>
    <h3>וואו שטעלן מיר צו?</h3>
    <p>בארא פארק, וויליאמסבורג, פלעטבוש, קרית יואל, מאנסי, לעיקוואד — און דורך דער פאסט אומעטום אין אמעריקע.</p>
    <div class="line"></div>
    <h3>געשעפטן און מוסדות</h3>
    <p>ספעציעלע פרייזן פאר ביהמ"דים, ישיבות, אפיסעס און געשעפטן וואס ווילן מערערע קאפיעס. <a href="contact.html" class="red"><b>פרעגט אונז</b></a>.</p>
  </aside>
</div>''')

# ---------- advertise ----------
page("advertise.html", "רעקלאמעס", "רעקלאמירט אין די צייטונג און דערגרייכט דעם אידיש-רעדנדן ציבור אין ניו יארק יעדע וואך.",
 "רעקלאמירט אין די צייטונג", "דער דירעקטסטער וועג צו דערגרייכן טויזנטער היימישע שטובער יעדע מיטוואך — זינט 1988.",
 '''<div class="hero" style="padding:0 0 40px;border:0">
  <div class="facts" style="margin:0 0 40px;padding:0;border:0;gap:40px">
    <div><b>37+</b><span>יאר געטרויט</span></div>
    <div><b>מיטוואך</b><span>יעדע וואך אין שטוב</span></div>
    <div><b>3</b><span>אפטיילונגען + מוסף</span></div>
    <div><b>100%</b><span>אידיש-רעדנדער ציבור</span></div>
  </div>
</div>
<div class="cards" style="margin-bottom:48px">
  <article class="card"><span class="tag">פארמאט</span><h3>פולע בלאט</h3><p>מאקסימאלע ווירקונג. אידעאל פאר גרויסע אנזאגן, אירועים און קאמפיינס.</p></article>
  <article class="card"><span class="tag">פארמאט</span><h3>האלבע בלאט</h3><p>דער באלאנס פון גרייס און פרייז. די מערסט פאפולערע אפציע ביי געשעפטן.</p></article>
  <article class="card"><span class="tag">פארמאט</span><h3>פערטל בלאט</h3><p>פארלאזליכע וואכנטליכע אנוועזנהייט פאר לאקאלע געשעפטן און סערוויסעס.</p></article>
  <article class="card"><span class="tag">פארמאט</span><h3>קליינע מודעות</h3><p>שידוכים, מזל טוב'ס, דירות, ארבעט, געזוכט/פארקויף — שנעל און ביליג.</p></article>
</div>
<div class="two-col">
  <div>
    <h2 class="serif" style="font-size:30px;margin-bottom:6px">פרעגט פאר פרייזן און דעדליינס</h2>
    <p class="muted" style="margin-bottom:22px">זאגט אונז וואס איר ווילט רעקלאמירן און מיר שיקן אייך א פרייז-ליסטע און די ספעסיפיקאציעס. דעדליין פאר רעקלאמעס: <b>מאנטאג 5:00 נאכמיטאג</b>.</p>
    <form class="form" name="advertise" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
      <input type="hidden" name="form-name" value="advertise">
      <p style="display:none"><label>Don't fill this out: <input name="bot-field"></label></p>
      <div class="row">
        <div><label>נאמען / געשעפט</label><input type="text" name="name" required></div>
        <div><label>טעלעפאן</label><input type="tel" name="phone" required></div>
      </div>
      <div><label>אימעיל</label><input type="email" name="email" required></div>
      <div class="row">
        <div><label>גרייס</label><select name="size"><option>פולע בלאט</option><option>האלבע בלאט</option><option>פערטל בלאט</option><option>קליינע מודעה</option><option>נאך נישט זיכער</option></select></div>
        <div><label>וויפיל וואכן?</label><select name="weeks"><option>1 וואך</option><option>4 וואכן</option><option>12 וואכן</option><option>א גאנץ יאר</option></select></div>
      </div>
      <div><label>וואס ווילט איר רעקלאמירן?</label><textarea name="message" required></textarea></div>
      <button class="btn red" type="submit">שיקט די אנפראגע</button>
    </form>
  </div>
  <aside class="aside">
    <h3>רעקלאמע אפטיילונג</h3>
    <p><b>טעלעפאן:</b> <a href="tel:7188516607">718-851-6607</a></p>
    <p><b>אימעיל:</b> <a href="mailto:mail@ditzeitung.com">mail@ditzeitung.com</a></p>
    <div class="line"></div>
    <h3>פארוואס די צייטונג?</h3>
    <p>א צייטונג וואס ליגט אויפן טיש א גאנצע וואך, אין שטוב, אין ביהמ"ד און אין געשעפט — נישט א רעקלאמע וואס פארשווינדט אין א סעקונדע.</p>
    <div class="line"></div>
    <h3>דיזיין הילף</h3>
    <p>האט איר נישט קיין גרייטע רעקלאמע? אונזער דיזיין טים קען עס מאכן פאר אייך.</p>
  </aside>
</div>''')

# ---------- contact ----------
page("contact.html", "קאנטאקט", "פארבינדט זיך מיט די צייטונג — רעדאקציע, רעקלאמעס, אבאנעמענטן און מאטעריאל אריינצושיקן.",
 "פארבינדט זיך מיט אונז", "פאר די רעדאקציע, אבאנעמענטן, רעקלאמעס, אדער אריינצושיקן מאטעריאל און בילדער.",
 f'''<div class="two-col">
  <div>
    <form class="form" name="contact" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="thanks.html">
      <input type="hidden" name="form-name" value="contact">
      <p style="display:none"><label>Don't fill this out: <input name="bot-field"></label></p>
      <div class="row">
        <div><label>נאמען</label><input type="text" name="name" required></div>
        <div><label>טעלעפאן</label><input type="tel" name="phone"></div>
      </div>
      <div><label>אימעיל</label><input type="email" name="email" required></div>
      <div><label>וועגן וואס?</label><select name="topic"><option>אלגעמיין</option><option>רעדאקציע / א נייעס טיפ</option><option>אריינשיקן אן ארטיקל</option><option>אריינשיקן בילדער</option><option>אבאנעמענט</option><option>רעקלאמעס</option><option>קאררעקציע</option></select></div>
      <div><label>אייער מעסעדזש</label><textarea name="message" required></textarea></div>
      <button class="btn red" type="submit">שיקט</button>
    </form>
  </div>
  {CONTACT_ASIDE}
</div>''')

# ---------- archive ----------
figs = "".join(f'''<figure><a href="subscribe.html"><img src="covers/cover-archive-{i}.svg" alt="אויסגאבע" width="440" height="600"></a><figcaption><b>{t}</b>הויפט אפטיילונג · דער אידישער צייט · בילדער</figcaption></figure>''' for i, t in [(1,"פאריגע וואך"),(2,"צוויי וואכן צוריק"),(3,"דריי וואכן צוריק"),(4,"פיר וואכן צוריק")])
page("archive.html", "ארכיוו", "ארכיוו פון די פריערדיגע אויסגאבעס פון די צייטונג.",
 "ארכיוו", "די פריערדיגע אויסגאבעס פון די צייטונג. אבאנענטן קענען בעטן פריערדיגע נומערן ביים אפיס.",
 f'''<div class="sec-head"><h2>לעצטע אויסגאבעס</h2><a href="subscribe.html">ווערט אן אבאנענט ←</a></div>
<div class="archive-grid covers">{figs}</div>
<div class="aside" style="margin-top:48px;max-width:720px">
  <h3>דארפט איר א ספעציפישע אויסגאבע?</h3>
  <p>פאר פריערדיגע נומערן, ספעציעלע אויסגאבעס, אדער א קאפיע פון א ספעציפישן ארטיקל, רופט <a href="tel:7188516607"><b>718-851-6607</b></a> אדער שרייבט צו <a href="mailto:mail@ditzeitung.com"><b>mail@ditzeitung.com</b></a>.</p>
</div>''')

# ---------- thanks ----------
page("thanks.html", "א דאנק", "א דאנק פאר אייער מעסעדזש.",
 "א גרויסן דאנק!", "מיר האבן באקומען אייער מעסעדזש און וועלן זיך פארבינדן מיט אייך בקרוב.",
 '''<p style="margin-bottom:20px">דערווייל, קוקט זיך אום אויף די וועבסייט:</p>
<div class="btn-row"><a href="/" class="btn">צוריק צום הויפט</a><a href="subscribe.html" class="btn ghost">אבאנירט זיך</a></div>''')
