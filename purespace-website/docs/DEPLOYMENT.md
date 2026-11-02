# Deploying the website

The site is a standard Python web application with an SQLite database file. Any host that can run Python 3.10+ works.
Three routes are described: PythonAnywhere (easiest, about £5/month) and your own Linux server.

> **What has and hasn't been verified.** The application, database, forms and admin area were tested with Flask's own
> server and real Chromium (see `TESTING.md`). The Waitress and Gunicorn servers named below are standard, widely used
> production servers for Flask, but they could not be downloaded in the environment where the site was built, so
> the exact commands below have not been run end to end there. Test on your chosen host before announcing the site.

## Option A - PythonAnywhere (simplest)

1. Create an account (the "Hacker" plan or above is needed for a custom domain).
2. Open a **Bash console** and upload or clone the project into your home folder, for example `~/purespace-website`.
3. Create a virtual environment and install:
   ```bash
   cd ~/purespace-website
   python3.12 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   flask --app purespace init-db
   flask --app purespace create-admin --username owner
   ```
4. **Web** tab → *Add a new web app* → *Manual configuration* → the same Python version.
5. Set **Virtualenv** to `/home/<you>/purespace-website/.venv`.
6. Edit the **WSGI configuration file** so it contains only:
   ```python
   import os, sys
   path = "/home/<you>/purespace-website"
   sys.path.insert(0, path)
   os.environ["PURESPACE_SECURE_COOKIES"] = "1"
   os.environ["PURESPACE_TRUST_PROXY"] = "1"
   from wsgi import app as application
   ```
7. **Static files**: URL `/static/` → directory `/home/<you>/purespace-website/purespace/static`
8. Turn on **Force HTTPS**, then **Reload**.

## Option B - your own Ubuntu server (nginx + Gunicorn)

```bash
sudo apt install python3-venv nginx
sudo useradd --system --create-home --home-dir /srv/purespace purespace
sudo -u purespace -i
git clone <your copy> app && cd app        # or upload the zip
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt gunicorn
flask --app purespace init-db
flask --app purespace create-admin --username owner
exit
```

`/etc/systemd/system/purespace.service`:

```ini
[Unit]
Description=PureSpace website
After=network.target

[Service]
User=purespace
WorkingDirectory=/srv/purespace/app
Environment=PURESPACE_SECURE_COOKIES=1
Environment=PURESPACE_TRUST_PROXY=1
ExecStart=/srv/purespace/app/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/nginx/sites-available/purespace`:

```nginx
server {
    server_name purespace-cleaning.co.uk www.purespace-cleaning.co.uk;
    client_max_body_size 100k;

    location /static/ {
        alias /srv/purespace/app/purespace/static/;
        expires 7d;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/purespace /etc/nginx/sites-enabled/
sudo systemctl daemon-reload && sudo systemctl enable --now purespace
sudo nginx -t && sudo systemctl reload nginx
sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx   # free HTTPS certificate
```

## Option C - Windows server or a small office PC

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
flask --app purespace init-db
flask --app purespace create-admin --username owner
python run.py --host 0.0.0.0 --port 8000
```

This uses Waitress, which runs on Windows. Put it behind IIS or a hosting provider's HTTPS proxy before exposing it to
the internet.

## Email alerts (optional)

Set `PURESPACE_SMTP_HOST`, `PURESPACE_SMTP_PORT`, `PURESPACE_SMTP_USER`, `PURESPACE_SMTP_PASSWORD`,
`PURESPACE_MAIL_FROM` and `PURESPACE_NOTIFY_EMAIL`. Any SMTP service works (your email provider, Microsoft 365, Google
Workspace with an app password, Brevo, Postmark...). If sending fails, the enquiry is **still saved** and visible in the
admin area; the failure is written to the server log. `PURESPACE_SEND_CUSTOMER_CONFIRMATION=1` also emails the customer
a copy of their request.

## Backups

All enquiries are in one file: `instance/purespace.sqlite3` (or wherever `PURESPACE_DATABASE` points). Back it up
daily with SQLite's safe online backup, which works while the site is running:

```bash
# crontab -e   (as the purespace user)
15 2 * * * sqlite3 /srv/purespace/app/instance/purespace.sqlite3 ".backup '/srv/purespace/backups/purespace-$(date +\%a).sqlite3'"
```

This keeps one copy per weekday. Copy the backups off the server too (your hosting provider's snapshots, or a cloud drive).
**The backups contain customer personal data** - store them securely.

## Deleting old enquiries (privacy notice promise)

The privacy notice says enquiries that never become bookings are deleted within 12 months. This command does it:

```bash
flask --app purespace purge-old            # asks before deleting
flask --app purespace purge-old --yes      # for a scheduled job
```

Schedule it monthly, e.g. `0 3 1 * * cd /srv/purespace/app && .venv/bin/flask --app purespace purge-old --yes`
(on PythonAnywhere, add it under the *Tasks* tab). Enquiries marked *Booked* are kept, since they are customer records.

## Updating the site

Replace the code files, keep the `instance/` folder (database and secret key), then restart:
`sudo systemctl restart purespace` (or *Reload* on PythonAnywhere). The database tables are created automatically on
start-up if missing; existing data is never touched.

## Capacity

SQLite comfortably handles a small business's enquiry volume (thousands of enquiries a day would still be fine). If the
site is ever moved to several servers at once, it would need a shared database such as PostgreSQL instead.
