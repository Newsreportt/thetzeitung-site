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

  // One purchase may be handed fresh links only so many times: a link passed around runs out.
  const { catalog: c } = await shop.catalog();
  const cap = c.max_downloads || 40;
  const ip = (event.headers["x-nf-client-connection-ip"] || event.headers["client-ip"] || "").split(",")[0].trim();
  let rec = null;
  try { rec = p.n ? await shop.getJson(`receipts/${p.n}.json`) : null; } catch (ex) { console.error("receipt unreadable", p.n, ex.message); }
  if (rec) {
    const handed = (rec.handed_out || 0) + 1;
    if (handed > cap) {
      console.log("cap reached", p.n, handed);
      return shop.json(429, { ok: false, error: "These downloads have been fetched many times already. Call the office at 718-851-6607 with your receipt number and we will help." });
    }
    rec.handed_out = handed; rec.last_at = new Date().toISOString();
    rec.seen_ips = Array.from(new Set([...(rec.seen_ips || []), ip].filter(Boolean))).slice(-20);
    try { await shop.putJson(`receipts/${p.n}.json`, rec); } catch (ex) { console.error("receipt not updated", p.n, ex.message); }
  }
  const links = await shop.links(what.dates);
  const hours = c.link_hours || 6;
  return shop.json(200, { ok: true, item: p.i, kind: what.kind, label: what.label, refnum: p.r, invoice: p.n,
                          until: p.exp, hours, left: rec ? Math.max(0, cap - rec.handed_out) : null, links });
};
