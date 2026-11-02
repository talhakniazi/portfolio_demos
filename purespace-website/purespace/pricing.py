"""Guide prices for the online estimator.

These are SAMPLE figures. The business owner should set their real prices here -
the same rules drive the live estimate on the website (sent to the browser as JSON)
and the estimate saved with each enquiry (calculated again on the server, so a
visitor cannot alter it).
"""
from __future__ import annotations

import math

RESIDENTIAL = {
    #  service key       label                      base  per bedroom  per bathroom
    "regular":        ("Regular home clean",          45,   10,          8),
    "deep":           ("Deep clean",                 120,   30,         25),
    "end_of_tenancy": ("End of tenancy clean",       150,   40,         30),
    "after_builders": ("After-builders clean",       200,   45,         35),
}
COMMERCIAL = {
    #  service key       label                      £ per hour  sq ft cleaned per hour  minimum hours
    "office_regular": ("Regular office cleaning",     19,        1500,                   2),
    "office_deep":    ("One-off deep office clean",   24,         900,                   4),
    "communal":       ("Communal areas and stairwells", 19,      2000,                   2),
}
FREQUENCY = {   # discount on each visit for regular bookings
    "weekly": ("Weekly", 0.10), "fortnightly": ("Every two weeks", 0.05), "monthly": ("Monthly", 0.0),
    "one_off": ("One-off", 0.0), "daily": ("Every weekday", 0.15), "three_weekly": ("Three times a week", 0.12),
}
EXTRAS = {"oven": ("Oven clean", 60), "windows_inside": ("Inside windows", 25), "fridge": ("Inside fridge", 20),
          "linen": ("Change bed linen", 10), "carpet": ("Carpet shampoo (per room)", 35)}
RANGE = 0.15     # the estimate is shown as a range: price -15% to +15%

SERVICE_LABELS = {k: v[0] for k, v in {**RESIDENTIAL, **COMMERCIAL}.items()}


def estimate(sector, service, bedrooms, bathrooms, floor_area, frequency, extras):
    """Return (low, high) in whole pounds, or (None, None) if there is not enough information."""
    if sector == "residential" and service in RESIDENTIAL:
        _, base, per_bed, per_bath = RESIDENTIAL[service]
        price = base + per_bed * (bedrooms or 0) + per_bath * (bathrooms or 0)
    elif sector == "commercial" and service in COMMERCIAL:
        if not floor_area:
            return None, None
        _, rate, sqft_hr, min_hours = COMMERCIAL[service]
        price = rate * max(min_hours, floor_area / sqft_hr)
    else:
        return None, None
    price *= 1 - FREQUENCY.get(frequency, ("", 0.0))[1]
    price += sum(EXTRAS[e][1] for e in extras if e in EXTRAS)
    r5 = lambda x: int(math.floor(x / 5 + 0.5)) * 5      # same rounding as Math.round in quote.js
    return r5(price * (1 - RANGE)), r5(price * (1 + RANGE))


def as_json():
    return {"residential": {k: v[1:] for k, v in RESIDENTIAL.items()}, "commercial": {k: v[1:] for k, v in COMMERCIAL.items()},
            "frequency": {k: v[1] for k, v in FREQUENCY.items()}, "extras": {k: v[1] for k, v in EXTRAS.items()}, "range": RANGE}


def from_price(service):
    """Lowest guide price for a service, for 'from £X' labels (smallest home / minimum visit)."""
    if service in RESIDENTIAL:
        return estimate("residential", service, 1, 1, None, "one_off", [])[0]
    if service in COMMERCIAL:
        _, rate, sqft_hr, min_hours = COMMERCIAL[service]
        return estimate("commercial", service, None, None, int(sqft_hr * min_hours), "one_off", [])[0]
    return None
