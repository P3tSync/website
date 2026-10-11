## Petsync

A demo Flask web app for pet food delivery and vet appointment booking. PetSync includes a demo kitchen, clinic, pet profiles, shopping cart checkout, booking flow, a dashboard, and frontend animations.

## Features

- Public CozyPaws-style landing: letter-by-letter hero ("Everything Your Pets Need"), postcode search, floating product/video cards, pet photo panels with speech bubbles, kitchens strip, glow pillar cards, partner teaser
- "Get early access" waitlist pill in the hero (emails stored in `waitlist_emails` via `/api/waitlist`)
- Preview accounts: Order / Vets / Pets tabs need a demo or admin login (Partners stays public); login returns you to where you were headed
- Aurora-style onboarding login at `/access` (demo: `demo@petsync.co.uk` / `petsync-demo`; admin: `admin@petsync.co.uk` / `petsync-admin`)
- Pet Profile Management
- Browse kitchens and add food to shopping cart
- Order checkout with delivery total (£)
- Browse vet clinics and book appointment slots
- Partner Contact Form
- Reduced-motion-safe CSS animations (no animation library)

## Requirements

- Python 3.10+ (or compatible Python 3)
- flask

## Install

1. Create a virtual environment:

```Bash
python -m venv .venv
```

1. Activate the Environment:

- Windows Powershell:
  ```Powershell
  .\.venv\Scripts\Activate.ps1
  ```
- Windows CMD:
  ```CMD
  .\.venv\Scripts\activate.bat
  ```

2. Install Dependencies:

```Bash
pip install -r requirements.txt
```

## Run the app

3. Start the app:

```Bash
python app.py
```

4. Open the app in your browser:

```
http://127.0.0.1:5000/
```

## Database

The app uses SQLite by default. It automatically initializes the schema and sends demo data on startup.

## Test

Run unit tests with:

```Bash
python test_app.py
```
 ### Project Structure

- `app.py` - main flask application
- `requirements.txt` - Python dependencies
- `test_app.py` - unit tests for main routes and protected flows
 - `Templates/` - Jinja HTML Templates (`home.html` landing, `access.html` Aurora login)
 - `static/css/styles.css` - full-site styling (Velvet Purple system)
 - `static/css/glow.css` - shared glow feature cards
 - `static/css/aurora.css` - Aurora-style login page styling
 - `static/js/petsync-animations.js` - scroll-reveal, letter stagger
 - `static/img/logo.png` - transparent Petsync logo (`logo-black.png` is the original black-tile backup)

 ### Access

 - Order food, Find a vet and My pets require a demo or admin login; For partners and the waitlist stay public.
 - Log in at `/access` (demo and admin accounts both work there).
 - Admins can also sign in at `/admin/login` (`PETSYNC_ADMIN_PASSWORD`) for the dashboard.
 - Env overrides: `PETSYNC_ADMIN_EMAIL`, `PETSYNC_DEMO_EMAIL` / `PETSYNC_DEMO_PASSWORD`.

 ### Notes

 - Prices are in £ for the UK launch.
