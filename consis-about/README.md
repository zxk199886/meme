# Consis Engineering — About Us

A redesigned **About Us** page for [Consis Engineering](https://consis.com.sg/about-us/),
re-styled to follow the visual language of the
[Singapore Green Plan 2030](https://www.greenplan.gov.sg/) website:

- Fresh green palette with generous whitespace
- Bold display typography
- A **funnel content structure**: Vision → Our Story → 5 Pillars → The System → By the Numbers → Take Action
- Nature motifs, big-number targets and clear calls to action

All of the original About Us content is preserved and reorganised, including:
the company story (founded 2006, debut at the Singapore Garden Festival), the
award-winning Consis Vertical Greenery System (Consis VGS), its five winning
features, the integrated irrigation/fertigation/drainage system, technical
specs (95% coverage from day one, UL 94 V0 fire rating, 3 kg/m² frame, 2D & 3D
designs), and the full corporate + contact details.

## Files

| File | Purpose |
|------|---------|
| `index.html` | Page markup and all content |
| `styles.css` | Green Plan–inspired styling, fully responsive |
| `script.js`  | Sticky nav, mobile menu, scroll reveals, animated counters |

## Run it

It's a static site — no build step. Open `index.html` directly, or serve the
folder:

```bash
cd consis-about
python3 -m http.server 8000
# then visit http://localhost:8000
```

Fonts load from Google Fonts when online and fall back to system fonts offline.
