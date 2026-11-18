// The one letter this site sends: the buyer's receipt, with a link to the PDF they paid for.
// It goes out through Resend (RESEND_API_KEY, MAIL_FROM); if those are not set, or Resend is
// having a bad day, the sale still stands — the links are in the open page — and the office is
// told in the log which letter did not go out.
const SITE_NAME = "The Tzeitung";

function ready() { return Boolean(process.env.RESEND_API_KEY && process.env.MAIL_FROM); }

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

/** The receipt letter, in the plain two-column look of a paper's own stationery. */
function receipt({ label, amount, refnum, card, links, hours }) {
  const rows = links.map(l => `
      <tr><td style="padding:10px 0;border-bottom:1px solid #e7e1d5;">
        <a href="${esc(l.url)}" style="display:inline-block;background:#c8a24a;color:#1d2d20;text-decoration:none;
           font:600 15px/1 Helvetica,Arial,sans-serif;padding:13px 22px;border-radius:4px;">Download the PDF</a>
        <div style="font:13px/1.5 Helvetica,Arial,sans-serif;color:#5d5a52;padding-top:7px;">
          <bdi>${esc(l.label)}</bdi>${l.pages ? ` · ${l.pages} pages` : ""}${l.bytes ? ` · ${Math.round(l.bytes / 1e6)} MB` : ""}
        </div>
      </td></tr>`).join("");

  const html = `<!doctype html><html><body style="margin:0;background:#f4efe4;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4efe4;padding:28px 14px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:540px;background:#fffdf7;border:1px solid #e7e1d5;border-radius:6px;">
        <tr><td style="background:#14442a;padding:18px 24px;font:600 17px/1.2 Georgia,serif;color:#f4efe4;">${SITE_NAME}</td></tr>
        <tr><td style="padding:24px;">
          <p style="margin:0 0 6px;font:600 19px/1.3 Georgia,serif;color:#1d2d20;">Your PDF is ready</p>
          <p style="margin:0 0 18px;font:14px/1.6 Helvetica,Arial,sans-serif;color:#5d5a52;">
            <bdi>${esc(label)}</bdi><br>$${esc(amount)} charged to the card ending ${esc(String(card || "").slice(-4))} · ref. ${esc(refnum)}
          </p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">${rows}</table>
          <p style="margin:18px 0 0;font:13px/1.6 Helvetica,Arial,sans-serif;color:#5d5a52;">
            The link works for ${hours} hours. The PDF is for your own use; it may not be reprinted or posted.
            Anything else — call the office, 718-851-6607.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table></body></html>`;

  const text = [
    `${SITE_NAME} — your PDF is ready`, "",
    label, `$${amount} charged to the card ending ${String(card || "").slice(-4)} · ref. ${refnum}`, "",
    ...links.map(l => `${l.label}\n${l.url}`), "",
    `The link works for ${hours} hours. The PDF is for your own use; it may not be reprinted or posted.`,
    "Anything else — call the office, 718-851-6607.",
  ].join("\n");

  return { html, text };
}

async function send({ to, subject, html, text }) {
  if (!ready()) throw new Error("no mail key");
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: process.env.MAIL_FROM, to: [to], subject, html, text,
                           reply_to: process.env.MAIL_REPLY_TO || undefined }),
  });
  if (!r.ok) throw new Error(`resend ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return r.json();
}

module.exports = { ready, receipt, send, SITE_NAME };
