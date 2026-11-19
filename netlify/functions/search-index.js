// GET /.netlify/functions/search-index?s=<two letters>  — one slice of the archive's word index,
// or ?s=meta for the list of editions. The index holds words and page numbers only, never a line
// of an article; it is cached hard, because it changes once a week at most.
const shop = require("./lib/shop.js");

const SHARD = /^[א-תa-z0-9]{1,2}$/;

exports.handler = async (event) => {
  if (!shop.bucketReady()) return shop.json(503, { ok: false, error: "The archive search is not switched on yet." });
  const s = ((event.queryStringParameters || {}).s || "").trim();
  const key = s === "meta" ? "idx/meta.json" : SHARD.test(s) ? `idx/w/${s}.json` : null;
  if (!key) return shop.json(400, { ok: false, error: "Ask for 'meta' or for one or two letters." });
  let body;
  try {
    body = await shop.getJson(key);
  } catch (ex) {
    console.error("index", key, ex.message);
    return shop.json(502, { ok: false, error: "The index could not be read." });
  }
  // nothing to cache about an index that is not there yet: the day it arrives, the old answer
  // must not still be standing in front of it
  if (body === null) return { statusCode: 200, headers: head(false), body: "{}" };
  return { statusCode: 200, headers: head(true), body: JSON.stringify(body) };
};

function head(found) {
  return {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": found ? "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800" : "no-store",
    "X-Robots-Tag": "noindex",
  };
}
