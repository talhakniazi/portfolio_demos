# Design notes

## The idea

Professional cleaners colour-code their cloths so that nothing used on a toilet ever touches a kitchen:
**blue** for general areas, **green** for kitchens, **red** for toilets, **yellow** for basins and showers. It's a real
hygiene practice, it's specific to cleaning, and it gives PureSpace a brand that no generic "sparkle and bubbles"
cleaning site has.

The four colours appear as the stacked-cloth logo, the hero illustration, the stripe under each call-to-action panel,
and the coloured edges of the service lists. Everywhere else the site stays calm: deep navy text on white and a pale
"mist" blue-grey.

## Colours

| Token | Hex | Use |
|---|---|---|
| `--ink` | `#14284b` | Text, primary buttons, footer |
| `--mist` | `#eef3f6` | Alternate section backgrounds |
| `--blue` / `--green` / `--red` / `--yellow` | cloth colours | Logo, illustrations, stripes, small markers only |
| `--*-text` variants | darker versions | Any coloured text, so it passes WCAG AA contrast |

Never put body text in the bright cloth colours; use the `-text` variants.

## Type

- **Bricolage Grotesque** (headings): a characterful grotesque with optical sizes, used heavy and tight at large sizes.
- **Atkinson Hyperlegible** (body): designed by the Braille Institute for readers with low vision. Clear letter shapes
  (it distinguishes 0/O and 1/l/I), which matters for prices, postcodes, phone numbers and reference codes.

Both are self-hosted (no Google Fonts request, which keeps the privacy notice simple) and subset to Latin characters.

## Motion

One moment only: on the home page the four cloths drop into a stack when the page loads, then two sparkles appear.
Turned off automatically for visitors who ask their device for reduced motion. Everything else moves only in response
to the visitor (menu opening, live price updating).

## Writing

Plain, specific British English. Buttons say what happens ("Send my quote request", "See office cleaning"). Errors say
how to fix the problem ("Enter a full UK postcode, like M1 1AA"). No invented reviews, statistics or awards.

## Adding a page

1. Create `templates/yourpage.html` extending `base.html` (copy `about.html` as a starting point).
2. Add a route in `public.py` and, if it belongs in the menu, an entry in the `nav` list at the top of `base.html`.
3. Add it to `sitemap.xml` (in `public.py`) and to `PAGES` in `tests/test_pages.py` and `tests/test_browser.py` so the
   tests cover it.
4. No inline `<style>` or `<script>`: the Content Security Policy blocks them. Add CSS to `static/css/site.css`.
