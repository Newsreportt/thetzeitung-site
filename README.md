# The Tzeitung — thetzeitung.com

Source for the website. Netlify deploys `main` automatically.

## Weekly update
1. Drop the week's cover PDFs (main section, Yiddishe Tzeit, Chassidishe Tzeit) anywhere and run
   `python3 _build/import_covers.py path/to/*.pdf`
   It reads the date, volume/number and parsha from the PDF text, renders the covers into
   `covers/archive/` (and small copies into `covers/wall/` for the drifting background) and records
   the edition in `_build/editions.json`.
2. Run `python3 _build/build.py` to regenerate the pages. The newest edition becomes "This week's
   edition" on the home page; the Archives page lists every edition, newest first.
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
earlier, and honours `raw/out/manual.json` (`dates` read by eye, `rotate` for yom tov spreads,
`skip` for stray files). A yom tov edition's second Yiddishe Tzeit section is labelled through
`labels` in `editions.json`.

Primary domain is thetzeitung.com; ditzeitung.com redirects to it (see `_redirects`).
Forms (subscribe, advertise, contact) are Netlify Forms; notifications go to mk@thetzeitung.com.
The email list form posts to Mailchimp.
