# Finish Petsync: bug fixes, tests, targeted polish

Date: 2026-08-07

## Goal

Get the existing Petsync Flask app (pet food delivery + vet booking demo) into a
working, tested state: fix everything that currently crashes or silently fails,
add the test suite the README already promises, and apply a small, agreed-upon
set of UX polish items. No new features/pages are in scope.

## Scope: Bug fixes

1. **Static JS path.** `templates/base.html` references
   `static/js/petsync-animations.js`, but the file lives at
   `static/css/js/petsync-animations.js`. Move the file to
   `static/js/petsync-animations.js` (matches the README's documented
   structure). Delete the now-empty `static/css/js/` directory.

2. **Missing `templates/login.html`.** `admin_login()` renders it on GET and on
   failed POST; currently crashes with `TemplateNotFound`. Add a template
   consistent with the existing form-card styling (see `partners.html` /
   `booking_form.html` for the pattern): a single password field, submit
   button, using `base.html`.

3. **Missing `templates/error.html`.** Both the 404 and 500 handlers render
   this with `code`, `title`, `message`. Add a template that displays those
   three variables with a link back to `home`.

4. **`history.html` item count bug.** `owner_history()` passes raw `orders`
   rows straight from the DB; `items_json` is a JSON string, and the template
   does `{{ order['items_json'] | length }}`, which is the string's character
   count, not the item count. Fix in the route: parse `items_json` per order
   (`json.loads`) into an `items` list before passing to the template, and
   update the template to use `order.items | length` — same pattern already
   used correctly in `order_status_page()`.

5. **Typo.** "Avvailable slots" → "Available slots" in `templates/vets.html`.

6. **Unsized brand-mark icons.** Neither `.brand-mark` (header) nor the
   footer's bare `<svg><use href="#icon-paw"/></svg>` has a CSS width/height
   rule, and `styles.css` has no generic `svg` size rule either. Browsers fall
   back to the default replaced-element size (~300×150) for an un-set SVG,
   stretching the 24×24 paw artwork into a large, distorted shape instead of a
   small icon. Confirmed live: this is what's actually rendering, not
   `logo.png` (which isn't wired into any template yet). Resolved as part of
   the logo integration below — both spots get an explicitly-sized `<img>`
   instead of an unsized `<svg>`.

## Scope: Dark mode fix

`petsync-animations.js` toggles a `.dark` class on `<html>`; `styles.css`
keys its entire dark palette off `[data-theme="dark"]` on an ancestor. They
never match — the toggle changes the button icon only.

**Fix:** change `petsync-animations.js` to set `root.setAttribute('data-theme',
theme)` (and remove it / set to `"light"` for light mode) instead of toggling a
class. `styles.css` is unchanged — it's already correct.

## Scope: anime.js version pin

The CDN `<script>` tag in `base.html` is unpinned
(`animejs/dist/bundles/anime.umd.min.js`). `petsync-animations.js` calls the
v3-style API (`anime({ targets, ...params })`); `order_status.html` guards for
`anime.animate` (a v4-only method) with a fallback. If the CDN ever resolves to
v4 by default, `petsync-animations.js` breaks (calling the default export as a
function is not the v4 pattern).

**Fix:**
- Pin the CDN URL to a specific v3 release, e.g.
  `https://cdn.jsdelivr.net/npm/animejs@3.2.2/lib/anime.umd.js` (project already
  assumes v3 semantics elsewhere).
- Simplify `order_status.html`'s script block to call `anime({...})` directly
  (drop the `window.anime.animate` branch and its `else` fallback — one
  consistent v3 call site).

## Scope: Logo integration

`C:\Users\ROG_X13\Desktop\petsync\logo.png` (purple paw + "Petsync" wordmark)
is the project logo.

- Copy it into `static/img/logo.png` (new folder; no existing image asset
  location in the project).
- Add it as the favicon: `<link rel="icon" href="{{ url_for('static',
  filename='img/logo.png') }}">` in `base.html`'s `<head>`.
- Replace the header brand mark in `base.html` (`<svg class="brand-mark">` +
  `<span class="brand-word">Petsync</span>`) with a single `<img>` tag pointing
  at the same file, with **explicit `height="28"` (width auto, `object-fit:
  contain`)** so it can't fall back to native-resolution rendering (source
  file is 256×192px — without sizing it would reproduce the exact oversized/
  distorted look already seen with the unsized SVG). The hand-drawn SVG
  `#icon-paw` symbol stays in the sprite sheet since it's reused elsewhere
  (`home.html` hero); only the header nav's brand mark changes. Apply the same
  swap to the footer brand mark, with `height="32"`.

## Scope: Tests

Add `test_app.py` at the project root (matches `python test_app.py` from the
README) using `unittest` + Flask's built-in test client — no new dependency.

- Each test case sets `PETSYNC_DB_PATH` to a fresh temp file (via
  `tempfile.mkstemp()` in `setUp`, removed in `tearDown`) so tests don't touch
  the real `petsync.db` and don't leak state between tests. Re-import or
  re-invoke `init_db()`/`seed_db()`/`ensure_demo_pet()` against that temp path
  per test.
- Coverage:
  - `GET /` returns 200.
  - Pet creation: `POST /pets` with valid data creates a pet and redirects;
    missing name shows a validation error (re-renders form, pet not created).
  - Order flow: `GET /order` filters kitchens; `GET /order/<id>` lists menu
    items; `POST /cart/add` adds an item to session cart; `POST /cart` (empty
    address) shows a validation error; `POST /cart` with valid data creates an
    order and redirects to `/orders/<id>`.
  - Vet flow: `GET /vets` lists clinics; `POST` to `/vets/<id>/book/<slot>`
    with valid data creates a booking, marks the slot booked, and a second
    booking attempt on the same slot is rejected.
  - Partner form: valid POST creates a lead and shows the success state;
    missing email does not create a lead.
  - Admin/dashboard: `GET /dashboard` without auth redirects to login;
    `POST /admin/login` with the correct password (via
    `PETSYNC_ADMIN_PASSWORD` env var set in the test) authenticates and
    `GET /dashboard` then returns 200; wrong password does not authenticate.
  - 404 handling: an unknown route returns the custom 404 page (verifies the
    `error.html` fix).

## Scope: Polish (agreed items only)

1. **Booking form species reselect.** `booking_form.html`'s species `<select>`
   doesn't mark any option `selected` based on `form.species`, so after a
   validation error (e.g. missing owner name) it silently reverts to showing
   "Dog" even if the pet is a cat. Add `{% if form.species=='...' %}selected{%
   endif %}` per option, same pattern already used in `pets.html`.

2. **Cart remove confirmation.** In `cart.html`, the qty "−" button at qty=1
   currently submits `qty=0`, which `cart_update()` treats as "remove the
   line" with no feedback beyond the line disappearing. Change: when
   `line.qty == 1`, render the "−" button as a "Remove" text button (still
   posts `qty=0` to the same endpoint) instead of a bare "−" glyph, so the
   destructive action is legible instead of a silent decrement-to-nothing.

3. **Mobile nav collapse.** `.site-nav` is a plain flex row
   (`brand` / `nav-links` / `pet-switcher` / `theme-toggle` / `cart`) with no
   responsive behavior — on narrow viewports the links wrap or overflow.
   Add a CSS-only collapse: below 640px, hide `.nav-links` behind a hamburger
   toggle button (checkbox-driven `:checked` CSS pattern, no new JS) that
   expands into a stacked dropdown. Brand, cart, and theme toggle stay visible
   in the collapsed bar.

**Explicitly out of scope for this round** (noted during audit, not
requested): live delivery-tracking map on the order status page, further
mobile layout work beyond the nav, currency/locale changes, favicon-only
alternative (superseded by the header brand-mark swap above).

## Verification

- `python app.py` boots without error; manually click through home → order →
  cart → checkout → order status, and vets → book → confirmation, and
  `/admin/login` → dashboard, and an invalid URL (404 page renders).
- Toggle dark mode and confirm the palette actually changes.
- Check the header and footer brand marks render as a small, correctly
  proportioned logo (not the oversized/distorted paw shape seen pre-fix).
- `python test_app.py` — all tests pass.
