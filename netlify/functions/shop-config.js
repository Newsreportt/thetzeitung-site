// GET /.netlify/functions/shop-config — what the browser needs to open the checkout: whether the
// shop is switched on (every key set in Netlify) and the public iFields key.
const shop = require("./lib/shop.js");

exports.handler = async () => {
  const on = shop.ready();
  return shop.json(200, {
    enabled: on,
    ifieldsKey: on ? process.env.SOLA_IFIELDS_KEY : null,
    ifieldsVersion: process.env.SOLA_IFIELDS_VERSION || "2.15.2309.2601",
  });
};
