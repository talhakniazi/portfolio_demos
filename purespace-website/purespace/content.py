"""Business details used across the website.

SAMPLE CONTENT: every value below is a placeholder written for the demonstration.
Replace them with the real details before launch. Items marked VERIFY are claims
about the business - they must be true (UK consumer protection law) before they go live.
While SAMPLE_CONTENT is True, the admin dashboard shows a reminder.
"""
SAMPLE_CONTENT = True

BUSINESS = {
    "name": "PureSpace Cleaning Services Ltd",
    "short_name": "PureSpace",
    "phone": "0161 496 0731",            # Ofcom drama-range number - replace
    "phone_link": "+441614960731",
    "whatsapp": "07700 900417",          # Ofcom drama-range number - replace
    "whatsapp_link": "447700900417",
    "email": "hello@purespace-cleaning.example",
    "area": "Greater Manchester and Stockport",
    "address": ["Unit 3, Example Business Park", "Manchester M1 1AA"],
    "hours": [("Monday to Friday", "7am to 7pm"), ("Saturday", "8am to 4pm"), ("Sunday", "Closed")],
    "company_number": "00000000",        # Companies House number - replace
    "founded": 2019,                     # VERIFY
}

PROMISES = [   # VERIFY every line before launch
    ("Insured", "Public liability insurance up to £5 million on every job."),
    ("Vetted staff", "Every cleaner is DBS-checked, trained and employed by us - not subcontracted."),
    ("Re-clean guarantee", "Tell us within 24 hours if anything was missed and we come back free of charge."),
    ("Your own products, or ours", "We bring eco-friendly products and equipment as standard."),
]

AREAS = ["Manchester city centre", "Salford", "Stockport", "Trafford", "Didsbury", "Chorlton", "Sale", "Altrincham", "Prestwich", "Cheadle"]

CLOTHS = [   # the colour-coding system used by professional cleaners (and our brand)
    ("blue", "Blue", "Living areas, offices, desks and general surfaces"),
    ("green", "Green", "Kitchens and food areas"),
    ("red", "Red", "Toilets and urinals"),
    ("yellow", "Yellow", "Washbasins, showers and bathroom surfaces"),
]
