// Shared pieces of the PDF shop: the catalogue (what is for sale, at what price), the Sola
// (Cardknox) charge, the signed "your downloads" token, and the time-limited download links
// to the PDFs in the Cloudflare R2 bucket. Keys live only in the Netlify environment:
//   SOLA_XKEY            the Sola API (transaction) key, server side only
//   SOLA_IFIELDS_KEY     the public iFields key the browser tokenises card numbers with
//   SOLA_GATEWAY_URL     optional, default https://x1.cardknox.com/gatewayjson
//   R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET   the bucket with pdf/<date>.pdf
//   SHOP_SECRET          any long random string: signs the download tokens
const crypto = require("crypto");

const SITE = (process.env.URL || "https://thetzeitung.com").replace(/\/$/, "");
const SOFTWARE = "thetzeitung.com";
const SOFTWARE_VERSION = "1.0";

function ready() {
  return ["SOLA_XKEY", "SOLA_IFIELDS_KEY", "R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "SHOP_SECRET"]
    .every(k => process.env[k]);
}

// ---- the catalogue: shop-catalog.json (prices, editions) and pdfs.json (which PDFs exist) --------
let cache = { at: 0, catalog: null, pdfs: null };
async function catalog() {
  if (Date.now() - cache.at < 5 * 60 * 1000 && cache.catalog) return cache;
  const [c, p] = await Promise.all([
    fetch(`${SITE}/shop-catalog.json`).then(r => r.json()),
    fetch(`${SITE}/pdfs.json`).then(r => r.json()),
  ]);
  cache = { at: Date.now(), catalog: c, pdfs: p };
  return cache;
}

function money(n) { return (Math.round(n * 100) / 100).toFixed(2); }

/** A whole year's price: by how many years back it lies from the newest edition's year. */
function yearPrice(c, hy) {
  const age = (c.current_hy || 0) - Number(hy);
  const tiers = c.year_tiers || [{ max_age: 999, price: c.year }];
  for (const t of tiers) if (age <= t.max_age) return t.price;
  return tiers[tiers.length - 1].price;
}

/** What `item` buys: {kind, dates, amount, description, label}. Throws on an unknown item. */
async function resolve(item) {
  const { catalog: c, pdfs } = await catalog();
  if (/^\d{4}-\d{2}-\d{2}$/.test(item)) {
    if (!pdfs[item] || !c.editions[item]) throw new Error("That edition is not available as a PDF.");
    const ed = c.editions[item];
    return { kind: "issue", dates: [item], amount: c.issue,
             description: `The Tzeitung PDF ${item}`, label: editionLabel(item, ed) };
  }
  const m = /^year:(\d{4})$/.exec(item);
  if (m) {
    const y = m[1]; const yr = c.years[y];
    const dates = Object.keys(pdfs).filter(d => c.editions[d] && String(c.editions[d].hy) === y).sort();
    if (!yr || dates.length < (c.year_min_issues || 1)) throw new Error("That year is not available as a bundle.");
    return { kind: "year", dates, amount: yearPrice(c, y), year: y,
             description: `The Tzeitung PDFs ${yr.label} (${dates.length} editions)`, label: `${yr.label} — ${dates.length} editions` };
  }
  throw new Error("Unknown item.");
}

function editionLabel(date, ed) {
  const parts = [];
  if (ed.parsha) parts.push(ed.parsha);
  if (ed.hdate) parts.push(ed.hdate);
  parts.push(date);
  return parts.join(" · ");
}

// ---- Sola / Cardknox: one sale with the single-use tokens iFields made in the browser -------------
async function charge({ amount, description, invoice, item, cardToken, cvvToken, exp, name, email, zip, street, ip }) {
  const url = process.env.SOLA_GATEWAY_URL || "https://x1.cardknox.com/gatewayjson";
  const body = {
    xKey: process.env.SOLA_XKEY, xVersion: "5.0.0", xSoftwareName: SOFTWARE, xSoftwareVersion: SOFTWARE_VERSION,
    xCommand: "cc:sale", xAmount: money(amount), xCurrency: "USD",
    xCardNum: cardToken, xExp: exp, xName: name, xEmail: email, xZip: zip,
    xInvoice: invoice, xDescription: description, xCustom01: item, xTimeoutSeconds: "60",
  };
  if (cvvToken) body.xCVV = cvvToken;
  if (street) body.xStreet = street;
  if (ip) body.xIP = ip;
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const text = await r.text();
  let res; try { res = JSON.parse(text); } catch (e) { res = Object.fromEntries(new URLSearchParams(text)); }
  return res;   // xResult: A approved, D declined, E error; xError, xRefNum, xAuthAmount, xMaskedCardNumber
}

// ---- the "your downloads" token: item + reference number, signed, good for token_days ------------
function b64url(buf) { return Buffer.from(buf).toString("base64").replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_"); }
function sign(payload) {
  const data = b64url(JSON.stringify(payload));
  const mac = crypto.createHmac("sha256", process.env.SHOP_SECRET).update(data).digest();
  return `${data}.${b64url(mac)}`;
}
function verify(token) {
  const m = /^([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)$/.exec(token || "");
  if (!m) return null;
  const mac = b64url(crypto.createHmac("sha256", process.env.SHOP_SECRET).update(m[1]).digest());
  if (mac.length !== m[2].length || !crypto.timingSafeEqual(Buffer.from(mac), Buffer.from(m[2]))) return null;
  const payload = JSON.parse(Buffer.from(m[1].replace(/-/g, "+").replace(/_/g, "/"), "base64").toString());
  if (!payload.exp || payload.exp * 1000 < Date.now()) return null;
  return payload;
}

// ---- time-limited links to the PDFs (S3 SigV4 query signing against Cloudflare R2) ---------------
function rfc3986(s) { return encodeURIComponent(s).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase()); }
function hmac(key, s) { return crypto.createHmac("sha256", key).update(s).digest(); }
function sha256(s) { return crypto.createHash("sha256").update(s).digest("hex"); }

function presignUrl({ host, path, region, akid, secret, params, seconds, now }) {
  const amzDate = now.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  const day = amzDate.slice(0, 8), service = "s3";
  const scope = `${day}/${region}/${service}/aws4_request`;
  const all = Object.assign({
    "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
    "X-Amz-Credential": `${akid}/${scope}`,
    "X-Amz-Date": amzDate,
    "X-Amz-Expires": String(seconds),
    "X-Amz-SignedHeaders": "host",
  }, params || {});
  const query = Object.keys(all).sort().map(k => `${rfc3986(k)}=${rfc3986(all[k])}`).join("&");
  const canonical = ["GET", path, query, `host:${host}\n`, "host", "UNSIGNED-PAYLOAD"].join("\n");
  const toSign = ["AWS4-HMAC-SHA256", amzDate, scope, sha256(canonical)].join("\n");
  const kSigning = hmac(hmac(hmac(hmac("AWS4" + secret, day), region), service), "aws4_request");
  const signature = crypto.createHmac("sha256", kSigning).update(toSign).digest("hex");
  return `https://${host}${path}?${query}&X-Amz-Signature=${signature}`;
}

function presign(key, filename, seconds, now = new Date()) {
  const bucket = process.env.R2_BUCKET;
  return presignUrl({
    host: `${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    path: `/${bucket}/` + key.split("/").map(rfc3986).join("/"),
    region: "auto", akid: process.env.R2_ACCESS_KEY_ID, secret: process.env.R2_SECRET_ACCESS_KEY,
    params: { "response-content-disposition": `attachment; filename="${filename.replace(/["\\]/g, "")}"` },
    seconds, now,
  });
}

/** Download links for a list of edition dates. */
async function links(dates) {
  const { catalog: c, pdfs } = await catalog();
  const hours = c.link_hours || 24;
  return dates.filter(d => pdfs[d]).map(d => ({
    date: d,
    label: editionLabel(d, c.editions[d] || {}),
    bytes: pdfs[d].bytes || null,
    pages: pdfs[d].pages || null,
    url: presign(`pdf/${d}.pdf`, `Di Tzeitung ${d}.pdf`, hours * 3600),
  }));
}

function json(status, body) {
  return { statusCode: status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" }, body: JSON.stringify(body) };
}

module.exports = { ready, catalog, resolve, charge, sign, verify, presign, presignUrl, links, json, money, yearPrice, SITE };
