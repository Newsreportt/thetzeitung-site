// What stands between the till and somebody who means it harm.
//
// The danger at a card form is not that a thief buys a newspaper: it is that a stolen list of card
// numbers is tried out against it, a few hundred at a time, to see which still work. That shows up
// as many attempts from one place, or many declines in a row, and both are counted here. The count
// is kept in the bucket, one small record per visitor, so it holds across the many short-lived
// servers a request may land on.
//
// Nothing here identifies a reader: the address is kept only as a hash, with a secret the attacker
// does not have, and the records fall out of use on their own.
const crypto = require("crypto");
const shop = require("./shop.js");

const LIMITS = {
  tries_hour: 6,          // attempts to pay from one address in an hour
  tries_day: 15,          // and in a day
  declines_hour: 3,       // declined cards in an hour, after which that address waits
  cool_minutes: 45,       // how long it then waits
  min_seconds: 3,         // a form filled faster than this was not filled by a person
};

function tag(ip) {
  const salt = process.env.SHOP_SECRET || process.env.R2_SECRET_ACCESS_KEY || "tz";
  return crypto.createHmac("sha256", salt).update(String(ip || "none")).digest("hex").slice(0, 24);
}

function fresh(list, seconds, now) {
  return (list || []).filter(t => now - t < seconds * 1000);
}

/** May this address try to pay? Returns {ok} or {ok:false, error, status}. */
async function check(ip) {
  let rec = null;
  try { rec = await shop.getJson(`rate/${tag(ip)}.json`); } catch (ex) { return { ok: true, blind: true }; }
  const now = Date.now();
  rec = rec || { tries: [], declines: [] };
  const tries = fresh(rec.tries, 86400, now), declines = fresh(rec.declines, 3600, now);
  const hour = tries.filter(t => now - t < 3600 * 1000);

  if (declines.length >= LIMITS.declines_hour) {
    const until = Math.max(...declines) + LIMITS.cool_minutes * 60 * 1000;
    if (now < until) return { ok: false, status: 429,
      error: `Too many cards have been declined here. Please wait ${Math.ceil((until - now) / 60000)} minutes, or call the office, 718-851-6607.` };
  }
  if (hour.length >= LIMITS.tries_hour) return { ok: false, status: 429,
    error: "Too many attempts from here in the last hour. Please try later, or call the office, 718-851-6607." };
  if (tries.length >= LIMITS.tries_day) return { ok: false, status: 429,
    error: "Too many attempts from here today. Please call the office, 718-851-6607." };
  return { ok: true, rec: { tries, declines } };
}

/** Write down what happened, so the next attempt knows about it. */
async function note(ip, rec, what) {
  const now = Date.now();
  const next = {
    tries: fresh(rec && rec.tries, 86400, now).concat([now]).slice(-40),
    declines: fresh(rec && rec.declines, 3600, now).concat(what === "declined" ? [now] : []).slice(-20),
    last: new Date(now).toISOString(),
  };
  try { await shop.putJson(`rate/${tag(ip)}.json`, next); } catch (ex) { /* a count is not worth a sale */ }
}

/** The signs of a machine rather than a reader: a field no one can see, filled in; or a form
 *  sent back the moment it was opened. */
function looksAutomated(body) {
  if (typeof body.company === "string" && body.company.trim() !== "") return true;
  const opened = Number(body.opened);
  if (!opened || !isFinite(opened)) return false;
  return (Date.now() - opened) / 1000 < LIMITS.min_seconds;
}

module.exports = { check, note, looksAutomated, LIMITS };
