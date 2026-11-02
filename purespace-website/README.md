# PureSpace Cleaning Services - website

A complete website for PureSpace Cleaning Services Ltd: eight public pages, an online quote form with a live guide price,
a contact form, and a password-protected admin area where staff view and manage every enquiry.

Built with Python (Flask) and SQLite. There is no build step, no Node.js and no external service: the fonts, images and
scripts are all served by the site itself.

| | |
|---|---|
| Public pages | Home, Home cleaning, Office cleaning, Prices, About, Contact, Get a quote, Privacy notice |
| Forms | Quote request (live guide price), contact message. Both validate, store to the database and show a confirmation page with a reference number |
| Admin | `/admin` - sign in, search and filter enquiries, change status, add notes, delete on request, download CSV, change password |
| Security | Hashed passwords, CSRF protection, login lockout, form rate limits, spam trap, strict Content Security Policy, no raw IP addresses stored |
| Tests | 48 automated tests, including real-browser tests at desktop, tablet and phone sizes |

---

## 1. Install and run (about 5 minutes)

You need **Python 3.10 or newer**. Check with `python --version` (on some Macs and Linux machines, use `python3`).

```bash
# 1. Get into the project folder
cd purespace-website

# 2. Create a private Python environment for the site
python -m venv .venv
# Windows:          .venv\Scripts\activate
# macOS / Linux:    source .venv/bin/activate

# 3. Install the two packages it needs (Flask and Waitress)
pip install -r requirements.txt

# 4. Create the database
flask --app purespace init-db

# 5. Create the first admin login (you'll be asked for a password)
flask --app purespace create-admin --username owner

# 6. Optional: add 12 example enquiries so the admin area isn't empty
flask --app purespace seed-demo

# 7. Start the site
python run.py
```

Open **http://127.0.0.1:8000** for the website and **http://127.0.0.1:8000/admin** for the admin area.

`python run.py --dev` starts Flask's development server instead, which reloads when you edit files. Use it for local
changes only, never on a live site.

### Admin login

There is **no built-in or default password**. Step 5 creates the login, and the password you choose is stored only as a
scrypt hash. Passwords must be at least 12 characters with upper- and lower-case letters and a number.

To add another member of staff, run step 5 again with a different username. If a password is forgotten, run step 5 with
the same username to set a new one.

`flask --app purespace purge-old` deletes enquiries over 12 months old that never became bookings (see `docs/DEPLOYMENT.md`).

Demo enquiries all have names starting with "DEMO" and `@example.com` emails. Delete them from the admin area (or start
with a fresh database) before launch.

---

## 2. Before launch

The site ships with **sample business details** (a drama-range phone number, an example address, placeholder company
number) and some business claims that only the owner can confirm, such as the insurance amount and the re-clean
guarantee. Nothing on the site is a real review or testimonial, and none have been invented.

Work through [`docs/LAUNCH_CHECKLIST.md`](docs/LAUNCH_CHECKLIST.md). Until `SAMPLE_CONTENT` is set to `False` in
`purespace/content.py`, the admin dashboard shows a reminder banner.

## 3. Where things are

```
purespace/
  content.py        Business details, promises, areas covered - edit this first
  pricing.py        All prices and the guide-price formula (the website and admin both use it)
  public.py         Public pages and the two forms
  admin.py          Admin area
  forms.py          Form validation and error messages
  security.py       CSRF, rate limiting, login checks, security headers
  notify.py         Optional email alerts for new enquiries
  db.py, schema.sql Database and the command-line tools
  templates/        Page templates (Jinja2); admin/ holds the admin pages
  static/           CSS, JavaScript, self-hosted fonts, favicon
tests/              Automated tests
docs/               Deployment, testing, launch checklist, design notes
run.py              Start the site (Waitress)
wsgi.py             Entry point for Gunicorn / PythonAnywhere
```

**Changing prices:** edit `purespace/pricing.py`. The Prices page, the "From £" figures, the live guide price on the
quote form and the price stored with each enquiry all read from that one file, so they always agree.

## 4. Settings

Everything has a sensible default. On a live server, set these as environment variables (full list in `.env.example`):

| Variable | What it does |
|---|---|
| `PURESPACE_SECRET_KEY` | Signs the login cookie. If unset, a random key is created once in `instance/secret_key` |
| `PURESPACE_SECURE_COOKIES=1` | Turn on once the site has HTTPS |
| `PURESPACE_TRUST_PROXY=1` | Turn on when running behind nginx or a hosting proxy |
| `PURESPACE_SMTP_HOST` and friends | Email the office when a new enquiry arrives (off by default) |

## 5. More documentation

- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) - putting the site live (PythonAnywhere or your own server), HTTPS, backups
- [`docs/TESTING.md`](docs/TESTING.md) - how to run the tests and what each one proves
- [`docs/LAUNCH_CHECKLIST.md`](docs/LAUNCH_CHECKLIST.md) - everything to confirm before going live
- [`docs/DESIGN.md`](docs/DESIGN.md) - the brand idea, colours, fonts and how to keep new pages consistent

## 6. Licences

Code: written for PureSpace Cleaning Services Ltd. Fonts: Bricolage Grotesque and Atkinson Hyperlegible, both under the
SIL Open Font Licence (licence files are in `purespace/static/fonts/`). All illustrations were drawn for this project as
SVG; no stock photos or third-party images are used.
