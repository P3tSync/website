# Finish Petsync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every crashing/silently-broken behavior in the Petsync Flask app, add the `test_app.py` suite the README promises, integrate the provided logo, and apply three agreed polish items — no new pages or features.

**Architecture:** Single Flask app (`app.py`) + Jinja templates + one CSS file + one vanilla JS file, SQLite storage. All fixes are surgical edits to existing files; one new test file (`test_app.py`) and two new templates (`login.html`, `error.html`). Tests use `unittest` + Flask's built-in test client against a fresh temp SQLite file per test — no new dependencies.

**Tech Stack:** Python 3.14 (project requires 3.10+), Flask 3.1.3, SQLite (stdlib `sqlite3`), vanilla JS, anime.js from CDN, `unittest` (stdlib).

## Global Constraints

- No new pip dependencies — `requirements.txt` stays `Flask` only. Tests use stdlib `unittest`, not `pytest`.
- Tests run via `python test_app.py` (per README) — the file must be executable directly and via `unittest` discovery.
- anime.js CDN reference must be pinned to `animejs@3.2.2` (project code assumes v3's `anime({...})` callable API, not v4's `.animate()` method).
- Dark mode: JS must set the `data-theme` attribute (not a `.dark` class) — `styles.css`'s `[data-theme="dark"]` selector is the fixed point, do not change `styles.css`'s theme selectors.
- Logo source file: `C:\Users\ROG_X13\Desktop\petsync\logo.png`, 256×192px. Every `<img>` referencing it must set an explicit `height` attribute — never render it unsized.
- `PETSYNC_ADMIN_PASSWORD` env var defaults to `"petsync-admin"` (see `app.py:17`) — tests rely on this default unless they set the env var themselves.
- Every task ends with a commit. Use `git add <specific files>` (never `-A`) and commit messages in imperative mood.
- Working directory for all commands below: `C:\Users\ROG_X13\Desktop\petsync\website-main`, using the venv Python at `.venv/Scripts/python.exe` (or an activated venv shell).

---

### Task 1: Test harness scaffold + smoke test

**Files:**
- Create: `test_app.py`

**Interfaces:**
- Produces: `PetsyncTestCase` (subclass of `unittest.TestCase`) — every later task appends test methods to this class. `self.client` is a Flask test client bound to a fresh temp SQLite DB per test (via `setUp`/`tearDown` swapping `app.DB_PATH`).

- [ ] **Step 1: Write the test harness and one smoke test**

```python
import atexit
import os
import tempfile
import unittest
from pathlib import Path

_import_fd, _import_db_path = tempfile.mkstemp(suffix=".db")
os.close(_import_fd)
os.environ["PETSYNC_DB_PATH"] = _import_db_path
os.environ.setdefault("PETSYNC_ADMIN_PASSWORD", "petsync-admin")
atexit.register(lambda: Path(_import_db_path).unlink(missing_ok=True))

import app as petsync_app  # noqa: E402 (must import after env vars are set above)


class PetsyncTestCase(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db_path = Path(path)
        petsync_app.DB_PATH = self.db_path
        petsync_app.init_db()
        petsync_app.seed_db()
        petsync_app.ensure_demo_pet()
        petsync_app.app.config["TESTING"] = True
        self.client = petsync_app.app.test_client()

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    def test_home_page_returns_200(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: `test_home_page_returns_200 ... ok`, 1 test run, OK.

- [ ] **Step 3: Commit**

```bash
git add test_app.py
git commit -m "test: add test harness with temp-db isolation and smoke test"
```

---

### Task 2: Fix static JS path (404 for animations/theme-toggle script)

**Files:**
- Modify: move `static/css/js/petsync-animations.js` → `static/js/petsync-animations.js`
- Modify: `test_app.py` (append test to `PetsyncTestCase`)

**Interfaces:**
- Consumes: `PetsyncTestCase` from Task 1.

- [ ] **Step 1: Write the failing test**

Append to `PetsyncTestCase` in `test_app.py`:

```python
    def test_animations_js_served_at_documented_path(self):
        resp = self.client.get("/static/js/petsync-animations.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"petsync-theme", resp.data)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: `test_animations_js_served_at_documented_path ... FAIL` (404, file not found at that path).

- [ ] **Step 3: Move the file**

```bash
mkdir -p static/js
git mv static/css/js/petsync-animations.js static/js/petsync-animations.js
rmdir static/css/js
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: both tests OK.

- [ ] **Step 5: Commit**

```bash
git add -u static/css/js static/js/petsync-animations.js test_app.py
git commit -m "fix: serve petsync-animations.js from the path base.html expects"
```

---

### Task 3: Fix dark mode toggle (class vs. attribute mismatch)

**Files:**
- Modify: `static/js/petsync-animations.js` (the `setTheme` function, near the top of the file)
- Modify: `test_app.py` (append test)

**Interfaces:**
- Consumes: static file route fixed in Task 2 (`/static/js/petsync-animations.js` now resolves).

- [ ] **Step 1: Write the failing test**

Append to `PetsyncTestCase`:

```python
    def test_theme_toggle_sets_data_theme_attribute(self):
        resp = self.client.get("/static/js/petsync-animations.js")
        body = resp.data.decode("utf-8")
        self.assertIn('root.setAttribute("data-theme"', body)
        self.assertNotIn('classList.toggle("dark"', body)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: FAIL — the file still does `root.classList.toggle("dark", isDark)`.

- [ ] **Step 3: Fix `setTheme`**

In `static/js/petsync-animations.js`, replace:

```js
  function setTheme(theme) {
    const isDark = theme === "dark";
    root.classList.toggle("dark", isDark);
    if (themeToggle) {
```

with:

```js
  function setTheme(theme) {
    const isDark = theme === "dark";
    root.setAttribute("data-theme", isDark ? "dark" : "light");
    if (themeToggle) {
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 5: Commit**

```bash
git add static/js/petsync-animations.js test_app.py
git commit -m "fix: dark mode toggle sets data-theme attribute to match styles.css"
```

---

### Task 4: Add missing `templates/login.html`

**Files:**
- Create: `templates/login.html`
- Modify: `test_app.py` (append 4 tests)

**Interfaces:**
- Consumes: `app.py` routes `admin_login()` (`app.py:764-773`) and `dashboard()` / `login_required` (`app.py:318-325`, `app.py:747-749`) — unchanged, already correct, just missing their template.

- [ ] **Step 1: Write the failing tests**

Append to `PetsyncTestCase`:

```python
    def test_admin_login_page_renders(self):
        resp = self.client.get("/admin/login")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sign in", resp.data)

    def test_admin_login_wrong_password_rejected(self):
        resp = self.client.post(
            "/admin/login", data={"password": "nope"}, follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"did not work", resp.data)

    def test_admin_login_correct_password_unlocks_dashboard(self):
        resp = self.client.post(
            "/admin/login",
            data={"password": "petsync-admin"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Dashboard", resp.data)

    def test_dashboard_requires_login(self):
        resp = self.client.get("/dashboard", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sign in", resp.data)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all 4 new tests FAIL/ERROR with `TemplateNotFound: login.html`.

- [ ] **Step 3: Create the template**

```html
{% extends "base.html" %}
{% block title %}Admin sign in — Petsync{% endblock %}
{% block content %}

<section class="wrap page-head">
  <span class="eyebrow">Internal</span>
  <h1>Operations sign in</h1>
  <p class="lede">Enter the admin password to view the operations dashboard.</p>
</section>

<section class="wrap">
  <form method="post" class="form-card">
    <div class="field-row">
      <label for="password">Password</label>
      <input id="password" name="password" type="password" required autofocus>
    </div>
    <button type="submit" class="btn btn-primary" style="width:100%;">Sign in</button>
  </form>
</section>

{% endblock %}
```

Save as `templates/login.html`.

- [ ] **Step 4: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 5: Commit**

```bash
git add templates/login.html test_app.py
git commit -m "fix: add missing admin login template"
```

---

### Task 5: Add missing `templates/error.html`

**Files:**
- Create: `templates/error.html`
- Modify: `test_app.py` (append test)

**Interfaces:**
- Consumes: `app.py`'s `not_found()` / `server_error()` handlers (`app.py:781-789`), which pass `code`, `title`, `message` — unchanged.

- [ ] **Step 1: Write the failing test**

Append to `PetsyncTestCase`:

```python
    def test_unknown_route_returns_custom_404(self):
        resp = self.client.get("/this-page-does-not-exist")
        self.assertEqual(resp.status_code, 404)
        self.assertIn(b"Page not found", resp.data)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: FAIL/ERROR — `TemplateNotFound: error.html` (raised while handling the 404, so the response won't even be a clean 404).

- [ ] **Step 3: Create the template**

```html
{% extends "base.html" %}
{% block title %}{{ title }} — Petsync{% endblock %}
{% block content %}

<section class="wrap confirmation-box">
  <h1>{{ code }}</h1>
  <h2>{{ title }}</h2>
  <p class="lede">{{ message }}</p>
  <a href="{{ url_for('home') }}" class="btn btn-primary" style="margin-top:24px;">Back to home</a>
</section>

{% endblock %}
```

Save as `templates/error.html`.

- [ ] **Step 4: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 5: Commit**

```bash
git add templates/error.html test_app.py
git commit -m "fix: add missing error page template for 404/500 handlers"
```

---

### Task 6: Fix `history.html` item-count bug

**Files:**
- Modify: `app.py:392-407` (`owner_history()`)
- Modify: `templates/history.html:23`
- Modify: `test_app.py` (append helper method + test)

**Interfaces:**
- Produces: `PetsyncTestCase._create_test_order(self) -> int` — creates one order for the seeded demo pet via the real cart/checkout flow and returns its `order_id`. Reused by Task 8.

- [ ] **Step 1: Write the failing test (and shared helper)**

Append to `PetsyncTestCase`:

```python
    def _create_test_order(self):
        with petsync_app.app.app_context():
            db = petsync_app.get_db()
            kitchen = db.execute("SELECT id FROM kitchens LIMIT 1").fetchone()
            item = db.execute(
                "SELECT id FROM menu_items WHERE kitchen_id=? LIMIT 1",
                (kitchen["id"],),
            ).fetchone()
            pet = db.execute("SELECT id FROM pets LIMIT 1").fetchone()
        self.client.post(
            "/cart/add",
            data={"kitchen_id": kitchen["id"], "item_id": item["id"], "qty": 1},
        )
        resp = self.client.post(
            "/cart",
            data={
                "pet_id": pet["id"],
                "pet_name": "Miso",
                "address": "1 Test Street, Testville",
                "notes": "",
            },
        )
        return int(resp.headers["Location"].rstrip("/").split("/")[-1])

    def test_history_shows_correct_item_count(self):
        self._create_test_order()
        resp = self.client.get("/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"1 items", resp.data)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: FAIL — the rendered page shows a large number (JSON string length) instead of "1 items".

- [ ] **Step 3: Fix the route**

In `app.py`, replace the body of `owner_history()`:

```python
@app.route("/history")
def owner_history():
    db = get_db()
    active_pet = get_selected_pet()
    if active_pet:
        orders = db.execute(
            "SELECT * FROM orders WHERE pet_id=? ORDER BY id DESC LIMIT 25",
            (active_pet["id"],)).fetchall()
        bookings = db.execute(
            "SELECT * FROM bookings WHERE pet_id=? ORDER BY slot_time DESC LIMIT 25",
            (active_pet["id"],)).fetchall()
    else:
        orders = []
        bookings = []
    return render_template("history.html", active_pet=active_pet,
                           orders=orders, bookings=bookings)
```

with:

```python
@app.route("/history")
def owner_history():
    db = get_db()
    active_pet = get_selected_pet()
    if active_pet:
        order_rows = db.execute(
            "SELECT * FROM orders WHERE pet_id=? ORDER BY id DESC LIMIT 25",
            (active_pet["id"],)).fetchall()
        orders = []
        for row in order_rows:
            order = dict(row)
            order["items"] = json.loads(order["items_json"])
            orders.append(order)
        bookings = db.execute(
            "SELECT * FROM bookings WHERE pet_id=? ORDER BY slot_time DESC LIMIT 25",
            (active_pet["id"],)).fetchall()
    else:
        orders = []
        bookings = []
    return render_template("history.html", active_pet=active_pet,
                           orders=orders, bookings=bookings)
```

In `templates/history.html`, replace:

```html
          <p>{{ order['items_json'] | length }} items · {{ order['total_cents'] | money }} delivered to {{ order['address'][:40] }}</p>
```

with:

```html
          <p>{{ order['items'] | length }} items · {{ order['total_cents'] | money }} delivered to {{ order['address'][:40] }}</p>
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 5: Commit**

```bash
git add app.py templates/history.html test_app.py
git commit -m "fix: parse order items so history page shows a real item count"
```

---

### Task 7: Fix vets.html typo

**Files:**
- Modify: `templates/vets.html:8`
- Modify: `test_app.py` (append test)

- [ ] **Step 1: Write the failing test**

Append to `PetsyncTestCase`:

```python
    def test_vets_page_has_no_typo(self):
        resp = self.client.get("/vets")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(b"Avvailable", resp.data)
        self.assertIn(b"Available slots", resp.data)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: FAIL — page contains "Avvailable slots".

- [ ] **Step 3: Fix the typo**

In `templates/vets.html`, replace:

```html
  <p class="lede">Avvailable slots, filtered by species and urgency — book in one tap.</p>
```

with:

```html
  <p class="lede">Available slots, filtered by species and urgency — book in one tap.</p>
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 5: Commit**

```bash
git add templates/vets.html test_app.py
git commit -m "fix: correct typo on vets page"
```

---

### Task 8: Pin anime.js to v3 and simplify order_status.html

**Files:**
- Modify: `templates/base.html:103` (anime.js CDN `<script>` tag)
- Modify: `templates/order_status.html:42-76` (`{% block scripts %}`)
- Modify: `test_app.py` (append 2 tests)

**Interfaces:**
- Consumes: `PetsyncTestCase._create_test_order()` from Task 6.

- [ ] **Step 1: Write the failing tests**

Append to `PetsyncTestCase`:

```python
    def test_anime_js_cdn_pinned_to_v3(self):
        resp = self.client.get("/")
        self.assertIn(b"animejs@3.2.2", resp.data)

    def test_order_status_uses_single_anime_call_style(self):
        order_id = self._create_test_order()
        resp = self.client.get(f"/orders/{order_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(b"window.anime.animate", resp.data)
        self.assertIn(b"window.anime(", resp.data)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: both FAIL — CDN URL is unpinned, and `order_status.html` still contains `window.anime.animate`.

- [ ] **Step 3: Pin the CDN script**

In `templates/base.html`, replace:

```html
<script src="https://cdn.jsdelivr.net/npm/animejs/dist/bundles/anime.umd.min.js"></script>
```

with:

```html
<script src="https://cdn.jsdelivr.net/npm/animejs@3.2.2/lib/anime.umd.js"></script>
```

- [ ] **Step 4: Simplify the order-status polling script**

In `templates/order_status.html`, replace:

```js
      if (window.anime && window.anime.animate) {
        window.anime.animate(fillEl, {
          width: data.pct + '%',
          duration: 650,
          easing: 'outCubic'
        });
      } else {
        fillEl.style.width = data.pct + '%';
      }
```

with:

```js
      if (window.anime) {
        window.anime({
          targets: fillEl,
          width: data.pct + '%',
          duration: 650,
          easing: 'easeOutCubic'
        });
      } else {
        fillEl.style.width = data.pct + '%';
      }
```

- [ ] **Step 5: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 6: Commit**

```bash
git add templates/base.html templates/order_status.html test_app.py
git commit -m "fix: pin anime.js to v3 and use one consistent call style"
```

---

### Task 9: Logo integration (favicon + sized header/footer brand marks)

**Files:**
- Create: `static/img/logo.png` (copy of `C:\Users\ROG_X13\Desktop\petsync\logo.png`)
- Modify: `templates/base.html` (head favicon link near line 10; header brand mark near lines 52-55; footer brand mark near lines 96-98)
- Modify: `static/css/styles.css` (append a small rule)
- Modify: `test_app.py` (append 2 tests)

- [ ] **Step 1: Write the failing tests**

Append to `PetsyncTestCase`:

```python
    def test_favicon_link_present(self):
        resp = self.client.get("/")
        self.assertIn(b'rel="icon"', resp.data)
        self.assertIn(b"img/logo.png", resp.data)

    def test_logo_served_and_brand_marks_sized(self):
        resp = self.client.get("/static/img/logo.png")
        self.assertEqual(resp.status_code, 200)
        home = self.client.get("/").data
        self.assertIn(b'height="28"', home)
        self.assertIn(b'height="32"', home)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: both FAIL — no favicon link, `/static/img/logo.png` 404s, no sized `<img>` tags.

- [ ] **Step 3: Copy the logo into the static folder**

```bash
mkdir -p static/img
cp "C:\Users\ROG_X13\Desktop\petsync\logo.png" static/img/logo.png
```

- [ ] **Step 4: Add the favicon link**

In `templates/base.html`, replace:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
```

with:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
<link rel="icon" type="image/png" href="{{ url_for('static', filename='img/logo.png') }}">
</head>
```

- [ ] **Step 5: Replace the header brand mark**

In `templates/base.html`, replace:

```html
    <a href="{{ url_for('home') }}" class="brand">
      <svg class="brand-mark" viewBox="0 0 24 24"><use href="#icon-paw"/></svg>
      <span class="brand-word">Petsync</span>
    </a>
```

with:

```html
    <a href="{{ url_for('home') }}" class="brand">
      <img src="{{ url_for('static', filename='img/logo.png') }}" alt="Petsync" height="28" style="width:auto;object-fit:contain;">
    </a>
```

- [ ] **Step 6: Replace the footer brand mark**

In `templates/base.html`, replace:

```html
    <a href="{{ url_for('home') }}" class="foot-brand">
      <svg viewBox="0 0 24 24"><use href="#icon-paw"/></svg> Petsync
    </a>
```

with:

```html
    <a href="{{ url_for('home') }}" class="foot-brand">
      <img src="{{ url_for('static', filename='img/logo.png') }}" alt="Petsync" height="32" style="width:auto;object-fit:contain;">
    </a>
```

- [ ] **Step 7: Add a small CSS tidy-up rule**

Append to `static/css/styles.css`:

```css
/* Logo */
.brand img, .foot-brand img { display: block; }
```

- [ ] **Step 8: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 9: Commit**

```bash
git add static/img/logo.png templates/base.html static/css/styles.css test_app.py
git commit -m "feat: use the Petsync logo as favicon and header/footer brand mark"
```

---

### Task 10: Polish — booking form reselects species after a validation error

**Files:**
- Modify: `templates/booking_form.html:26-31`
- Modify: `test_app.py` (append test)

- [ ] **Step 1: Write the failing test**

Append to `PetsyncTestCase`:

```python
    def test_booking_form_reselects_species_after_error(self):
        with petsync_app.app.app_context():
            db = petsync_app.get_db()
            slot = db.execute(
                "SELECT id, vet_id FROM vet_slots WHERE is_booked=0 LIMIT 1"
            ).fetchone()
        resp = self.client.post(
            f"/vets/{slot['vet_id']}/book/{slot['id']}",
            data={
                "pet_id": "",
                "owner_name": "",
                "pet_name": "Miso",
                "species": "cat",
                "reason": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'value="cat" selected', resp.data)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: FAIL — species dropdown re-renders with no option marked `selected`.

- [ ] **Step 3: Fix the template**

In `templates/booking_form.html`, replace:

```html
      <select id="species" name="species">
        <option value="dog">Dog</option>
        <option value="cat">Cat</option>
        <option value="exotic">Exotic</option>
        <option value="small mammal">Small mammal</option>
      </select>
```

with:

```html
      <select id="species" name="species">
        <option value="dog" {% if form.species=='dog' %}selected{% endif %}>Dog</option>
        <option value="cat" {% if form.species=='cat' %}selected{% endif %}>Cat</option>
        <option value="exotic" {% if form.species=='exotic' %}selected{% endif %}>Exotic</option>
        <option value="small mammal" {% if form.species=='small mammal' %}selected{% endif %}>Small mammal</option>
      </select>
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 5: Commit**

```bash
git add templates/booking_form.html test_app.py
git commit -m "polish: booking form keeps the submitted species selected after an error"
```

---

### Task 11: Polish — cart shows "Remove" instead of a silent decrement-to-zero

**Files:**
- Modify: `templates/cart.html:25-30`
- Modify: `static/css/styles.css` (append a small rule)
- Modify: `test_app.py` (append test)

- [ ] **Step 1: Write the failing test**

Append to `PetsyncTestCase`:

```python
    def test_cart_shows_remove_button_at_qty_one(self):
        with petsync_app.app.app_context():
            db = petsync_app.get_db()
            kitchen = db.execute("SELECT id FROM kitchens LIMIT 1").fetchone()
            item = db.execute(
                "SELECT id FROM menu_items WHERE kitchen_id=? LIMIT 1",
                (kitchen["id"],),
            ).fetchone()
        self.client.post(
            "/cart/add",
            data={"kitchen_id": kitchen["id"], "item_id": item["id"], "qty": 1},
        )
        resp = self.client.get("/cart")
        self.assertIn(b">Remove<", resp.data)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: FAIL — no "Remove" text in the cart page; the qty=1 line shows a bare "−" button instead.

- [ ] **Step 3: Fix the template**

In `templates/cart.html`, replace:

```html
      <form action="{{ url_for('cart_update') }}" method="post" class="qty-form">
        <input type="hidden" name="item_id" value="{{ line['id'] }}">
        <button type="submit" name="qty" value="{{ line['qty'] - 1 }}" class="qty-btn">−</button>
        <span class="qty-num">{{ line['qty'] }}</span>
        <button type="submit" name="qty" value="{{ line['qty'] + 1 }}" class="qty-btn">+</button>
      </form>
```

with:

```html
      <form action="{{ url_for('cart_update') }}" method="post" class="qty-form">
        <input type="hidden" name="item_id" value="{{ line['id'] }}">
        {% if line['qty'] == 1 %}
        <button type="submit" name="qty" value="0" class="qty-btn qty-remove">Remove</button>
        {% else %}
        <button type="submit" name="qty" value="{{ line['qty'] - 1 }}" class="qty-btn">−</button>
        {% endif %}
        <span class="qty-num">{{ line['qty'] }}</span>
        <button type="submit" name="qty" value="{{ line['qty'] + 1 }}" class="qty-btn">+</button>
      </form>
```

- [ ] **Step 4: Add supporting CSS**

Append to `static/css/styles.css`:

```css
.qty-remove { width: auto; border-radius: 8px; padding: 0 10px; font-size: 0.8rem; color: var(--danger); border-color: var(--danger); }
```

- [ ] **Step 5: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 6: Commit**

```bash
git add templates/cart.html static/css/styles.css test_app.py
git commit -m "polish: cart shows an explicit Remove button instead of decrementing to zero silently"
```

---

### Task 12: Polish — mobile nav collapse

**Files:**
- Modify: `templates/base.html` (nav-row block, currently lines ~50-78; shifted after Task 9's edits — locate by the `<div class="wrap nav-row">` opening tag)
- Modify: `static/css/styles.css` (append a media-query block)
- Modify: `test_app.py` (append test)

- [ ] **Step 1: Write the failing test**

Append to `PetsyncTestCase`:

```python
    def test_mobile_nav_toggle_present(self):
        resp = self.client.get("/")
        self.assertIn(b'id="nav-toggle"', resp.data)
        self.assertIn(b'class="nav-toggle-label"', resp.data)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: FAIL — no hamburger toggle markup exists yet.

- [ ] **Step 3: Add the checkbox-driven hamburger markup**

In `templates/base.html`, replace:

```html
    <a href="{{ url_for('home') }}" class="brand">
      <img src="{{ url_for('static', filename='img/logo.png') }}" alt="Petsync" height="28" style="width:auto;object-fit:contain;">
    </a>
    <nav class="nav-links">
```

with:

```html
    <a href="{{ url_for('home') }}" class="brand">
      <img src="{{ url_for('static', filename='img/logo.png') }}" alt="Petsync" height="28" style="width:auto;object-fit:contain;">
    </a>
    <input type="checkbox" id="nav-toggle" class="nav-toggle-checkbox">
    <label for="nav-toggle" class="nav-toggle-label" aria-label="Toggle menu">☰</label>
    <nav class="nav-links">
```

(This edit depends on Task 9 having already swapped the header brand mark to an `<img>`; the `<a class="brand">...</a>` block content must match exactly what Task 9 left behind.)

- [ ] **Step 4: Add the responsive CSS**

Append to `static/css/styles.css`:

```css
/* Mobile nav */
.nav-toggle-checkbox { display: none; }
.nav-toggle-label { display: none; cursor: pointer; font-size: 1.4rem; line-height: 1; }
@media (max-width: 640px) {
  .nav-row { flex-wrap: wrap; }
  .nav-toggle-label { display: block; margin-left: auto; order: 1; }
  .nav-links {
    display: none;
    order: 5;
    flex-basis: 100%;
    flex-direction: column;
    gap: 4px;
    margin-left: 0;
  }
  .nav-toggle-checkbox:checked ~ .nav-links { display: flex; }
  .pet-switcher, .theme-toggle, .nav-cart { order: 2; }
}
```

- [ ] **Step 5: Run it to confirm it passes**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK.

- [ ] **Step 6: Manual verification**

Start the app (`./.venv/Scripts/python.exe app.py`), open `http://127.0.0.1:5000/` in a browser, resize the window below 640px width, and confirm the nav links collapse behind a tappable "☰" that expands/collapses them. Confirm the brand logo, cart icon, and theme toggle stay visible and usable at that width.

- [ ] **Step 7: Commit**

```bash
git add templates/base.html static/css/styles.css test_app.py
git commit -m "polish: collapse nav links behind a hamburger toggle on narrow viewports"
```

---

### Task 13: Remaining spec-required test coverage

The design spec's "Tests" section lists coverage for pet creation, order
filtering/menu browsing, cart validation, vet double-booking, and the
partner form — none of which are tied to a specific bug fix above but are
still required. Add them now, all in one pass.

**Files:**
- Modify: `test_app.py` (append 6 tests)

**Interfaces:**
- Consumes: `PetsyncTestCase` and its `_create_test_order` helper (unused
  here, but same DB-query pattern reused).

- [ ] **Step 1: Write the tests**

Append to `PetsyncTestCase`:

```python
    def test_pet_creation_valid_and_invalid(self):
        resp = self.client.post(
            "/pets",
            data={
                "name": "Rex", "species": "dog", "life_stage": "adult",
                "allergies": "", "diet_notes": "",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Rex", resp.data)

        resp = self.client.post(
            "/pets",
            data={"name": "", "species": "dog", "life_stage": "adult"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Pet name is required.", resp.data)

    def test_order_browse_filters_by_species(self):
        resp = self.client.get("/order?species=cat")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Whisker Pantry", resp.data)

    def test_kitchen_menu_lists_items(self):
        with petsync_app.app.app_context():
            db = petsync_app.get_db()
            kitchen = db.execute("SELECT id, name FROM kitchens LIMIT 1").fetchone()
        resp = self.client.get(f"/order/{kitchen['id']}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(kitchen["name"].encode(), resp.data)

    def test_cart_checkout_requires_address(self):
        with petsync_app.app.app_context():
            db = petsync_app.get_db()
            kitchen = db.execute("SELECT id FROM kitchens LIMIT 1").fetchone()
            item = db.execute(
                "SELECT id FROM menu_items WHERE kitchen_id=? LIMIT 1",
                (kitchen["id"],),
            ).fetchone()
            pet = db.execute("SELECT id FROM pets LIMIT 1").fetchone()
        self.client.post(
            "/cart/add",
            data={"kitchen_id": kitchen["id"], "item_id": item["id"], "qty": 1},
        )
        resp = self.client.post(
            "/cart",
            data={
                "pet_id": pet["id"], "pet_name": "Miso",
                "address": "short", "notes": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Enter a complete delivery address.", resp.data)

    def test_vet_double_booking_rejected(self):
        with petsync_app.app.app_context():
            db = petsync_app.get_db()
            slot = db.execute(
                "SELECT id, vet_id FROM vet_slots WHERE is_booked=0 LIMIT 1"
            ).fetchone()
            pet = db.execute("SELECT id FROM pets LIMIT 1").fetchone()
        first = self.client.post(
            f"/vets/{slot['vet_id']}/book/{slot['id']}",
            data={
                "pet_id": pet["id"], "owner_name": "Alex", "pet_name": "Miso",
                "species": "cat", "reason": "check-up",
            },
        )
        self.assertEqual(first.status_code, 302)
        second = self.client.get(
            f"/vets/{slot['vet_id']}/book/{slot['id']}", follow_redirects=True
        )
        self.assertEqual(second.status_code, 200)
        self.assertIn(b"just booked by someone else", second.data)

    def test_partners_form_valid_and_invalid(self):
        resp = self.client.post(
            "/partners",
            data={
                "kind": "kitchen", "business_name": "Test Kitchen",
                "contact_name": "Alex", "email": "alex@example.com",
                "message": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Thanks", resp.data)

        resp = self.client.post(
            "/partners",
            data={
                "kind": "kitchen", "business_name": "",
                "contact_name": "", "email": "", "message": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Business name and email are required.", resp.data)
```

- [ ] **Step 2: Run the full suite**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: all tests OK, including the 6 new ones.

- [ ] **Step 3: Commit**

```bash
git add test_app.py
git commit -m "test: cover pet creation, order filtering, cart validation, double-booking, partner form"
```

---

### Task 14: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `.venv/Scripts/python.exe test_app.py -v`
Expected: every test across all 13 prior tasks passes (should be ~27 tests total).

- [ ] **Step 2: Boot the app and manually click through every flow**

Run: `.venv/Scripts/python.exe app.py` (background it or use a second terminal), then in a browser:
- Home → Order food → pick a kitchen → add an item → Cart → checkout → order status page (confirm the progress bar animates and no console errors from anime.js).
- Home → Find a vet → book an open slot → confirm booking confirmation page.
- Toggle dark mode from the header — confirm the whole page palette changes, not just the button icon.
- Visit `/admin/login`, try a wrong password (see the flash error), then the correct password (`petsync-admin` unless overridden) and confirm the dashboard loads.
- Visit a nonexistent URL (e.g. `/nope`) and confirm the styled 404 page renders (not a stack trace).
- Resize the browser below 640px and confirm the nav collapses correctly.
- Confirm the browser tab shows the Petsync paw favicon, and the header/footer logos are a normal, correctly-proportioned size (not stretched or huge).

- [ ] **Step 3: Stop the dev server**

If started in the background for this check, stop it.

No commit for this task — it's a verification-only checkpoint confirming Tasks 1-12 together produce a working app.
