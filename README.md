## Petsync

A demo Flask web app for pet food delivery and vet appointment booking. PetSync includes a demo kitchen, clinic, pet profiles, shopping cart checkout, booking flow, a dashboard, and frontend animations.

## Features

- Home page with animated clock and pet care timeline
- Pet Profile Management
- Browse kitchens and add food to shopping cart
- Order checkout with delivery total
- Browse vet clinics and book appointment slots
- Partner Contact Form
- Toggle light/dark theme with saved preference
- Frontend animations powered by Anime.js

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
  ``Powershell
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
- `Templates/` - Jinja HTML Templates
- `static/css/styles.css` - site styling and dark mode support
- `static/js/petsync-animations.js` - Anime.js animations and theme toggle logic

 ### Notes

- Theme toggle saves the selected mode to `localstorage`.
- Animations use Anime.js from CDN.
