// POST /.netlify/functions/buy — charge the card (tokenised in the browser by Sola's iFields) for
// one edition's PDF or a whole year, and answer with the download links and a signed token that
// brings the buyer back to them (pdfs.html?t=...) for the next weeks.
const shop = require("./lib/shop.js");

const clean = (v, max) => (typeof v === "string" ? v.trim().slice(0, max) : "");

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return shop.json(405, { ok: false, error: "POST only" });
  if (!shop.ready()) return shop.json(503, { ok: false, error: "The PDF shop is not switched on yet." });
  let b; try { b = JSON.parse(event.body || "{}"); } catch (e) { return shop.json(400, { ok: false, error: "Bad request" }); }

  const item = clean(b.item, 20), cardToken = clean(b.cardToken, 300), cvvToken = clean(b.cvvToken, 300);
  const exp = clean(b.exp, 4), name = clean(b.name, 60), email = clean(b.email, 100), zip = clean(b.zip, 12), street = clean(b.street, 80);
  if (!cardToken) return shop.json(400, { ok: false, error: "The card number is missing." });
  if (!/^(0[1-9]|1[0-2])\d{2}$/.test(exp)) return shop.json(400, { ok: false, error: "The expiry date should be MM/YY." });
  if (!name) return shop.json(400, { ok: false, error: "Please give the name on the card." });
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return shop.json(400, { ok: false, error: "Please give an email address for the receipt." });

  let what;
  try { what = await shop.resolve(item); } catch (e) { return shop.json(400, { ok: false, error: e.message }); }

  const invoice = "TZ" + Date.now().toString(36).toUpperCase() + Math.random().toString(36).slice(2, 5).toUpperCase();
  const ip = (event.headers["x-nf-client-connection-ip"] || event.headers["client-ip"] || "").split(",")[0].trim();
  let res;
  try {
    res = await shop.charge({ amount: what.amount, description: what.description, invoice, item, cardToken, cvvToken, exp, name, email, zip, street, ip });
  } catch (e) {
    console.error("gateway", e);
    return shop.json(502, { ok: false, error: "The payment service did not answer. Nothing was charged; please try again." });
  }
  if (res.xResult !== "A") {
    console.log("not approved", invoice, res.xResult, res.xError, res.xErrorCode);
    const why = res.xResult === "D" ? "The card was declined." : (res.xError || res.xStatus || "The payment did not go through.");
    return shop.json(402, { ok: false, error: why, declined: res.xResult === "D" });
  }

  const { catalog: c } = await shop.catalog();
  const days = c.token_days || 30;
  const token = shop.sign({ i: item, r: String(res.xRefNum || ""), n: invoice, exp: Math.floor(Date.now() / 1000) + days * 86400 });
  const links = await shop.links(what.dates);
  console.log("sold", invoice, item, shop.money(what.amount), res.xRefNum, res.xMaskedCardNumber);
  return shop.json(200, {
    ok: true, item, kind: what.kind, label: what.label, amount: shop.money(what.amount),
    refnum: String(res.xRefNum || ""), invoice, card: res.xMaskedCardNumber || "", email, token, days, links,
    downloads: `${shop.SITE}/pdfs.html?t=${encodeURIComponent(token)}`,
  });
};
