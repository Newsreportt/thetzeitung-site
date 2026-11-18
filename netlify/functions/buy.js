// POST /.netlify/functions/buy — charge the card (tokenised in the browser by Sola's iFields) for
// one edition's PDF, answer with links the open page can download from, and send the buyer a
// letter with a link of its own. There is no lasting downloads page: once the page is closed, the
// letter is the way back, and that link too runs out after its hours.
const shop = require("./lib/shop.js");
const mail = require("./lib/mail.js");
const guard = require("./lib/guard.js");

const clean = (v, max) => (typeof v === "string" ? v.trim().slice(0, max) : "");

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return shop.json(405, { ok: false, error: "POST only" });
  if (!shop.ready()) return shop.json(503, { ok: false, error: "The PDF shop is not switched on yet." });
  let b; try { b = JSON.parse(event.body || "{}"); } catch (e) { return shop.json(400, { ok: false, error: "Bad request" }); }

  // a request that did not come from this site's own checkout is not served
  const origin = String(event.headers.origin || event.headers.referer || "");
  if (origin && !/^https:\/\/(www\.)?thetzeitung\.com(\/|$)/.test(origin) && !/^http:\/\/localhost/.test(origin))
    return shop.json(403, { ok: false, error: "Not allowed from there." });

  const item = clean(b.item, 800), cardToken = clean(b.cardToken, 300), cvvToken = clean(b.cvvToken, 300);
  const exp = clean(b.exp, 4), name = clean(b.name, 60), email = clean(b.email, 100), zip = clean(b.zip, 12), street = clean(b.street, 80);
  if (!cardToken) return shop.json(400, { ok: false, error: "The card number is missing." });
  if (!/^(0[1-9]|1[0-2])\d{2}$/.test(exp)) return shop.json(400, { ok: false, error: "The expiry date should be MM/YY." });
  if (!name) return shop.json(400, { ok: false, error: "Please give the name on the card." });
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return shop.json(400, { ok: false, error: "Please give an email address for the receipt." });

  const ip = (event.headers["x-nf-client-connection-ip"] || event.headers["client-ip"] || "").split(",")[0].trim();

  // a machine working through a list of stolen cards is stopped before the gateway is troubled
  if (guard.looksAutomated(b)) {
    console.log("automated attempt", ip);
    return shop.json(400, { ok: false, error: "Something went wrong with the form. Please reload the page and try again." });
  }
  const gate = await guard.check(ip);
  if (!gate.ok) { console.log("held back", ip, gate.error); return shop.json(gate.status, { ok: false, error: gate.error }); }

  let what;
  try { what = await shop.resolve(item); } catch (e) { return shop.json(400, { ok: false, error: e.message }); }

  const invoice = "TZ" + Date.now().toString(36).toUpperCase() + Math.random().toString(36).slice(2, 5).toUpperCase();
  let res;
  try {
    res = await shop.charge({ amount: what.amount, description: what.description, invoice, item, cardToken, cvvToken, exp, name, email, zip, street, ip });
  } catch (e) {
    await guard.note(ip, gate.rec, "error");
    console.error("gateway", e);
    return shop.json(502, { ok: false, error: "The payment service did not answer. Nothing was charged; please try again." });
  }
  if (res.xResult !== "A") {
    await guard.note(ip, gate.rec, res.xResult === "D" ? "declined" : "error");
    console.log("not approved", invoice, res.xResult, res.xError, res.xErrorCode);
    const why = res.xResult === "D" ? "The card was declined." : (res.xError || res.xStatus || "The payment did not go through.");
    return shop.json(402, { ok: false, error: why, declined: res.xResult === "D" });
  }

  await guard.note(ip, gate.rec, "approved");
  const { catalog: c } = await shop.catalog();
  const emailHours = c.email_hours || 48;
  const links = await shop.links(what.dates);
  // the purchase is written down, so the downloads page can count what it hands out
  try {
    await shop.putJson(`receipts/${invoice}.json`, {
      invoice, item, kind: what.kind, dates: what.dates, amount: shop.money(what.amount),
      refnum: String(res.xRefNum || ""), card: res.xMaskedCardNumber || "", name, email,
      bought_at: new Date().toISOString(), bought_ip: ip,
    });
  } catch (ex) { console.error("receipt not written", invoice, ex.message); }
  // the letter: its own links, good for longer than the ones in the page
  let emailed = false;
  try {
    const sent = await shop.links(what.dates, emailHours);
    const body = mail.receipt({ label: what.label, amount: shop.money(what.amount), refnum: String(res.xRefNum || ""),
                                card: res.xMaskedCardNumber || "", links: sent, hours: emailHours });
    await mail.send({ to: email, subject: `${mail.SITE_NAME} — your PDF (${what.label})`, html: body.html, text: body.text });
    emailed = true;
  } catch (ex) { console.error("letter not sent", invoice, email, ex.message); }

  // and the office is told, with everything needed to answer a reader who calls about it
  try {
    const note = mail.sale({
      invoice, label: what.label, kind: what.kind, dates: what.dates, amount: shop.money(what.amount),
      refnum: String(res.xRefNum || ""), card: res.xMaskedCardNumber || "", name, email,
      when: new Date().toLocaleString("en-US", { timeZone: "America/New_York" }) + " (New York)", emailed,
    });
    await mail.send({ to: mail.OFFICE, subject: `Sold: ${what.label} — $${shop.money(what.amount)}`,
                      html: note.html, text: note.text, replyTo: email });
  } catch (ex) { console.error("office not told", invoice, ex.message); }

  console.log("sold", invoice, item, shop.money(what.amount), res.xRefNum, res.xMaskedCardNumber, emailed ? "emailed" : "NOT emailed");
  return shop.json(200, {
    ok: true, item, kind: what.kind, label: what.label, amount: shop.money(what.amount),
    refnum: String(res.xRefNum || ""), invoice, card: res.xMaskedCardNumber || "", email, links,
    emailed, email_hours: emailHours,
  });
};
