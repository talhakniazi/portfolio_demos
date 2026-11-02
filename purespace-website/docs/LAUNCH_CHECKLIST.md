# Launch checklist

The website works fully as delivered, but some content is **sample text** that only the business can confirm. Publishing
an untrue claim (for example an insurance level you don't hold) can breach consumer-protection law, so please check
every item below. All of it lives in `purespace/content.py` unless stated otherwise.

## Business details - replace

- [ ] Phone number (sample: 0161 496 0731, an Ofcom number reserved for TV and film, so it never rings anyone)
- [ ] WhatsApp number (sample: 07700 900417, also a reserved fictional number)
- [ ] Email address (sample: hello@purespace-cleaning.example)
- [ ] Postal address (sample: Unit 3, Example Business Park, Manchester M1 1AA)
- [ ] Company number (sample: 00000000) - must be your real Companies House number (shown in the footer and About page)
- [ ] Opening hours
- [ ] Year founded and the "How we started" story on the About page (`templates/about.html`)
- [ ] Areas covered (list of towns on the home page)

## Claims - confirm each one is true, or edit/remove it

- [ ] "Public liability insurance up to £5 million on every job" - check your policy
- [ ] "Every cleaner is DBS-checked, trained and employed by us - not subcontracted"
- [ ] "Re-clean guarantee: tell us within 24 hours and we come back free of charge"
- [ ] "We bring eco-friendly products and equipment as standard" - "eco-friendly" should be something you can back up
- [ ] "Cloths are washed at 90°C after every job"
- [ ] "We reply within one working day" / "Evening and weekend slots"
- [ ] Office cleaning page, "How we work with businesses": free walk-round, same cleaners each week, key-holding and alarm
      procedures, named supervisor, safety data sheets, risk assessments and method statements, monthly invoicing,
      30 days' notice / no long contracts (`templates/commercial.html`)
- [ ] Room-by-room checklists on the Home cleaning page match what your cleaners actually do

## Prices - confirm

- [ ] Every price in `purespace/pricing.py`: base prices, per-bedroom and per-bathroom amounts, hourly office rates,
      minimum hours, add-ons, and frequency discounts (weekly 10%, fortnightly 5%)
- [ ] Guide prices are shown as a range of ±15%. Change `RANGE` in `pricing.py` if you want it wider or narrower
- [ ] Open the Prices page and two or three quote-form combinations and check the figures look right to you

## Privacy and legal

- [ ] Read the Privacy notice (`templates/privacy.html`) and adjust it to how you really handle data. In particular the
      retention periods (12 months for enquiries that don't book; 6 years for customers)
- [ ] Register with the ICO and pay the data protection fee if you haven't already (most UK businesses that hold
      customer data must)
- [ ] If you add analytics, chat widgets or advertising tags later, the cookie wording and Content Security Policy
      need updating

## Technical

- [ ] Set `SAMPLE_CONTENT = False` in `content.py` (removes the reminder banner in the admin area)
- [ ] Delete any DEMO enquiries, or start with a fresh database
- [ ] Create admin logins for real staff; don't share one login between people
- [ ] Site served over HTTPS with `PURESPACE_SECURE_COOKIES=1`
- [ ] Optional: set the email settings so the office gets an email for each new enquiry, then send a test quote
- [ ] Daily database backups set up (see `DEPLOYMENT.md`)
- [ ] Monthly `purge-old` job scheduled, or the retention wording in the privacy notice changed to match what you do
- [ ] Submit one real test quote and one test message on the live site, check both appear in the admin area, then delete them
