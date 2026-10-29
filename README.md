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

Primary domain is thetzeitung.com; ditzeitung.com redirects to it (see `_redirects`).
Forms (subscribe, advertise, contact) are Netlify Forms; notifications go to mk@thetzeitung.com.
The email list form posts to Mailchimp.
