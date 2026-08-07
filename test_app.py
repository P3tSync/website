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

    def test_animations_js_served_at_documented_path(self):
        resp = self.client.get("/static/js/petsync-animations.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"petsync-theme", resp.data)

    def test_theme_toggle_sets_data_theme_attribute(self):
        resp = self.client.get("/static/js/petsync-animations.js")
        body = resp.data.decode("utf-8")
        self.assertIn('root.setAttribute("data-theme"', body)
        self.assertNotIn('classList.toggle("dark"', body)

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


if __name__ == "__main__":
    unittest.main()
