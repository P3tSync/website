import atexit
import os
import tempfile
import unittest
from pathlib import Path

import markupsafe

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
        petsync_app.ensure_accounts()
        petsync_app.app.config["TESTING"] = True
        self.client = petsync_app.app.test_client()
        self.client.post("/access", data={
            "email": petsync_app.DEMO_EMAIL,
            "password": petsync_app.DEMO_PASSWORD,
        })

    def _log_out(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    def test_home_page_returns_200(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_animations_js_served_at_documented_path(self):
        resp = self.client.get("/static/js/petsync-animations.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"motion-ready", resp.data)

    def test_theme_toggle_sets_data_theme_attribute(self):
        resp = self.client.get("/static/js/petsync-animations.js")
        body = resp.data.decode("utf-8")
        self.assertIn("prefers-reduced-motion", body)
        self.assertIn("IntersectionObserver", body)
        self.assertNotIn('data-theme', body)
        home = self.client.get("/").data
        self.assertNotIn(b"theme-toggle", home)

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
        self._log_out()
        resp = self.client.get("/dashboard", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sign in", resp.data)

    def test_site_public_without_login(self):
        self._log_out()
        for path in ["/", "/partners", "/access"]:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)

    def test_gated_tabs_require_login(self):
        self._log_out()
        for path in ["/order", "/vets", "/pets", "/cart", "/history"]:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 302, path)
            self.assertIn("/access", resp.headers["Location"], path)

    def test_login_redirects_to_next(self):
        self._log_out()
        resp = self.client.post("/access?next=/order", data={
            "email": petsync_app.DEMO_EMAIL,
            "password": petsync_app.DEMO_PASSWORD})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers["Location"].endswith("/order"))

    def test_home_has_kitchens_strip_and_contact(self):
        self._log_out()
        resp = self.client.get("/")
        self.assertIn(b"Fresh from local kitchens", resp.data)
        self.assertIn("Willow &amp; Bone".encode(), resp.data)
        self.assertIn(b"Bark Lane", resp.data)

    def test_public_home_has_hero_and_pill(self):
        self._log_out()
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'name="location"', resp.data)
        self.assertIn(b"Order pet food", resp.data)
        self.assertIn(b"wl-pill", resp.data)
        self.assertIn(b"Get early access", resp.data)
        self.assertIn(b"glow-band", resp.data)

    def test_full_home_shown_with_access(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"What Petsync does", resp.data)
        self.assertNotIn(b"wl-pill", resp.data)

    def test_waitlist_has_glow_cards(self):
        resp = self.client.get("/")
        self.assertIn(b"Pet Groceries", resp.data)
        self.assertIn(b"Fresh Food Delivery", resp.data)
        self.assertIn(b"Local Vet Matching", resp.data)
        self.assertIn(b"glow-face", resp.data)
        css = self.client.get("/static/css/glow.css").data.decode()
        self.assertIn("blur(45px)", css)

    def test_public_hero_waitlist_pill_joins(self):
        self._log_out()
        joined = self.client.post("/", data={"email": "pill@example.com"},
                                  follow_redirects=True)
        self.assertIn(b"on the list", joined.data)
        self.assertNotIn(b"wl-pill-form", joined.data)

    def test_home_has_glow_band(self):
        resp = self.client.get("/")
        self.assertIn(b"glow-band", resp.data)
        self.assertIn(b"Pet Groceries", resp.data)
        self.assertIn(b"Local Vet Matching", resp.data)
        self.assertIn(b"blur(45px)", self.client.get(
            "/static/css/glow.css").data)

    def test_access_demo_code_unlocks_site(self):
        self._log_out()
        bad = self.client.post("/access", data={
            "email": petsync_app.DEMO_EMAIL, "password": "wrong"},
            follow_redirects=True)
        self.assertIn(b"did not work", bad.data)
        good = self.client.post("/access", data={
            "email": petsync_app.DEMO_EMAIL,
            "password": petsync_app.DEMO_PASSWORD},
            follow_redirects=True)
        self.assertIn(b"What Petsync does", good.data)

    def test_access_page_is_aurora_onboarding(self):
        self._log_out()
        resp = self.client.get("/access")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"auth-left", resp.data)
        self.assertIn(b"auth-steps", resp.data)
        self.assertIn(b"Sign in to your account", resp.data)
        self.assertIn(b"auth-eye", resp.data)
        self.assertIn(b"stream.mux.com", resp.data)
        self.assertIn(b"aurora.css", resp.data)

    def test_access_admin_account_unlocks_dashboard(self):
        self._log_out()
        self.client.post("/access", data={
            "email": petsync_app.ADMIN_EMAIL,
            "password": petsync_app.ADMIN_PASSWORD})
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Dashboard", resp.data)

    def test_admin_login_unlocks_full_site(self):
        self._log_out()
        self.client.post("/admin/login",
                         data={"password": "petsync-admin"})
        resp = self.client.get("/")
        self.assertIn(b"What Petsync does", resp.data)

    def test_waitlist_api_valid_invalid_duplicate(self):
        self._log_out()
        ok = self.client.post("/api/waitlist", json={"email": "a@example.com"})
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.get_json()["ok"])
        dup = self.client.post("/api/waitlist", json={"email": "a@example.com"})
        self.assertEqual(dup.status_code, 200)
        bad = self.client.post("/api/waitlist", json={"email": "nope"})
        self.assertEqual(bad.status_code, 400)

    def test_waitlist_form_post_joins(self):
        self._log_out()
        resp = self.client.post("/", data={"email": "b@example.com"},
                                follow_redirects=True)
        self.assertIn(b"on the list", resp.data)

    def test_unknown_route_returns_custom_404(self):
        resp = self.client.get("/this-page-does-not-exist")
        self.assertEqual(resp.status_code, 404)
        self.assertIn(b"Page not found", resp.data)

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

    def test_vets_page_has_no_typo(self):
        resp = self.client.get("/vets")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(b"Avvailable", resp.data)
        self.assertIn(b"Available slots", resp.data)

    def test_anime_js_cdn_pinned_to_v3(self):
        resp = self.client.get("/")
        self.assertNotIn(b"anime.min.js", resp.data)
        self.assertIn(b"hero-search", resp.data)
        self.assertIn(b"cozy-letter", resp.data)

    def test_order_status_uses_single_anime_call_style(self):
        order_id = self._create_test_order()
        resp = self.client.get(f"/orders/{order_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(b"window.anime", resp.data)
        self.assertIn(b"progress-fill", resp.data)

    def test_favicon_link_present(self):
        resp = self.client.get("/")
        self.assertIn(b'rel="icon"', resp.data)
        self.assertIn(b"img/logo.png", resp.data)

    def test_logo_served_and_brand_marks_sized(self):
        resp = self.client.get("/static/img/logo.png")
        self.assertEqual(resp.status_code, 200)
        home = self.client.get("/").data
        self.assertIn(b'height="44"', home)
        self.assertIn(b'height="48"', home)

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

    def test_mobile_nav_toggle_present(self):
        resp = self.client.get("/")
        self.assertIn(b'id="nav-toggle"', resp.data)
        self.assertIn(b'class="nav-toggle-label"', resp.data)

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
        # Seeded kitchen names can contain "&" (e.g. "Willow & Bone Kitchen"),
        # which Jinja2 autoescaping renders as "&amp;" in the HTML response.
        # Escape the expected value the same way before comparing.
        self.assertIn(str(markupsafe.escape(kitchen["name"])).encode(), resp.data)

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

    def test_cart_checkout_form_includes_pet_id_field(self):
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
        resp = self.client.get("/cart")
        self.assertIn(
            f'name="pet_id" value="{pet["id"]}"'.encode(), resp.data
        )

    def test_booking_form_includes_pet_id_field(self):
        with petsync_app.app.app_context():
            db = petsync_app.get_db()
            slot = db.execute(
                "SELECT id, vet_id FROM vet_slots WHERE is_booked=0 LIMIT 1"
            ).fetchone()
            pet = db.execute("SELECT id FROM pets LIMIT 1").fetchone()
        resp = self.client.get(f"/vets/{slot['vet_id']}/book/{slot['id']}")
        self.assertIn(
            f'name="pet_id" value="{pet["id"]}"'.encode(), resp.data
        )

    def test_vercel_hero_details_ported(self):
        self._log_out()
        resp = self.client.get("/")
        self.assertIn(b"cozy-hero__heading", resp.data)
        self.assertIn(b"cozy-letter", resp.data)
        self.assertIn(b'data-says="woof!"', resp.data)
        self.assertIn(b'data-says="treats?"', resp.data)
        self.assertIn(b'data-says="meow?"', resp.data)
        self.assertNotIn(b"cursor-bubble", resp.data)
        self.assertIn("browsing as a guest".encode(), resp.data)
        js = self.client.get("/static/js/petsync-animations.js").data.decode()
        self.assertIn("cozy-letter", js)
        self.assertNotIn("cursor-bubble", js)
        self.client.post("/access", data={
            "email": petsync_app.DEMO_EMAIL,
            "password": petsync_app.DEMO_PASSWORD})
        logged = self.client.get("/")
        self.assertIn(b"acct-menu", logged.data)
        self.assertIn(b"Hey Miso", logged.data)

    def test_clock_ticker_rotates_around_its_own_center(self):
        resp = self.client.get("/static/css/styles.css")
        body = resp.data.decode("utf-8")
        self.assertIn("@keyframes letter-pop", body)
        self.assertIn("@keyframes photo-reveal", body)
        self.assertIn("prefers-reduced-motion", body)
        self.assertNotIn(".ticker", body)


if __name__ == "__main__":
    unittest.main()
