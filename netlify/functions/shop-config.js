// GET /.netlify/functions/shop-config — what the browser needs to open the checkout: whether the
// shop is switched on (every key set in Netlify) and the public iFields key.
const shop = require("./lib/shop.js");
const mail = require("./lib/mail.js");

exports.handler = async () => {
  const on = shop.ready();
  const out = {
    enabled: on,
    ifieldsKey: on ? process.env.SOLA_IFIELDS_KEY : null,
    ifieldsVersion: process.env.SOLA_IFIELDS_VERSION || "2.15.2309.2601",
  };
  // while the shop is off, say which settings are still missing — the names only, never a value
  if (!on) out.missing = shop.missing();
  if (!mail.ready()) out.mail = false;   // the letters cannot go out yet
  return shop.json(200, out);
};
