// GET /.netlify/functions/downloads?t=<token> — fresh download links for a purchase, as long as
// its token (handed out by buy.js, shown on pdfs.html) has not run out.
const shop = require("./lib/shop.js");

exports.handler = async (event) => {
  if (!shop.ready()) return shop.json(503, { ok: false, error: "The PDF shop is not switched on yet." });
  const t = (event.queryStringParameters || {}).t || "";
  const p = shop.verify(t);
  if (!p) return shop.json(403, { ok: false, error: "This link is not valid any more. Call the office with your receipt and we will send the PDF." });
  let what;
  try { what = await shop.resolve(p.i); } catch (e) { return shop.json(404, { ok: false, error: e.message }); }
  const links = await shop.links(what.dates);
  return shop.json(200, { ok: true, item: p.i, kind: what.kind, label: what.label, refnum: p.r, invoice: p.n, until: p.exp, links });
};
