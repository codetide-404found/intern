# Intern Accra

A free internship board for Accra students, built with Python and Django.
Django serves the public pages and the admin site, so there is one project and one language.

| What | Where |
|---|---|
| Public site (students) | `/` |
| One internship | `/internship/<id>/<name>/` (each has its own shareable link) |
| Admin (you, needs a login) | `/manage/` |

## Run it on your computer

You need Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # your admin username and password
python manage.py seed_samples      # optional: 6 sample listings so the site is not empty
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the site and http://127.0.0.1:8000/manage/ for the admin.

## Adding internships

1. Go to `/manage/` and log in.
2. Open **Internships** and choose **Add internship**.
3. Fill in the form. The fields follow the questions you ask companies during visits.
4. Save. The listing is on the public site straight away.

Things to know:

- **WhatsApp and email are both optional. Fill in either one, or both.** Each one you fill in becomes an Apply button on the listing, and the home page card says "Apply by WhatsApp or email". The email button opens the student's mail app with a ready-made subject and message. Because many computers have no mail app, the page also offers "Open in Gmail" and "Copy address". Leave one empty and its button is hidden. If a company takes neither, write instructions under "How to apply" (for example "Walk in with your CV").
- **Programmes** are tags students filter by. Add new ones from the listing form (the green plus) or under **Programmes**.
- **Deadlines hide listings automatically.** After the deadline date the listing disappears from the public pages. It stays in the admin, filtered as "Expired".
- **Hide without deleting:** untick "Published", or select listings in the list and use the "Hide selected listings" action.
- **Contact person (private)** and **Confirmed with company on** are your own records. The contact person is never shown to students.
- **Remove the samples** with `python manage.py seed_samples --clear`, or filter by "sample listing" in the admin and delete them.

## See how many students use the site

Log in to `/manage/` and open **Site stats** in the sidebar. It shows:

- visitors and page views for today, the last 7 days, the last 30 days and all time
- a day-by-day chart for the last 14 days
- your most viewed internships
- which programmes and areas students filter by
- what students search for, and the **searches that found nothing** (good targets for your next company visits)

How it counts, and what it does not store:

- Students do not need an account, and no cookies are used.
- Each visit saves the date, the page, any filter or search used, and a short code that stands in for the visitor.
  The code is a one-way hash of the device and network plus the date and your secret key, so it changes every day.
  No IP address, name, email or phone number is stored.
- A "visit" is one visitor on one day. The same student returning tomorrow counts as a new visit,
  and one student using two phones counts twice. Treat the numbers as good estimates.
- Search engines, link previews (for example WhatsApp), scripts, anyone logged in to the admin (you),
  and visitors who send "Do Not Track" are not counted.
- Search words are saved in lower case so you can see what students want. Students could in theory type
  personal details into the search box, so keep the stats page private (it is behind your admin login).

To keep the database small, delete visit records older than a year:

```bash
python manage.py prune_stats --days 400
```

## Put it online

Set these environment variables on the host:

| Variable | Value |
|---|---|
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | a long random string, at least 40 characters (the site refuses to start in production without it) |
| `DJANGO_ALLOWED_HOSTS` | your domain, e.g. `internaccra.pythonanywhere.com` (`*` is refused) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | your full address, e.g. `https://internaccra.pythonanywhere.com` |
| `CONTACT_WHATSAPP` | your number for companies, digits only, e.g. `233244000000` (optional) |
| `CONTACT_EMAIL` | your email for companies (optional) |
| `DJANGO_DB_PATH` | optional: full path for the SQLite file if you want it outside the project folder |
| `DJANGO_SSL_REDIRECT` | `0` only if you get a redirect loop behind your host's proxy |
| `DJANGO_ADMIN_URL` | optional but recommended: a private admin address only you know, e.g. `desk-7f3k` (then the admin is at `/desk-7f3k/`) |
| `DJANGO_TRUSTED_PROXIES` | `1` (default) on hosts that put a proxy in front of your site, which is most of them. `0` only if visitors reach the site directly |
| `DJANGO_HSTS_SECONDS` | starts at `3600`. Once HTTPS works everywhere, raise it to `31536000` (one year) |
| `DJANGO_HSTS_SUBDOMAINS` | `1` only on your own domain, and only if every subdomain uses HTTPS. Leave unset on `pythonanywhere.com` addresses |
| `DJANGO_CACHE_DIR` | optional: folder where failed-login counts are kept (default `.cache` in the project) |

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Then, on the server, run once and again after each update:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Run `python manage.py createsuperuser` once to create your admin login.

### Option A: PythonAnywhere (simplest to set up)

What to know before you choose a plan (from PythonAnywhere's own pages, checked October 2026; plans change, so confirm on their site):

- A **free account** gets one web app with one worker, 512 MiB of disk, and no direct support. The web app **expires after one month** unless you extend it, so a free account is fine for testing but not for a real launch: if you forget, the site goes down.
- For a real launch, use a paid plan. Their blog says the base paid tier is $10 a month. A paid plan is also what you need if you want your own domain name.
- Your files and SQLite database stay on the server between restarts, which is why it suits this project.

Sources: [Free account features](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/) and [Changes on free accounts](https://blog.pythonanywhere.com/221/).


1. Create an account and open a Bash console. Upload or `git clone` this folder.
2. Make a virtualenv and run the install commands above.
3. On the **Web** tab, add a new web app, choose **Manual configuration** and your Python version.
4. Set the source folder and virtualenv, and edit the WSGI file so it contains:
   ```python
   import os, sys
   sys.path.insert(0, '/home/YOURUSERNAME/internaccra')
   os.environ['DJANGO_DEBUG'] = '0'
   os.environ['DJANGO_SECRET_KEY'] = 'your-long-random-key'
   os.environ['DJANGO_ALLOWED_HOSTS'] = 'YOURUSERNAME.pythonanywhere.com'
   os.environ['DJANGO_CSRF_TRUSTED_ORIGINS'] = 'https://YOURUSERNAME.pythonanywhere.com'
   os.environ['DJANGO_ADMIN_URL'] = 'choose-a-private-word'
   from config.wsgi import application
   ```
5. Reload the web app. The SQLite database file stays on the server between restarts.

### Option B: Render, Railway, Fly.io or a VPS

Use `pip install -r requirements.txt` as the build command (plus `python manage.py collectstatic --noinput`
and `python manage.py migrate`) and `gunicorn config.wsgi` as the start command.

Important: some hosts wipe the disk on every deploy or restart. SQLite then loses your listings.
On those hosts, attach a persistent disk and point `DJANGO_DB_PATH` at it, or switch the database to PostgreSQL
(change `DATABASES` in `config/settings.py` and add `psycopg[binary]` to `requirements.txt`).

## Security

What is already built in:

- **The admin needs a login, and you can hide it.** Set `DJANGO_ADMIN_URL` to a private word so strangers cannot find the login page. Search engines are told not to index it.
- **Login lockout.** After 5 failed attempts for one username from one address, login is paused for 15 minutes, even with the right password. Failures are written to your server's error log.
- **Strong passwords only.** Admin passwords must be at least 12 characters and not common or all numbers. A phrase of four or five unrelated words is easy to remember and hard to guess.
- **Short sessions.** Admin logins expire after 8 hours.
- **A strict content policy on public pages** blocks scripts and styles that did not come from your own site, which stops most cross-site scripting. Pages also refuse to be shown inside other sites (clickjacking), and camera, microphone and location are switched off.
- **HTTPS everywhere in production**: secure cookies, automatic redirect to HTTPS, and HSTS.
- **Safe by default in the code.** Search text goes into the database as data, never as SQL. Everything typed into a listing is escaped before it is shown. The admin forms are protected against forged requests. Students cannot upload anything. The private "contact person" field is never shown or searchable on the public site.
- **The site refuses to start with unsafe settings**: no secret key, a short one, or `*` as the allowed host.
- Dependencies were checked against a public vulnerability database and none were known to be affected.

What is still up to you (no code can do this part):

- Use a long, unique password for the admin, and for your hosting account and email. Most real break-ins start there.
- Keep `DJANGO_SECRET_KEY` private. Never put it in a repository. If it leaks, change it.
- Keep `db.sqlite3` out of your repository (it is already in `.gitignore`) and back it up regularly.
- Update Django and the other packages every few months: `pip install -U -r requirements.txt`, then run the tests.
- Create a separate admin account for anyone who helps you, and delete it when they stop.
- Check `python manage.py check --deploy` on the server. One notice about `SECURE_HSTS_INCLUDE_SUBDOMAINS` is expected and deliberate; see `DJANGO_HSTS_SUBDOMAINS` above.

Two-factor login (a code from a phone app) is the next big step for the admin. It is not included yet. No website can promise to be unhackable, but with the points above a stranger cannot guess their way in, and a guessed or leaked password is the main risk left.

## What students see when something goes wrong

Missing pages, expired links and server errors show a short friendly page with a button back to the open internships, never a blank screen or technical error. These pages are plain files that do not depend on the database, so they work even if the rest of the site is broken.

When you open the admin, a **Needs attention** box tells you if only sample listings are live, if nothing is live, or which listings close within 7 days.

## Back up your data

Copy `db.sqlite3` somewhere safe regularly, or export listings with
`python manage.py dumpdata listings --indent 2 > backup.json` and restore them with `loaddata`.

## Project layout

```
config/            settings and URL routing
listings/
  models.py        Internship and Programme
  admin.py         the admin screens
  views.py         list page (search, filters, sorting) and detail page
  stats.py         visit counting and the numbers on the Site stats page
  security.py      login lockout and security headers
  sites.py         the admin site (Needs attention box, lockout)
  templates/       HTML pages
  static/          CSS and a few lines of JavaScript
  tests.py         automated tests (python manage.py test)
manage.py
```

## Tests

```bash
python manage.py test
```
