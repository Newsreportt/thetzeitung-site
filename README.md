# The Tzeitung — thetzeitung.com

Source for the website. Netlify deploys `main` automatically.

## Weekly update
1. Drop the week's cover PDFs (main section, Yiddishe Tzeit, Chassidishe Tzeit) anywhere and run
   `python3 _build/import_covers.py path/to/*.pdf`
   It reads the date, volume/number and parsha from the PDF text, renders the covers into
   `covers/archive/` (and small copies into `covers/wall/` for the drifting background) and records
   the edition in `_build/editions.json`.
2. Run `python3 _build/build.py` to regenerate the pages. The newest edition becomes "This week's
   edition" on the home page; the Archives page lists every edition, newest first. The "in the
   stores" poster beside the list of places (`ads/in-stores.jpg`) is rendered again with the newest
   edition's three covers (`_build/stores_ad.py`: the background and the three page positions were
   lifted once from the office's poster into `_build/stores-ad/`).
3. Commit and push.

When the week's covers come as pictures instead of PDFs:
`python3 _build/import_images.py --week 2026-11-06 a=main.jpg b=yiddishe.jpg c=chassidishe.jpg`
(a = the main section, b = Yiddishe Tzeit, c = Chassidishe Tzeit, d/t/k = the yom tov supplements), then build as usual.

## Older covers
The covers back to Elul 5778 came from the JPEGs in the Mailchimp content studio
(`python3 _build/import_images.py manifest.tsv images/ --decisions decisions.tsv`): the edition date
and section are read from the Mailchimp file names, the volume and number off the main cover with
OCR, and the search text of each cover with OCR as well. Sections: a = the main section,
b = Yiddishe Tzeit, c = Chassidishe Tzeit, d = Yom Tov Tzeit, t = Torah Tzeit, k = Kehila Tzeit.
Those JPEGs carried an unmanaged print green (bright, yellowish); `_build/regreen.py` remaps it to the
masthead green of the PDF renders and runs as part of the image import.

The years תשס״ה–תשע״ח came from the office's Google Drive (the "News Report old" folders, Vol 18–32).
A GitHub Actions workflow on the `year-fetch` branch crawls the shared folders through Drive's
embedded folder view, picks the cover file of every issue (page 1 / Section A for the main paper,
Section B/C/D for the supplements), renders each first page and publishes the renders to the
`year-raw` branch. Google throttles anonymous downloads after a couple of gigabytes, so the workflow
runs in rounds (one an hour while throttled); meanwhile it keeps Drive's own first-page thumbnails
(`<tag>.thumb.jpg`, 1024px) for the issues still missing. Then, on a clone of `year-raw`:
`python3 _build/import_pages.py raw/out --no-wall` (the `--no-wall` keeps these covers out of the
home page background). The importer reads each page's date and section from its text layer (OCR of
the masthead for thumbnails), places every issue on its volume's weekly grid so a misread digit or
a misfiled copy cannot land on the wrong week, lets a real page replace a thumbnail imported
earlier, and honours `raw/out/manual.json` (kept as `_build/drive-manual.json`: `dates` and
`section` settled by eye, `rotate` for yom tov spreads, `skip` for stray files). A yom tov edition's second Yiddishe Tzeit section is labelled through
`labels` in `editions.json`.

## The PDF shop (back issues as PDF)
Any edition can be bought as a PDF of the whole paper (`pdfs.html`; the buttons appear in the
Archives). Prices are in `_build/shop.json` (`issue_tiers`: per edition, by how many years back its Hebrew year lies; a year bundle appears only if `year_tiers` is set and a year has at least
`year_min_issues` PDFs). The pieces:
- `pdfs.json` (site root) says which editions exist as PDFs; the PDFs themselves sit in a
  Cloudflare R2 bucket as `pdf/<date>.pdf`. `.github/workflows/pdf-archive.yml` keeps both up:
  it walks the office's Google Drive (`_pdf/job.json`: the "News Report old" root, the Vol N /
  NN issue folders), merges each issue's section or page PDFs into one (`_pdf/archive.py`, with
  the file list in `_pdf/manifest.json`), uploads it and commits `pdfs.json`. It runs every
  Monday night for new issues and can be run by hand (Actions → PDF archive → Run workflow).
- `shop.js` puts the buttons into the archive, opens the checkout (the card number and CVV are
  Sola iFields iframes, so card data never touches the site) and shows the download links;
  `pdfs.html?t=<token>` shows a buyer's links again for `token_days`.
- `netlify/functions/`: `shop-config` (is the shop on, the public iFields key), `buy` (one Sola
  `cc:sale` with the iFields tokens, then signed download links), `downloads` (fresh links for
  a token). `build.py` writes `shop-catalog.json` (prices and every edition's label and year) for
  them and the browser.
Nothing shows on the site until these environment variables are set in Netlify (Site
configuration → Environment variables): `SOLA_XKEY` (the Sola API key, server side only),
`SOLA_IFIELDS_KEY` (the public iFields key), `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`,
`R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `SHOP_SECRET` (any long random string). The archive
workflow needs the R2 values and `GDRIVE_SA_JSON` (a Google service-account key whose email the
Drive folder is shared with) as repository secrets (Settings → Secrets and variables → Actions).
Optional: `SOLA_GATEWAY_URL`, `SOLA_IFIELDS_VERSION`.

Primary domain is thetzeitung.com; ditzeitung.com redirects to it (see `_redirects`).
Forms (subscribe, advertise, contact) are Netlify Forms; notifications go to mk@thetzeitung.com.
The email list form posts to Mailchimp.
