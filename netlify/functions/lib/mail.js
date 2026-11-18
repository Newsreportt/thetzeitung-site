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

/** The office's own word that something was sold, with everything needed to answer a reader
 *  who calls about it. */
function sale({ invoice, label, kind, dates, amount, refnum, card, name, email, when, emailed }) {
  const rows = [
    ["What", label],
    ["Amount", "$" + amount],
    ["Buyer", name],
    ["Email", email],
    ["Card", card],
    ["Sola ref.", refnum],
    ["Invoice", invoice],
    ["When", when],
    ["Letter to the buyer", emailed ? "sent" : "NOT SENT — the reader has no link"],
  ];
  const list = kind === "basket" || (dates || []).length > 1
    ? `<p style="margin:14px 0 0;font:13px/1.7 Helvetica,Arial,sans-serif;color:#5d5a52;">${dates.join("<br>")}</p>` : "";
  const html = `<!doctype html><html><body style="margin:0;background:#f4efe4;padding:24px 14px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#fffdf7;border:1px solid #e7e1d5;border-radius:6px;">
        <tr><td style="background:#14442a;padding:16px 22px;font:600 15px/1.2 Georgia,serif;color:#f4efe4;">A PDF was sold</td></tr>
        <tr><td style="padding:20px 22px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font:14px/1.6 Helvetica,Arial,sans-serif;color:#1d2d20;">
            ${rows.map(([k, v]) => `<tr><td style="padding:5px 0;color:#5d5a52;width:150px;">${esc(k)}</td><td style="padding:5px 0;"><bdi>${esc(v)}</bdi></td></tr>`).join("")}
          </table>${list}
        </td></tr>
      </table>
    </td></tr></table></body></html>`;
  const text = rows.map(([k, v]) => `${k}: ${v}`).join("\n") + (list ? "\n\n" + dates.join("\n") : "");
  return { html, text };
}

async function send({ to, subject, html, text, replyTo }) {
  if (!ready()) throw new Error("no mail key");
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: process.env.MAIL_FROM, to: [to], subject, html, text,
                           reply_to: replyTo || process.env.MAIL_REPLY_TO || undefined }),
  });
  if (!r.ok) throw new Error(`resend ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return r.json();
}

const OFFICE = process.env.MAIL_OFFICE || "mk@thetzeitung.com";

module.exports = { ready, receipt, sale, send, SITE_NAME, OFFICE };
