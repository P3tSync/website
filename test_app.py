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
        petsync_app.app.config["TESTING"] = True
        self.client = petsync_app.app.test_client()

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    def test_home_page_returns_200(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_animations_js_served_at_documented_path(self):
        resp = self.client.get("/static/js/petsync-animations.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"petsync-theme", resp.data)

    def test_theme_toggle_sets_data_theme_attribute(self):
        resp = self.client.get("/static/js/petsync-animations.js")
        body = resp.data.decode("utf-8")
        self.assertIn('root.setAttribute("data-theme"', body)
        self.assertNotIn('classList.toggle("dark"', body)
        self.assertNotIn('classList.contains("dark")', body)

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
        self.assertIn(b"animejs@3.2.2/lib/anime.min.js", resp.data)

    def test_order_status_uses_single_anime_call_style(self):
        order_id = self._create_test_order()
        resp = self.client.get(f"/orders/{order_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(b"window.anime.animate", resp.data)
        self.assertIn(b"window.anime(", resp.data)

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


if __name__ == "__main__":
    unittest.main()
