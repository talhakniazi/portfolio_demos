# Testing

## Running the tests

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium     # one-off, downloads the test browser (~150 MB)
python -m pytest                           # all 48 tests, about one minute
python -m pytest --ignore=tests/test_browser.py   # the 41 fast tests only, about 10 seconds
SCREENSHOTS=1 python -m pytest tests/test_browser.py   # also saves screenshots to test-results/screenshots/
```

(On Windows PowerShell: `$env:SCREENSHOTS=1; python -m pytest tests/test_browser.py`.)

Every test uses its own temporary database, so running the tests never touches real enquiries. If Playwright isn't
installed, the browser tests are skipped rather than failing.

## What is tested

Mapped to the acceptance criteria in the brief:

| Acceptance criterion | Tests |
|---|---|
| Every navigation link works | `test_crawl_all_internal_links_and_assets` follows every link, stylesheet, script and font from every page; `test_main_menu_links_every_section`; `test_nav_links_work_on_desktop` clicks each menu item in Chromium; `test_mobile_menu` opens the phone menu, closes it with Escape, and navigates from it |
| Forms submit successfully and store data | `test_quote_success_is_stored_and_confirmed`, `test_commercial_quote`, `test_contact_success_and_errors`, and `test_quote_journey_in_browser`, which fills the quote form on a phone-sized screen in Chromium, checks the live price, submits, and reads the reference number from the confirmation page |
| Validation and error messages | `test_quote_validation_errors_are_shown_and_nothing_saved` (5 field errors, typed answers kept, nothing saved), `test_date_rules`, `test_whatsapp_needs_phone`, `test_out_of_range_numbers_rejected`; in the browser, the error summary appears and receives keyboard focus |
| Admin can view enquiries | `test_dashboard_lists_and_filters`, `test_status_notes_delete`, `test_csv_export_escapes_formulas`, `test_change_password`, and `test_admin_in_browser` (sign in, open the browser-submitted enquiry, change status, add a note, sign out) |
| Works on desktop and mobile | `test_pages_render_cleanly` loads all 8 pages at 1440×900, 820×1180 and 390×844 and fails on any broken image, sideways scrolling, missing font, JavaScript error, console error, Content Security Policy violation, or failed request; the admin list is checked at phone width too |
| No broken images or missing pages | as above, plus `test_every_page_loads` (one `<h1>`, title, description, language on each page) and `test_404_page` |
| No obvious security vulnerabilities | see below |
| Another developer can install and run it | the README steps were run as written using the real `flask` commands (see "Limits" for the one exception) |

### Security tests

| Risk | Test |
|---|---|
| Cross-site request forgery | `test_csrf_required`, `test_admin_actions_need_csrf` - missing or forged tokens are refused and nothing changes |
| Cross-site scripting | `test_html_is_escaped_everywhere` - a `<script>` tag sent through the form is shown as text on the confirmation page, the admin list and the admin detail page |
| Password guessing | `test_login_lockout` - 5 failures lock that username from that address for 15 minutes, even for the correct password |
| Revealing which usernames exist | `test_wrong_password` - unknown user and wrong password get the identical response (timing is equalised in code too) |
| Session fixation | `test_login_changes_session` |
| Redirect to a malicious site after login | `test_open_redirect_blocked` |
| Spam and form flooding | `test_honeypot_pretends_success_but_stores_nothing`, `test_rate_limit` (5 per visitor per 15 min), `test_oversized_post_rejected` |
| Spreadsheet formula injection in the CSV export | `test_csv_export_escapes_formulas` |
| Admin pages open to the public | `test_admin_pages_need_login`, `test_logout_requires_post_and_ends_session` |
| Leaked error details | `test_errors_do_not_leak_details` |
| Stored passwords | `test_passwords_are_hashed` (scrypt), `test_weak_admin_password_refused` |
| Browser protections | `test_security_headers` (strict CSP without `unsafe-inline`, no framing, nosniff), `test_session_cookie_flags`, `test_admin_not_cached_or_indexed`, `test_no_inline_scripts_or_styles` |
| Data retention | `test_purge_old_keeps_bookings_and_recent` |
| Invented reviews | `test_no_fake_social_proof` - fails if the words testimonial, Trustpilot, star ratings etc. appear on any page |

## Results at delivery

```
48 passed in about 60 seconds
Python 3.13, Flask 3.1, Chromium (Playwright), Linux
```

## Limits - what was not tested

- **Waitress and Gunicorn were not run.** The build environment could not download packages, so the site was tested
  on Flask's built-in server. The app code is identical under either; the risk is limited to the server command itself.
  Try `python run.py` once after `pip install -r requirements.txt`.
- **Windows and macOS were not tested** for this project (the code uses nothing platform-specific; the date formatting
  was written to avoid a known Windows difference).
- **Browsers other than Chromium were not tested.** The CSS and JavaScript use widely supported features only; checking
  in Safari on an iPhone and in Firefox before launch is recommended.
- **Email sending was not tested against a real mail server.** The code path is written so that a mail failure can never
  lose an enquiry, but the first real alert should be checked after setting the SMTP details.
- **No professional penetration test.** The tests above cover the common web risks (OWASP Top 10 categories relevant to
  this site); they are not a substitute for an independent security review if the business needs one.
- **Accessibility** was designed for (labels, focus states, error summary, keyboard menu, reduced motion, contrast), but
  not audited with a screen reader.
