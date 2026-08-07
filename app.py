import json
import os
import random
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, g, render_template, request, session, redirect, url_for, flash, abort, jsonify 

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("PETSYNC_DB_PATH", BASE_DIR / "petsync.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("PETSYNC_SECRET_KEY", "dev-petsync-secret-change-me")

DELIVERY_FEE_CENTS = 299
ADMIN_PASSWORD = os.environ.get("PETSYNC_ADMIN_PASSWORD", "petsync-admin")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

SCHEMA = """
CREATE TABLE IF NOT EXISTS kitchens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    tagline TEXT,
    tags TEXT,
    rating REAL,
    eta_min INTEGER,
    distance_label TEXT,
    accent TEXT
);

CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id),
    name TEXT NOT NULL,
    description TEXT,
    price_cents INTEGER NOT NULL,
    tag TEXT
);

CREATE TABLE IF NOT EXISTS vets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    lat REAL,
    lng REAL,
    phone TEXT,
    species TEXT,
    urgency TEXT,
    rating REAL,
    distance_label TEXT
);

CREATE TABLE IF NOT EXISTS vet_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vet_id INTEGER NOT NULL REFERENCES vets(id),
    slot_time TEXT NOT NULL,
    is_booked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    name TEXT NOT NULL,
    species TEXT NOT NULL,
    life_stage TEXT,
    allergies TEXT,
    diet_notes TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    pet_id INTEGER REFERENCES pets(id),
    kitchen_id INTEGER,
    kitchen_name TEXT,
    items_json TEXT,
    subtotal_cents INTEGER,
    delivery_fee_cents INTEGER,
    total_cents INTEGER,
    pet_name TEXT,
    address TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    pet_id INTEGER REFERENCES pets(id),
    vet_id INTEGER,
    vet_name TEXT,
    slot_time TEXT,
    owner_name TEXT,
    pet_name TEXT,
    species TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS partner_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    kind TEXT,
    business_name TEXT,
    contact_name TEXT,
    email TEXT,
    message TEXT
);
"""

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    existing_order_cols = {
        row[1] for row in db.execute("PRAGMA table_info(orders)").fetchall()
    }
    if "pet_id" not in existing_order_cols:
        db.execute("ALTER TABLE orders ADD COLUMN pet_id INTEGER REFERENCES pets(id)")
    existing_booking_cols = {
        row[1] for row in db.execute("PRAGMA table_info(bookings)").fetchall()
    }
    if "pet_id" not in existing_booking_cols:
        db.execute("ALTER TABLE bookings ADD COLUMN pet_id INTEGER REFERENCES pets(id)")
    db.commit()
    db.close()

def seed_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    existing = db.execute("SELECT COUNT(*) AS c FROM kitchens").fetchone()["c"]
    if existing:
        db.close()
        return

    kitchens = [
        dict(name="Willow & Bone Kitchen", tagline="Grain-conscious, senior-friendly",
             tags="Grain-conscious,Senior-friendly", rating=4.8, eta_min=25,
             distance_label="0.4 mi", accent="#C8842A"),
        dict(name="Northpaw Provisions", tagline="High-protein, puppy formulas",
             tags="High-protein,Puppy formulas", rating=4.6, eta_min=30,
             distance_label="0.9 mi", accent="#6FB08F"),
        dict(name="The Whisker Pantry", tagline="Cat-only, limited ingredient",
             tags="Cat-only,Limited ingredient", rating=4.9, eta_min=20,
             distance_label="1.2 mi", accent="#E2604A"),
        dict(name="Two Bowls Kitchen", tagline="Mixed menu, family packs",
             tags="Mixed menu,Family packs", rating=4.5, eta_min=35,
             distance_label="1.6 mi", accent="#173C3C"),
    ]
    kitchen_ids = {}
    for k in kitchens:
        cur = db.execute(
            "INSERT INTO kitchens (name, tagline, tags, rating, eta_min, distance_label, accent) "
            "VALUES (:name,:tagline,:tags,:rating,:eta_min,:distance_label,:accent)", k)
        kitchen_ids[k["name"]] = cur.lastrowid

    menu = [
        ("Willow & Bone Kitchen", "Slow-Cooked Turkey & Pumpkin Bowl",
         "Lean turkey, roasted pumpkin, and a vet-formulated mineral mix.", 650, "Adult"),
        ("Willow & Bone Kitchen", "Senior Joint-Support Stew",
         "Beef and bone broth with glucosamine, soft-cooked carrots.", 720, "Senior"),
        ("Willow & Bone Kitchen", "Salmon & Sweet Potato Mash",
         "Omega-rich salmon with sweet potato for sensitive stomachs.", 690, "Sensitive stomach"),

        ("Northpaw Provisions", "Puppy Growth Bowl",
         "Extra-protein recipe for growing pups, calcium-balanced.", 600, "Puppy"),
        ("Northpaw Provisions", "Beef & Barley Bowl",
         "Hearty beef with barley and spinach for active dogs.", 675, "Adult"),
        ("Northpaw Provisions", "Lamb & Rice Recovery Meal",
         "Gentle, easy-to-digest meal for dogs recovering from illness.", 710, "Recovery"),

        ("The Whisker Pantry", "Chicken & Pumpkin Pâté",
         "Single-protein pâté for cats with sensitivities.", 540, "Limited ingredient"),
        ("The Whisker Pantry", "Whitefish & Pea Bowl",
         "Light, low-fat recipe for indoor cats.", 580, "Indoor"),
        ("The Whisker Pantry", "Sensitive Tummy Turkey Mince",
         "Minimal-ingredient mince for cats prone to upset stomachs.", 560, "Sensitive stomach"),

        ("Two Bowls Kitchen", "Family Variety Pack (Dog)",
         "Three rotating recipes so dinner never gets boring.", 850, "Variety"),
        ("Two Bowls Kitchen", "Family Variety Pack (Cat)",
         "Three rotating recipes for multi-cat households.", 790, "Variety"),
        ("Two Bowls Kitchen", "Weekend Treat Box",
         "Freeze-dried liver bites for training and treat time.", 420, "Treats"),
    ]
    for kitchen_name, name, desc, price, tag in menu:
        db.execute(
            "INSERT INTO menu_items (kitchen_id, name, description, price_cents, tag) "
            "VALUES (?,?,?,?,?)",
            (kitchen_ids[kitchen_name], name, desc, price, tag))

    vets = [
        dict(name="Riverside Veterinary Clinic", address="12 Riverside Walk, London",
             lat=51.5079, lng=-0.1281, phone="020 7946 0991",
             species="dog,cat,exotic", urgency="routine,urgent", rating=4.7,
             distance_label="0.6 mi"),
        dict(name="Northgate Animal Hospital", address="84 Northgate Road, London",
             lat=51.5132, lng=-0.1190, phone="020 7946 0102",
             species="dog,cat", urgency="routine", rating=4.5,
             distance_label="1.1 mi"),
        dict(name="Willow Paws Vet Care", address="5 Willow Lane, London",
             lat=51.5022, lng=-0.1345, phone="020 7946 0233",
             species="dog,cat,small mammal", urgency="routine,urgent", rating=4.8,
             distance_label="1.8 mi"),
        dict(name="Lonsdale Emergency Vets", address="201 Lonsdale Ave, London",
             lat=51.5151, lng=-0.1410, phone="020 7946 0777",
             species="dog,cat,exotic", urgency="urgent,emergency", rating=4.6,
             distance_label="2.3 mi"),
    ]
    vet_ids = {}
    for v in vets:
        cur = db.execute(
            "INSERT INTO vets (name, address, lat, lng, phone, species, urgency, rating, distance_label) "
            "VALUES (:name,:address,:lat,:lng,:phone,:species,:urgency,:rating,:distance_label)", v)
        vet_ids[v["name"]] = cur.lastrowid

    now = datetime.now().replace(second=0, microsecond=0)
    random.seed(7)
    for vet_name, vet_id in vet_ids.items():
        for day_offset in range(0, 3):
            day = (now + timedelta(days=day_offset)).replace(hour=9, minute=0)
            for slot_i in range(6):
                slot_time = day + timedelta(minutes=90 * slot_i)
                if slot_time <= now:
                    continue
                is_booked = 1 if random.random() < 0.35 else 0
                db.execute(
                    "INSERT INTO vet_slots (vet_id, slot_time, is_booked) VALUES (?,?,?)",
                    (vet_id, slot_time.isoformat(timespec="minutes"), is_booked))

    db.execute(
        "INSERT INTO pets (created_at, name, species, life_stage, allergies, diet_notes) "
        "VALUES (?,?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), "Miso", "cat", "adult",
         "Chicken sensitivity", "Prefers limited-ingredient fish recipes."))

    db.commit()
    db.close()

@app.template_filter("money")
def money(cents):
    return f"${cents / 100:,.2f}"

@app.template_filter("human_slot")
def human_slot(iso_str):
    dt = datetime.fromisoformat(iso_str)
    now = datetime.now()
    if dt.date() == now.date():
        day_label = "Today"
    elif dt.date() == (now + timedelta(days=1)).date():
        day_label = "Tomorrow"
    else:
        day_label = dt.strftime("%a %d %b")
    time_label = dt.strftime("%I:%M %p").lstrip("0")
    return f"{day_label}, {time_label}"

@app.template_filter("title_value")
def title_value(value):
    return (value or "").replace("_", " ").title()

def ensure_demo_pet():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    existing = db.execute("SELECT COUNT(*) AS c FROM pets").fetchone()["c"]
    if not existing:
        db.execute(
            "INSERT INTO pets (created_at, name, species, life_stage, allergies, diet_notes) "
            "VALUES (?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), "Miso", "cat", "adult",
             "Chicken sensitivity", "Prefers limited-ingredient fish recipes."))
        db.commit()
    db.close()

def get_pets():
    return get_db().execute("SELECT * FROM pets ORDER BY id DESC").fetchall()

def get_selected_pet():
    db = get_db()
    pet_id = session.get("selected_pet_id")
    pet = None
    if pet_id:
        pet = db.execute("SELECT * FROM pets WHERE id=?", (pet_id,)).fetchone()
    if pet is None:
        pet = db.execute("SELECT * FROM pets ORDER BY id DESC LIMIT 1").fetchone()
        if pet:
            session["selected_pet_id"] = pet["id"]
    return pet

def pet_form_data():
    return dict(
        name=request.form.get("name", "").strip(),
        species=request.form.get("species", "dog").strip(),
        life_stage=request.form.get("life_stage", "adult").strip(),
        allergies=request.form.get("allergies", "").strip(),
        diet_notes=request.form.get("diet_notes", "").strip(),
    )

def validate_pet(data):
    errors = []
    if not data["name"]:
        errors.append("Pet name is required.")
    if data["species"] not in {"dog", "cat", "exotic", "small mammal"}:
        errors.append("Choose a supported species.")
    if data["life_stage"] not in {"puppy", "kitten", "adult", "senior"}:
        errors.append("Choose a life stage.")
    return errors

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            flash("Sign in to view the operations dashboard.", "warning")
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_cart_count():
    cart = session.get("cart")
    count = sum(cart["items"].values()) if cart else 0
    selected_pet = None
    pets = []
    try:
        selected_pet = get_selected_pet()
        pets = get_pets()
    except sqlite3.Error:
        pass
    return dict(cart_count=count, selected_pet=selected_pet, pets=pets)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/pets", methods=["GET", "POST"])
def pets_page():
    db = get_db()
    form = dict(name="", species="dog", life_stage="adult", allergies="", diet_notes="")
    if request.method == "POST":
        data = pet_form_data()
        errors = validate_pet(data)
        if errors:
            for error in errors:
                flash(error, "warning")
            form = data
        else:
            cur = db.execute(
                "INSERT INTO pets (created_at, name, species, life_stage, allergies, diet_notes) "
                "VALUES (?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), data["name"],
                 data["species"], data["life_stage"], data["allergies"],
                 data["diet_notes"]))
            db.commit()
            session["selected_pet_id"] = cur.lastrowid
            flash(f"{data['name']} is now the active pet profile.", "success")
            return redirect(url_for("pets_page"))

    pets = get_pets()
    active_pet = get_selected_pet()
    pet_summaries = []
    for pet in pets:
        orders = db.execute(
            "SELECT * FROM orders WHERE pet_id=? ORDER BY id DESC LIMIT 3",
            (pet["id"],)).fetchall()
        bookings = db.execute(
            "SELECT * FROM bookings WHERE pet_id=? ORDER BY slot_time DESC LIMIT 3",
            (pet["id"],)).fetchall()
        pet_summaries.append(dict(pet=pet, orders=orders, bookings=bookings))
    return render_template("pets.html", pet_summaries=pet_summaries,
                           active_pet=active_pet, form=form)

@app.route("/pets/select", methods=["POST"])
def select_pet():
    pet_id = int(request.form.get("pet_id", 0))
    pet = get_db().execute("SELECT * FROM pets WHERE id=?", (pet_id,)).fetchone()
    if pet:
        session["selected_pet_id"] = pet["id"]
        flash(f"{pet['name']} is selected.", "success")
    else:
        flash("That pet profile could not be found.", "warning")
    return redirect(request.referrer or url_for("pets_page"))

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

@app.route("/order")
def order_browse():
    db = get_db()
    active_pet = get_selected_pet()
    filters = dict(
        species=request.args.get("species", active_pet["species"] if active_pet else "any"),
        life_stage=request.args.get("life_stage", active_pet["life_stage"] if active_pet else "any"),
        dietary=request.args.get("dietary", "any"),
        max_price=request.args.get("max_price", "any"),
        eta=request.args.get("eta", "any"),
    )
    kitchens = db.execute("""
        SELECT k.*, MIN(m.price_cents) AS min_price_cents,
               GROUP_CONCAT(m.tag || ' ' || m.name || ' ' || COALESCE(m.description, '')) AS menu_text
        FROM kitchens k
        JOIN menu_items m ON m.kitchen_id = k.id
        GROUP BY k.id
        ORDER BY k.name
    """).fetchall()

    filtered = []
    for kitchen in kitchens:
        menu_text = (kitchen["menu_text"] or "").lower()
        include = True
        if filters["species"] == "cat":
            include = "cat" in menu_text or "whisker" in kitchen["name"].lower() or "family" in menu_text
        elif filters["species"] == "dog":
            include = "dog" in menu_text or "puppy" in menu_text or "family" in menu_text
        if include and filters["life_stage"] in {"puppy", "kitten", "senior"}:
            include = filters["life_stage"] in menu_text or (
                filters["life_stage"] == "kitten" and "cat" in menu_text)
        if include and filters["dietary"] != "any":
            terms = {
                "sensitive": ["sensitive", "limited ingredient", "gentle"],
                "high_protein": ["high-protein", "protein"],
                "treats": ["treat", "treats"],
            }[filters["dietary"]]
            include = any(term in menu_text for term in terms)
        if include and filters["max_price"] != "any":
            include = kitchen["min_price_cents"] <= int(filters["max_price"])
        if include and filters["eta"] != "any":
            include = kitchen["eta_min"] <= int(filters["eta"])
        if include:
            filtered.append(kitchen)
    return render_template("order_browse.html", kitchens=filtered, filters=filters,
                           active_pet=active_pet)

@app.route("/order/<int:kitchen_id>")
def kitchen_menu(kitchen_id):
    db = get_db()
    kitchen = db.execute("SELECT * FROM kitchens WHERE id=?", (kitchen_id,)).fetchone()
    if kitchen is None:
        abort(404)
    items = db.execute(
        "SELECT * FROM menu_items WHERE kitchen_id=? ORDER BY id", (kitchen_id,)
    ).fetchall()
    return render_template("kitchen_menu.html", kitchen=kitchen, items=items)

@app.route("/cart/add", methods=["POST"])
def cart_add():
    kitchen_id = int(request.form["kitchen_id"])
    item_id = str(int(request.form["item_id"]))
    qty = max(1, int(request.form.get("qty", 1)))
    db = get_db()
    item = db.execute(
        "SELECT id FROM menu_items WHERE id=? AND kitchen_id=?",
        (item_id, kitchen_id)).fetchone()
    if item is None:
        flash("That menu item is no longer available.", "warning")
        return redirect(url_for("order_browse"))

    cart = session.get("cart")
    if cart and cart["kitchen_id"] != kitchen_id:
        flash("Your cart already has items from another kitchen. "
              "Clear it first to order from here instead.", "warning")
        return redirect(url_for("kitchen_menu", kitchen_id=kitchen_id))

    if not cart:
        kitchen = db.execute("SELECT name FROM kitchens WHERE id=?", (kitchen_id,)).fetchone()
        if kitchen is None:
            flash("That kitchen is no longer available.", "warning")
            return redirect(url_for("order_browse"))
        cart = {"kitchen_id": kitchen_id, "kitchen_name": kitchen["name"], "items": {}}

    cart["items"][item_id] = cart["items"].get(item_id, 0) + qty
    session["cart"] = cart
    flash("Added to cart.", "success")
    return redirect(url_for("kitchen_menu", kitchen_id=kitchen_id))

def _cart_lines(db, cart):
    lines = []
    subtotal = 0
    for item_id, qty in cart["items"].items():
        item = db.execute("SELECT * FROM menu_items WHERE id=?", (item_id,)).fetchone()
        if not item:
            continue
        line_total = item["price_cents"] * qty
        subtotal += line_total
        lines.append(dict(id=item["id"], name=item["name"], qty=qty,
                           price_cents=item["price_cents"], line_total=line_total))
    return lines, subtotal

@app.route("/cart", methods=["GET", "POST"])
def cart_view():
    db = get_db()
    cart = session.get("cart")
    active_pet = get_selected_pet()
    form = dict(pet_id=str(active_pet["id"]) if active_pet else "",
                pet_name=active_pet["name"] if active_pet else "",
                address="", notes="")

    if request.method == "POST":
        if not cart or not cart["items"]:
            return redirect(url_for("order_browse"))

        pet_id_raw = request.form.get("pet_id", "").strip()
        pet_id = int(pet_id_raw) if pet_id_raw.isdigit() else None
        pet = db.execute("SELECT * FROM pets WHERE id=?", (pet_id,)).fetchone() if pet_id else None
        pet_name = pet["name"] if pet else request.form.get("pet_name", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()
        form = dict(pet_id=pet_id_raw, pet_name=pet_name, address=address, notes=notes)

        errors = []
        if not pet:
            errors.append("Choose a pet profile for this order.")
        if len(address) < 8:
            errors.append("Enter a complete delivery address.")
        if errors:
            for error in errors:
                flash(error, "warning")
            lines, subtotal = _cart_lines(db, cart)
            total = subtotal + DELIVERY_FEE_CENTS if lines else 0
            return render_template("cart.html", cart=cart, lines=lines, subtotal=subtotal,
                                   delivery_fee=DELIVERY_FEE_CENTS, total=total, form=form,
                                   active_pet=active_pet)

        lines, subtotal = _cart_lines(db, cart)
        if not lines:
            return redirect(url_for("order_browse"))

        total = subtotal + DELIVERY_FEE_CENTS
        cur = db.execute(
            "INSERT INTO orders (created_at, pet_id, kitchen_id, kitchen_name, items_json, "
            "subtotal_cents, delivery_fee_cents, total_cents, pet_name, address, notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), pet["id"], cart["kitchen_id"],
             cart["kitchen_name"], json.dumps(lines), subtotal, DELIVERY_FEE_CENTS,
             total, pet_name, address, notes))
        db.commit()
        order_id = cur.lastrowid
        session.pop("cart", None)
        return redirect(url_for("order_status_page", order_id=order_id))

    if not cart or not cart["items"]:
        return render_template("cart.html", cart=None, lines=[], subtotal=0,
                                delivery_fee=DELIVERY_FEE_CENTS, total=0, form=form,
                                active_pet=active_pet)

    lines, subtotal = _cart_lines(db, cart)
    total = subtotal + DELIVERY_FEE_CENTS
    return render_template("cart.html", cart=cart, lines=lines, subtotal=subtotal,
                            delivery_fee=DELIVERY_FEE_CENTS, total=total, form=form,
                            active_pet=active_pet)

@app.route("/cart/update", methods=["POST"])
def cart_update():
    cart = session.get("cart")
    if cart:
        item_id = str(int(request.form["item_id"]))
        qty = int(request.form.get("qty", 0))
        if qty <= 0:
            cart["items"].pop(item_id, None)
        else:
            cart["items"][item_id] = qty
        if cart["items"]:
            session["cart"] = cart
        else:
            session.pop("cart", None)
    return redirect(url_for("cart_view"))

@app.route("/cart/clear", methods=["POST"])
def cart_clear():
    session.pop("cart", None)
    return redirect(request.referrer or url_for("order_browse"))

ORDER_STAGES = ["Confirmed", "Preparing", "Out for delivery", "Delivered"]

def _order_progress(created_at_iso):
    elapsed = (datetime.now() - datetime.fromisoformat(created_at_iso)).total_seconds()
    if elapsed < 20:
        idx = 0
    elif elapsed < 70:
        idx = 1
    elif elapsed < 180:
        idx = 2
    else:
        idx = 3
    pct = min(100, int((idx + 1) / len(ORDER_STAGES) * 100))
    return idx, ORDER_STAGES[idx], pct

@app.route("/orders/<int:order_id>")
def order_status_page(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if order is None:
        abort(404)
    items = json.loads(order["items_json"])
    pet = db.execute("SELECT * FROM pets WHERE id=?", (order["pet_id"],)).fetchone() if order["pet_id"] else None
    idx, status, pct = _order_progress(order["created_at"])
    return render_template("order_status.html", order=order, items=items,
                            stages=ORDER_STAGES, stage_idx=idx, status=status, pct=pct,
                            pet=pet)

@app.route("/api/orders/<int:order_id>/status")
def api_order_status(order_id):
    db = get_db()
    order = db.execute("SELECT created_at FROM orders WHERE id=?", (order_id,)).fetchone()
    if order is None:
        abort(404)
    idx, status, pct = _order_progress(order["created_at"])
    return jsonify(stage_idx=idx, status=status, pct=pct)

@app.route("/vets")
def vets_browse():
    db = get_db()
    active_pet = get_selected_pet()
    species = request.args.get("species", active_pet["species"] if active_pet else "any")
    urgency = request.args.get("urgency", "any")

    vets = db.execute("SELECT * FROM vets ORDER BY distance_label").fetchall()

    now_iso = datetime.now().isoformat(timespec="minutes")
    vet_cards = []
    markers = []
    for v in vets:
        if species != "any" and species not in v["species"].split(","):
            continue
        if urgency != "any" and urgency not in v["urgency"].split(","):
            continue
        slots = db.execute(
            "SELECT * FROM vet_slots WHERE vet_id=? AND is_booked=0 AND slot_time>? "
            "ORDER BY slot_time LIMIT 2", (v["id"], now_iso)).fetchall()
        slot_count = db.execute(
            "SELECT COUNT(*) AS c FROM vet_slots WHERE vet_id=? AND is_booked=0 AND slot_time>?",
            (v["id"], now_iso)).fetchone()["c"]
        vet_cards.append(dict(vet=v, slots=slots, slot_count=slot_count))
        markers.append(dict(id=v["id"], name=v["name"], lat=v["lat"], lng=v["lng"],
                             distance=v["distance_label"]))

    return render_template("vets.html", vet_cards=vet_cards, markers_json=json.dumps(markers),
                            species=species, urgency=urgency, active_pet=active_pet)

@app.route("/vets/<int:vet_id>/book/<int:slot_id>", methods=["GET", "POST"])
def book_slot(vet_id, slot_id):
    db = get_db()
    active_pet = get_selected_pet()
    vet = db.execute("SELECT * FROM vets WHERE id=?", (vet_id,)).fetchone()
    slot = db.execute("SELECT * FROM vet_slots WHERE id=? AND vet_id=?",
                       (slot_id, vet_id)).fetchone()
    if vet is None or slot is None:
        abort(404)
    if slot["is_booked"]:
        flash("That slot was just booked by someone else — pick another.", "warning")
        return redirect(url_for("vets_browse"))
    form = dict(
        pet_id=str(active_pet["id"]) if active_pet else "",
        owner_name="",
        pet_name=active_pet["name"] if active_pet else "",
        species=active_pet["species"] if active_pet else "dog",
        reason="",
    )

    if request.method == "POST":
        pet_id_raw = request.form.get("pet_id", "").strip()
        pet_id = int(pet_id_raw) if pet_id_raw.isdigit() else None
        pet = db.execute("SELECT * FROM pets WHERE id=?", (pet_id,)).fetchone() if pet_id else None
        owner_name = request.form.get("owner_name", "").strip()
        pet_name = pet["name"] if pet else request.form.get("pet_name", "").strip()
        species = pet["species"] if pet else request.form.get("species", "").strip()
        reason = request.form.get("reason", "").strip()
        form = dict(pet_id=pet_id_raw, owner_name=owner_name, pet_name=pet_name,
                    species=species, reason=reason)

        errors = []
        if not pet:
            errors.append("Choose a pet profile for this appointment.")
        if len(owner_name) < 2:
            errors.append("Enter your name.")
        if errors:
            for error in errors:
                flash(error, "warning")
            return render_template("booking_form.html", vet=vet, slot=slot,
                                   form=form, active_pet=active_pet)

        db.execute("UPDATE vet_slots SET is_booked=1 WHERE id=?", (slot_id,))
        cur = db.execute(
            "INSERT INTO bookings (created_at, pet_id, vet_id, vet_name, slot_time, owner_name, "
            "pet_name, species, reason) VALUES (?,?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), pet["id"], vet_id, vet["name"],
             slot["slot_time"], owner_name, pet_name, species, reason))
        db.commit()
        return redirect(url_for("booking_confirmation", booking_id=cur.lastrowid))

    return render_template("booking_form.html", vet=vet, slot=slot,
                           form=form, active_pet=active_pet)

@app.route("/bookings/<int:booking_id>")
def booking_confirmation(booking_id):
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
    if booking is None:
        abort(404)
    pet = db.execute("SELECT * FROM pets WHERE id=?", (booking["pet_id"],)).fetchone() if booking["pet_id"] else None
    return render_template("booking_confirmation.html", booking=booking, pet=pet)

@app.route("/partners", methods=["GET", "POST"])
def partners():
    success = False
    if request.method == "POST":
        db = get_db()
        kind = request.form.get("kind", "kitchen")
        business_name = request.form.get("business_name", "").strip()
        contact_name = request.form.get("contact_name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if business_name and email:
            db.execute(
                "INSERT INTO partner_leads (created_at, kind, business_name, contact_name, "
                "email, message) VALUES (?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), kind, business_name,
                 contact_name, email, message))
            db.commit()
            success = True
        else:
            flash("Business name and email are required.", "warning")
    return render_template("partners.html", success=success)

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    orders = db.execute("""
        SELECT o.*, p.species AS pet_species FROM orders o
        LEFT JOIN pets p ON p.id = o.pet_id
        ORDER BY o.id DESC LIMIT 25
    """).fetchall()
    bookings = db.execute("""
        SELECT b.*, p.life_stage AS pet_life_stage FROM bookings b
        LEFT JOIN pets p ON p.id = b.pet_id
        ORDER BY b.id DESC LIMIT 25
    """).fetchall()
    leads = db.execute("SELECT * FROM partner_leads ORDER BY id DESC LIMIT 25").fetchall()
    return render_template("dashboard.html", orders=orders, bookings=bookings, leads=leads)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["admin_authenticated"] = True
            flash("Dashboard unlocked.", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("That password did not work.", "warning")
    return render_template("login.html")

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_authenticated", None)
    flash("Signed out of the dashboard.", "success")
    return redirect(url_for("home"))

@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, title="Page not found",
                           message="That page or record is not available anymore."), 404

@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html", code=500, title="Something went wrong",
                           message="Petsync hit a problem. Try again in a moment."), 500

init_db()
seed_db()
ensure_demo_pet()

if __name__ == "__main__":
    app.run(debug=True)
