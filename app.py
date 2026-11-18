import os
import sys
import io
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file)
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from db import get_db, init_db

load_dotenv()

# Configure template and static directories for normal Python vs. PyInstaller frozen EXE
if getattr(sys, "frozen", False):
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    template_folder = os.path.join(bundle_dir, "templates")
    static_folder = os.path.join(bundle_dir, "static")
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "siddhanth-firm-secret-key-2024")
bcrypt = Bcrypt(app)

# Jinja2 globals
app.jinja_env.globals.update(now=datetime.now)


# ─────────────────────────────────────────────
# DECORATORS
# ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_rates():
    conn = get_db()
    try:
        cur = conn.execute("SELECT metal, price_per_gram, updated_at FROM rates")
        rows = cur.fetchall()
        return {r["metal"]: r for r in rows}
    finally:
        conn.close()


def get_service_charges():
    conn = get_db()
    try:
        cur = conn.execute("SELECT service_type, default_rate, unit, description, updated_at FROM service_charges")
        rows = cur.fetchall()
        charges = {r["service_type"]: dict(r) for r in rows}
        if "gold_testing" not in charges:
            charges["gold_testing"] = {"default_rate": 100.0, "unit": "per item"}
        if "silver_testing" not in charges:
            charges["silver_testing"] = {"default_rate": 50.0, "unit": "per item"}
        return charges
    finally:
        conn.close()


def get_next_gold_receipt_no(conn):
    year = date.today().year
    row = conn.execute("""
        SELECT receipt_no FROM gold_tests 
        WHERE receipt_no LIKE ? ORDER BY id DESC LIMIT 1
    """, (f"GT-{year}-%",)).fetchone()
    if row and row["receipt_no"]:
        try:
            last_num = int(row["receipt_no"].split("-")[-1])
            return f"GT-{year}-{last_num + 1:04d}"
        except (ValueError, IndexError):
            pass
    # Fallback checking total count
    cnt = conn.execute("SELECT COUNT(*) as c FROM gold_tests").fetchone()["c"]
    return f"GT-{year}-{cnt + 1:04d}"


def get_next_silver_receipt_no(conn):
    year = date.today().year
    row = conn.execute("""
        SELECT receipt_no FROM silver_tests 
        WHERE receipt_no LIKE ? ORDER BY id DESC LIMIT 1
    """, (f"ST-{year}-%",)).fetchone()
    if row and row["receipt_no"]:
        try:
            last_num = int(row["receipt_no"].split("-")[-1])
            return f"ST-{year}-{last_num + 1:04d}"
        except (ValueError, IndexError):
            pass
    cnt = conn.execute("SELECT COUNT(*) as c FROM silver_tests").fetchone()["c"]
    return f"ST-{year}-{cnt + 1:04d}"


def seed_admin():
    """Create a default admin user if none exists."""
    conn = get_db()
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE role='admin'").fetchone()
        if row["cnt"] == 0:
            pw_hash = bcrypt.generate_password_hash("Admin@123").decode("utf-8")
            conn.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
                ("Admin", "admin@siddhanth.com", pw_hash, "admin")
            )
            conn.commit()
    finally:
        conn.close()


def seed_sample_testing_data():
    """Seed realistic sample data for Gold and Silver testing matching authentic certificates."""
    conn = get_db()
    try:
        admin_id = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
        user_id = admin_id["id"] if admin_id else 1
        today = date.today()
        today_str = today.isoformat()

        # Seed Gold Testing sample if table is empty
        gold_cnt = conn.execute("SELECT COUNT(*) as cnt FROM gold_tests").fetchone()["cnt"]
        if gold_cnt == 0:
            # Sample 1: Matching uploaded Gold Certificate (Serial 149, Party: Banshidhar Jewellers)
            cur = conn.execute("""
                INSERT INTO gold_tests 
                (receipt_no, customer_name, contact_no, address, test_date, subtotal, 
                 additional_charges, discount, grand_total, amount_received, balance_amount, 
                 payment_method, payment_status, testing_status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "GT-2026-0149", "Banshidhar Jewellers (बंशीधर ज्वैलर्स)", "7376226999", 
                "Cinema Road, Hardoi (सिनेमा रोड, हरदोई)", today_str, 200.0, 
                0.0, 0.0, 200.0, 200.0, 0.0, 
                "UPI", "Paid", "Completed", 
                "Computerized Assay Certificate · 100% Perfect Testing Report", user_id
            ))
            test1_id = cur.lastrowid
            # Item 1: Chasani sample (from image)
            conn.execute("""
                INSERT INTO gold_test_items 
                (test_id, item_name, gross_weight, net_weight, purity_karat, purity_percent, 
                 fine_gold_weight, testing_method, quantity, testing_charge, total_charge, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test1_id, "Gold Chasani Sample (चासनी सैंपल)", 17.830, 17.830, 19.58, 81.58, 
                14.546, "Computerized XRF Assay", 1, 100.0, 100.0, "All Metal assay · Chasani melting sample"
            ))
            # Item 2: Gold Chain
            conn.execute("""
                INSERT INTO gold_test_items 
                (test_id, item_name, gross_weight, net_weight, purity_karat, purity_percent, 
                 fine_gold_weight, testing_method, quantity, testing_charge, total_charge, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test1_id, "Gold Chain (सोने की चेन)", 12.450, 12.450, 22.00, 91.60, 
                11.404, "Computerized XRF Assay", 1, 100.0, 100.0, "916 Hallmark Purity check"
            ))

            # Sample 2: Kundan Ring & Coin
            cur2 = conn.execute("""
                INSERT INTO gold_tests 
                (receipt_no, customer_name, contact_no, address, test_date, subtotal, 
                 additional_charges, discount, grand_total, amount_received, balance_amount, 
                 payment_method, payment_status, testing_status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "GT-2026-0150", "Rajesh Kumar Verma", "9839123456", 
                "Railway Ganj, Hardoi", today_str, 150.0, 
                0.0, 0.0, 150.0, 150.0, 0.0, 
                "Cash", "Paid", "Completed", 
                "Purity certified for exchange", user_id
            ))
            test2_id = cur2.lastrowid
            conn.execute("""
                INSERT INTO gold_test_items 
                (test_id, item_name, gross_weight, net_weight, purity_karat, purity_percent, 
                 fine_gold_weight, testing_method, quantity, testing_charge, total_charge, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test2_id, "Gold Ring (अंगूठी)", 6.280, 5.800, 18.00, 75.00, 
                4.350, "Computerized XRF Assay", 1, 150.0, 150.0, "Stone weight deducted 0.480g"
            ))
            conn.commit()

        # Seed Silver Testing sample if table is empty
        silver_cnt = conn.execute("SELECT COUNT(*) as cnt FROM silver_tests").fetchone()["cnt"]
        if silver_cnt == 0:
            # Sample 1: Matching uploaded Silver Certificate (Serial 508, Party: Vaibhav Ji Jewellers)
            cur = conn.execute("""
                INSERT INTO silver_tests 
                (receipt_no, customer_name, contact_no, address, test_date, subtotal, 
                 additional_charges, discount, grand_total, amount_received, balance_amount, 
                 payment_method, payment_status, testing_status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "ST-2026-0508", "Vaibhav Ji Jewellers (वैभव जी)", "9936538678", 
                "Sarafa Bazaar, Hardoi (सराफा बाजार, हरदोई)", today_str, 100.0, 
                0.0, 0.0, 100.0, 100.0, 0.0, 
                "Cash", "Paid", "Completed", 
                "वैज्ञानिक विधि से चाँदी की शुद्धता परीक्षण · पाँडुरंग मुम्बई वाले", user_id
            ))
            stest1_id = cur.lastrowid
            # Item 1: Payal
            conn.execute("""
                INSERT INTO silver_test_items 
                (test_id, item_name, gross_weight, net_weight, purity_fineness, purity_percent, 
                 testing_method, quantity, testing_charge, total_charge, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stest1_id, "Silver Payal (चाँदी की पायल)", 65.400, 61.700, "61 | 70 (617.0 प्रति हजार)", 61.70, 
                "Computerized XRF Assay & Touch", 1, 50.0, 50.0, "चिन्ह [ 61 | 70 ] · घुंघरू वजन काट"
            ))
            # Item 2: Silver Chhalla & Coin
            conn.execute("""
                INSERT INTO silver_test_items 
                (test_id, item_name, gross_weight, net_weight, purity_fineness, purity_percent, 
                 testing_method, quantity, testing_charge, total_charge, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stest1_id, "Silver Coin & Chhalla (सिक्का व छल्ला)", 25.000, 25.000, "80 | 00 (800.0 प्रति हजार)", 80.00, 
                "Computerized XRF Assay & Touch", 1, 50.0, 50.0, "चिन्ह [ 80 | 00 ]"
            ))

            # Sample 2: Sterling Silver Bartan
            cur2 = conn.execute("""
                INSERT INTO silver_tests 
                (receipt_no, customer_name, contact_no, address, test_date, subtotal, 
                 additional_charges, discount, grand_total, amount_received, balance_amount, 
                 payment_method, payment_status, testing_status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "ST-2026-0509", "Shree Ram Jewellers", "9415098765", 
                "Ashraf Tola, Hardoi", today_str, 50.0, 
                0.0, 0.0, 50.0, 50.0, 0.0, 
                "UPI", "Paid", "Completed", 
                "Standard 925 Sterling certified", user_id
            ))
            stest2_id = cur2.lastrowid
            conn.execute("""
                INSERT INTO silver_test_items 
                (test_id, item_name, gross_weight, net_weight, purity_fineness, purity_percent, 
                 testing_method, quantity, testing_charge, total_charge, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stest2_id, "Silver Utensils / Thali (चाँदी की थाली)", 340.500, 340.500, "925 Sterling Silver (92.5%)", 92.50, 
                "Computerized XRF Assay", 1, 50.0, 50.0, "Hallmarked 925 testing"
            ))
            conn.commit()
    except Exception as e:
        print(f"[SEED WARNING] Seed sample testing data skipped: {e}")
    finally:
        conn.close()


# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────

with app.app_context():
    try:
        init_db()
        seed_admin()
        seed_sample_testing_data()
    except Exception as e:
        print(f"[STARTUP WARNING] DB init failed: {e}")


# ─────────────────────────────────────────────
# ROOT / HEALTH CHECK
# ─────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        try:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        finally:
            conn.close()
        if user and bcrypt.check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    today = date.today()
    today_str = today.isoformat()
    try:
        # Existing Polish & Jewelry revenues
        silver_rev  = conn.execute("SELECT COALESCE(SUM(total_amount),0) AS rev FROM silver_bills WHERE date=?", (today_str,)).fetchone()["rev"]
        gold_rev    = conn.execute("SELECT COALESCE(SUM(total_amount),0) AS rev FROM gold_bills WHERE date=?", (today_str,)).fetchone()["rev"]
        jewelry_rev = conn.execute("SELECT COALESCE(SUM(total_price),0) AS rev FROM jewelry_items WHERE date=?", (today_str,)).fetchone()["rev"]

        # Testing revenues
        gold_test_today_rev = conn.execute("SELECT COALESCE(SUM(grand_total),0) AS rev FROM gold_tests WHERE test_date=?", (today_str,)).fetchone()["rev"]
        silver_test_today_rev = conn.execute("SELECT COALESCE(SUM(grand_total),0) AS rev FROM silver_tests WHERE test_date=?", (today_str,)).fetchone()["rev"]

        gold_testing_today_rev = float(gold_test_today_rev)
        silver_testing_today_rev = float(silver_test_today_rev)

        today_revenue = float(silver_rev) + float(gold_rev) + float(jewelry_rev) + gold_testing_today_rev + silver_testing_today_rev

        # Existing Polish entry counts
        pending_silver = conn.execute("SELECT COUNT(*) AS cnt FROM silver_entries WHERE status='entry'").fetchone()["cnt"]
        pending_gold   = conn.execute("SELECT COUNT(*) AS cnt FROM gold_entries WHERE status='entry'").fetchone()["cnt"]
        silver_today   = conn.execute("SELECT COUNT(*) AS cnt FROM silver_entries WHERE date=?", (today_str,)).fetchone()["cnt"]
        gold_today     = conn.execute("SELECT COUNT(*) AS cnt FROM gold_entries WHERE date=?", (today_str,)).fetchone()["cnt"]

        # Gold Testing Counts & Revenue (All from real DB)
        gold_testing_today_cnt = conn.execute("SELECT COUNT(*) AS cnt FROM gold_tests WHERE test_date=?", (today_str,)).fetchone()["cnt"]
        gold_testing_total_cnt = conn.execute("SELECT COUNT(*) AS cnt FROM gold_tests").fetchone()["cnt"]
        gold_testing_total_rev = float(conn.execute("SELECT COALESCE(SUM(grand_total),0) AS rev FROM gold_tests").fetchone()["rev"])

        # Silver Testing Counts & Revenue (All from real DB)
        silver_testing_today_cnt = conn.execute("SELECT COUNT(*) AS cnt FROM silver_tests WHERE test_date=?", (today_str,)).fetchone()["cnt"]
        silver_testing_total_cnt = conn.execute("SELECT COUNT(*) AS cnt FROM silver_tests").fetchone()["cnt"]
        silver_testing_total_rev = float(conn.execute("SELECT COALESCE(SUM(grand_total),0) AS rev FROM silver_tests").fetchone()["rev"])

        # 7-day trend chart
        chart_labels = []
        chart_silver, chart_gold, chart_jewelry = [], [], []
        chart_gold_test, chart_silver_test = [], []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            d_str = d.isoformat()
            chart_labels.append(d.strftime("%d %b"))
            chart_silver.append(float(conn.execute("SELECT COALESCE(SUM(total_amount),0) AS r FROM silver_bills WHERE date=?", (d_str,)).fetchone()["r"]))
            chart_gold.append(float(conn.execute("SELECT COALESCE(SUM(total_amount),0) AS r FROM gold_bills WHERE date=?", (d_str,)).fetchone()["r"]))
            chart_jewelry.append(float(conn.execute("SELECT COALESCE(SUM(total_price),0) AS r FROM jewelry_items WHERE date=?", (d_str,)).fetchone()["r"]))
            chart_gold_test.append(float(conn.execute("SELECT COALESCE(SUM(grand_total),0) AS r FROM gold_tests WHERE test_date=?", (d_str,)).fetchone()["r"]))
            chart_silver_test.append(float(conn.execute("SELECT COALESCE(SUM(grand_total),0) AS r FROM silver_tests WHERE test_date=?", (d_str,)).fetchone()["r"]))

        # Recent activities
        recent_silver = conn.execute("""
            SELECT 'Silver' AS type, customer_name, date, silver_weight AS weight, total_amount, created_at
            FROM silver_bills ORDER BY created_at DESC LIMIT 5
        """).fetchall()
        recent_gold = conn.execute("""
            SELECT 'Gold' AS type, customer_name, date, gold_weight AS weight, total_amount, created_at
            FROM gold_bills ORDER BY created_at DESC LIMIT 5
        """).fetchall()

        recent_gold_tests = conn.execute("""
            SELECT t.id, t.receipt_no, t.customer_name, t.test_date, t.grand_total, t.created_at,
                   COUNT(i.id) AS item_count
            FROM gold_tests t
            LEFT JOIN gold_test_items i ON t.id = i.test_id
            GROUP BY t.id ORDER BY t.created_at DESC LIMIT 5
        """).fetchall()

        recent_silver_tests = conn.execute("""
            SELECT t.id, t.receipt_no, t.customer_name, t.test_date, t.grand_total, t.created_at,
                   COUNT(i.id) AS item_count
            FROM silver_tests t
            LEFT JOIN silver_test_items i ON t.id = i.test_id
            GROUP BY t.id ORDER BY t.created_at DESC LIMIT 5
        """).fetchall()

    finally:
        conn.close()

    return render_template("dashboard.html",
        today_revenue=today_revenue,
        pending_silver=pending_silver, pending_gold=pending_gold,
        silver_today=silver_today, gold_today=gold_today,
        gold_testing_today_cnt=gold_testing_today_cnt,
        gold_testing_total_cnt=gold_testing_total_cnt,
        gold_testing_today_rev=gold_testing_today_rev,
        gold_testing_total_rev=gold_testing_total_rev,
        silver_testing_today_cnt=silver_testing_today_cnt,
        silver_testing_total_cnt=silver_testing_total_cnt,
        silver_testing_today_rev=silver_testing_today_rev,
        silver_testing_total_rev=silver_testing_total_rev,
        chart_labels=chart_labels,
        chart_silver=chart_silver, chart_gold=chart_gold, chart_jewelry=chart_jewelry,
        chart_gold_test=chart_gold_test, chart_silver_test=chart_silver_test,
        recent_silver=recent_silver, recent_gold=recent_gold,
        recent_gold_tests=recent_gold_tests, recent_silver_tests=recent_silver_tests,
        today=today
    )


# ─────────────────────────────────────────────
# GOLD TESTING ROUTES
# ─────────────────────────────────────────────

@app.route("/gold-testing")
@login_required
def gold_testing_list():
    search = request.args.get("search", "").strip()
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()
    conn = get_db()
    today_str = date.today().isoformat()
    try:
        # Base query joining items to calculate summaries
        query = """
            SELECT t.*, 
                   COUNT(i.id) AS item_count, 
                   COALESCE(SUM(i.gross_weight), 0) AS total_weight,
                   COALESCE(AVG(i.purity_karat), 0) AS avg_karat,
                   COALESCE(AVG(i.purity_percent), 0) AS avg_percent,
                   u.name AS created_by_name
            FROM gold_tests t
            LEFT JOIN gold_test_items i ON t.id = i.test_id
            LEFT JOIN users u ON t.created_by = u.id
        """
        where_clauses = []
        params = []

        if search:
            q = f"%{search}%"
            where_clauses.append("(t.customer_name LIKE ? OR t.contact_no LIKE ? OR t.receipt_no LIKE ? OR t.address LIKE ?)")
            params.extend([q, q, q, q])
        if from_date:
            where_clauses.append("t.test_date >= ?")
            params.append(from_date)
        if to_date:
            where_clauses.append("t.test_date <= ?")
            params.append(to_date)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " GROUP BY t.id ORDER BY t.test_date DESC, t.created_at DESC"
        tests = conn.execute(query, params).fetchall()

        # Stats summary
        total_cnt = conn.execute("SELECT COUNT(*) AS c FROM gold_tests").fetchone()["c"]
        total_rev = conn.execute("SELECT COALESCE(SUM(grand_total), 0) AS r FROM gold_tests").fetchone()["r"]
        today_cnt = conn.execute("SELECT COUNT(*) AS c FROM gold_tests WHERE test_date = ?", (today_str,)).fetchone()["c"]
        today_rev = conn.execute("SELECT COALESCE(SUM(grand_total), 0) AS r FROM gold_tests WHERE test_date = ?", (today_str,)).fetchone()["r"]

        stats = {
            "total_count": total_cnt,
            "total_revenue": float(total_rev),
            "today_count": today_cnt,
            "today_revenue": float(today_rev)
        }
    finally:
        conn.close()

    return render_template("gold_testing/list.html", tests=tests, stats=stats, search=search, from_date=from_date, to_date=to_date)


@app.route("/gold-testing/new", methods=["GET", "POST"])
@login_required
def gold_testing_new():
    charges = get_service_charges()
    default_rate = float(charges.get("gold_testing", {}).get("default_rate", 100.0))

    if request.method == "POST":
        conn = get_db()
        try:
            receipt_no        = request.form.get("receipt_no", "").strip() or get_next_gold_receipt_no(conn)
            customer_name     = request.form.get("customer_name", "").strip()
            contact_no        = request.form.get("contact_no", "").strip()
            address           = request.form.get("address", "").strip()
            test_date         = request.form.get("test_date") or str(date.today())
            subtotal          = float(request.form.get("subtotal", 0))
            additional_charges = float(request.form.get("additional_charges", 0))
            discount          = float(request.form.get("discount", 0))
            grand_total       = float(request.form.get("grand_total", 0))
            amount_received   = float(request.form.get("amount_received", 0))
            balance_amount    = float(request.form.get("balance_amount", 0))
            payment_method    = request.form.get("payment_method", "Cash")
            testing_status    = request.form.get("testing_status", "Completed")
            notes             = request.form.get("notes", "").strip()

            # Determine payment status
            if balance_amount <= 0:
                payment_status = "Paid"
            elif amount_received > 0:
                payment_status = "Partial"
            else:
                payment_status = "Unpaid"

            # Item array form inputs
            item_names     = request.form.getlist("item_name[]")
            gross_weights  = request.form.getlist("gross_weight[]")
            net_weights    = request.form.getlist("net_weight[]")
            purity_karats  = request.form.getlist("purity_karat[]")
            purity_percents = request.form.getlist("purity_percent[]")
            fine_golds     = request.form.getlist("fine_gold_weight[]")
            methods        = request.form.getlist("testing_method[]")
            quantities     = request.form.getlist("quantity[]")
            rates          = request.form.getlist("testing_charge[]")
            totals         = request.form.getlist("total_charge[]")

            cur = conn.execute("""
                INSERT INTO gold_tests 
                (receipt_no, customer_name, contact_no, address, test_date, subtotal, 
                 additional_charges, discount, grand_total, amount_received, balance_amount, 
                 payment_method, payment_status, testing_status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (receipt_no, customer_name, contact_no, address, test_date, subtotal,
                  additional_charges, discount, grand_total, amount_received, balance_amount,
                  payment_method, payment_status, testing_status, notes, session["user_id"]))
            test_id = cur.lastrowid

            for i in range(len(item_names)):
                name = item_names[i].strip()
                if not name:
                    continue
                gross = float(gross_weights[i]) if i < len(gross_weights) and gross_weights[i] else 0.0
                net   = float(net_weights[i]) if i < len(net_weights) and net_weights[i] else gross
                karat = float(purity_karats[i]) if i < len(purity_karats) and purity_karats[i] else 0.0
                pct   = float(purity_percents[i]) if i < len(purity_percents) and purity_percents[i] else (karat / 24 * 100)
                fine  = float(fine_golds[i]) if i < len(fine_golds) and fine_golds[i] else (net * pct / 100)
                meth  = methods[i] if i < len(methods) else "Computerized XRF Assay"
                qty   = int(quantities[i]) if i < len(quantities) and quantities[i] else 1
                rate  = float(rates[i]) if i < len(rates) and rates[i] else default_rate
                tot   = float(totals[i]) if i < len(totals) and totals[i] else (qty * rate)

                conn.execute("""
                    INSERT INTO gold_test_items 
                    (test_id, item_name, gross_weight, net_weight, purity_karat, purity_percent, 
                     fine_gold_weight, testing_method, quantity, testing_charge, total_charge)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (test_id, name, gross, net, karat, pct, fine, meth, qty, rate, tot))

            conn.commit()
            flash(f"Gold Testing Receipt {receipt_no} generated successfully!", "success")
            return redirect(url_for("gold_testing_view", test_id=test_id))
        except Exception as e:
            conn.rollback()
            flash(f"Error saving gold test: {e}", "danger")
        finally:
            conn.close()

    conn = get_db()
    try:
        next_receipt_no = get_next_gold_receipt_no(conn)
    finally:
        conn.close()

    return render_template("gold_testing/entry.html", 
                           today=str(date.today()), 
                           next_receipt_no=next_receipt_no,
                           default_rate=default_rate)


@app.route("/gold-testing/<int:test_id>")
@login_required
def gold_testing_view(test_id):
    conn = get_db()
    try:
        test = conn.execute("SELECT * FROM gold_tests WHERE id = ?", (test_id,)).fetchone()
        if not test:
            flash("Gold testing record not found.", "danger")
            return redirect(url_for("gold_testing_list"))
        items = conn.execute("SELECT * FROM gold_test_items WHERE test_id = ? ORDER BY id", (test_id,)).fetchall()
    finally:
        conn.close()

    return render_template("gold_testing/bill_view.html", test=test, items=items)


@app.route("/gold-testing/<int:test_id>/pdf")
@login_required
def gold_testing_pdf(test_id):
    conn = get_db()
    try:
        test = conn.execute("SELECT * FROM gold_tests WHERE id = ?", (test_id,)).fetchone()
        if not test:
            flash("Record not found.", "danger")
            return redirect(url_for("gold_testing_list"))
        items = conn.execute("SELECT * FROM gold_test_items WHERE test_id = ? ORDER BY id", (test_id,)).fetchall()
    finally:
        conn.close()

    pdf_buffer = generate_gold_test_pdf(test, items)
    safe_name = "".join(c for c in test['customer_name'] if c.isalnum() or c in (' ', '_', '-')).strip()
    return send_file(pdf_buffer, mimetype="application/pdf",
                     as_attachment=True,
                     download_name=f"Gold_Assay_Bill_{test['receipt_no']}_{safe_name}.pdf")


@app.route("/gold-testing/sample")
@login_required
def gold_testing_sample():
    """View the realistic Gold Testing sample bill template."""
    conn = get_db()
    try:
        sample = conn.execute("SELECT * FROM gold_tests ORDER BY id ASC LIMIT 1").fetchone()
        if not sample:
            seed_sample_testing_data()
            sample = conn.execute("SELECT * FROM gold_tests ORDER BY id ASC LIMIT 1").fetchone()
        items = conn.execute("SELECT * FROM gold_test_items WHERE test_id = ? ORDER BY id", (sample["id"],)).fetchall()
    finally:
        conn.close()
    return render_template("gold_testing/bill_view.html", test=sample, items=items, is_sample=True)


@app.route("/gold-testing/<int:test_id>/delete", methods=["POST"])
@admin_required
def gold_testing_delete(test_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM gold_tests WHERE id = ?", (test_id,))
        conn.commit()
    finally:
        conn.close()
    flash("Gold testing record deleted.", "warning")
    return redirect(url_for("gold_testing_list"))


# ─────────────────────────────────────────────
# SILVER TESTING ROUTES
# ─────────────────────────────────────────────

@app.route("/silver-testing")
@login_required
def silver_testing_list():
    search = request.args.get("search", "").strip()
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()
    conn = get_db()
    today_str = date.today().isoformat()
    try:
        query = """
            SELECT t.*, 
                   COUNT(i.id) AS item_count, 
                   COALESCE(SUM(i.gross_weight), 0) AS total_weight,
                   COALESCE(MAX(i.purity_fineness), '—') AS sample_fineness,
                   u.name AS created_by_name
            FROM silver_tests t
            LEFT JOIN silver_test_items i ON t.id = i.test_id
            LEFT JOIN users u ON t.created_by = u.id
        """
        where_clauses = []
        params = []

        if search:
            q = f"%{search}%"
            where_clauses.append("(t.customer_name LIKE ? OR t.contact_no LIKE ? OR t.receipt_no LIKE ? OR t.address LIKE ?)")
            params.extend([q, q, q, q])
        if from_date:
            where_clauses.append("t.test_date >= ?")
            params.append(from_date)
        if to_date:
            where_clauses.append("t.test_date <= ?")
            params.append(to_date)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " GROUP BY t.id ORDER BY t.test_date DESC, t.created_at DESC"
        tests = conn.execute(query, params).fetchall()

        total_cnt = conn.execute("SELECT COUNT(*) AS c FROM silver_tests").fetchone()["c"]
        total_rev = conn.execute("SELECT COALESCE(SUM(grand_total), 0) AS r FROM silver_tests").fetchone()["r"]
        today_cnt = conn.execute("SELECT COUNT(*) AS c FROM silver_tests WHERE test_date = ?", (today_str,)).fetchone()["c"]
        today_rev = conn.execute("SELECT COALESCE(SUM(grand_total), 0) AS r FROM silver_tests WHERE test_date = ?", (today_str,)).fetchone()["r"]

        stats = {
            "total_count": total_cnt,
            "total_revenue": float(total_rev),
            "today_count": today_cnt,
            "today_revenue": float(today_rev)
        }
    finally:
        conn.close()

    return render_template("silver_testing/list.html", tests=tests, stats=stats, search=search, from_date=from_date, to_date=to_date)


@app.route("/silver-testing/new", methods=["GET", "POST"])
@login_required
def silver_testing_new():
    charges = get_service_charges()
    default_rate = float(charges.get("silver_testing", {}).get("default_rate", 50.0))

    if request.method == "POST":
        conn = get_db()
        try:
            receipt_no        = request.form.get("receipt_no", "").strip() or get_next_silver_receipt_no(conn)
            customer_name     = request.form.get("customer_name", "").strip()
            contact_no        = request.form.get("contact_no", "").strip()
            address           = request.form.get("address", "").strip()
            test_date         = request.form.get("test_date") or str(date.today())
            subtotal          = float(request.form.get("subtotal", 0))
            additional_charges = float(request.form.get("additional_charges", 0))
            discount          = float(request.form.get("discount", 0))
            grand_total       = float(request.form.get("grand_total", 0))
            amount_received   = float(request.form.get("amount_received", 0))
            balance_amount    = float(request.form.get("balance_amount", 0))
            payment_method    = request.form.get("payment_method", "Cash")
            testing_status    = request.form.get("testing_status", "Completed")
            notes             = request.form.get("notes", "").strip()

            if balance_amount <= 0:
                payment_status = "Paid"
            elif amount_received > 0:
                payment_status = "Partial"
            else:
                payment_status = "Unpaid"

            item_names       = request.form.getlist("item_name[]")
            gross_weights    = request.form.getlist("gross_weight[]")
            net_weights      = request.form.getlist("net_weight[]")
            purity_finenesses = request.form.getlist("purity_fineness[]")
            purity_percents  = request.form.getlist("purity_percent[]")
            methods          = request.form.getlist("testing_method[]")
            quantities       = request.form.getlist("quantity[]")
            rates            = request.form.getlist("testing_charge[]")
            totals           = request.form.getlist("total_charge[]")

            cur = conn.execute("""
                INSERT INTO silver_tests 
                (receipt_no, customer_name, contact_no, address, test_date, subtotal, 
                 additional_charges, discount, grand_total, amount_received, balance_amount, 
                 payment_method, payment_status, testing_status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (receipt_no, customer_name, contact_no, address, test_date, subtotal,
                  additional_charges, discount, grand_total, amount_received, balance_amount,
                  payment_method, payment_status, testing_status, notes, session["user_id"]))
            test_id = cur.lastrowid

            for i in range(len(item_names)):
                name = item_names[i].strip()
                if not name:
                    continue
                gross = float(gross_weights[i]) if i < len(gross_weights) and gross_weights[i] else 0.0
                net   = float(net_weights[i]) if i < len(net_weights) and net_weights[i] else gross
                fine  = purity_finenesses[i].strip() if i < len(purity_finenesses) else "925"
                pct   = float(purity_percents[i]) if i < len(purity_percents) and purity_percents[i] else 0.0
                meth  = methods[i] if i < len(methods) else "Computerized XRF Assay"
                qty   = int(quantities[i]) if i < len(quantities) and quantities[i] else 1
                rate  = float(rates[i]) if i < len(rates) and rates[i] else default_rate
                tot   = float(totals[i]) if i < len(totals) and totals[i] else (qty * rate)

                conn.execute("""
                    INSERT INTO silver_test_items 
                    (test_id, item_name, gross_weight, net_weight, purity_fineness, purity_percent, 
                     testing_method, quantity, testing_charge, total_charge)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (test_id, name, gross, net, fine, pct, meth, qty, rate, tot))

            conn.commit()
            flash(f"Silver Testing Receipt {receipt_no} generated successfully!", "success")
            return redirect(url_for("silver_testing_view", test_id=test_id))
        except Exception as e:
            conn.rollback()
            flash(f"Error saving silver test: {e}", "danger")
        finally:
            conn.close()

    conn = get_db()
    try:
        next_receipt_no = get_next_silver_receipt_no(conn)
    finally:
        conn.close()

    return render_template("silver_testing/entry.html", 
                           today=str(date.today()), 
                           next_receipt_no=next_receipt_no,
                           default_rate=default_rate)


@app.route("/silver-testing/<int:test_id>")
@login_required
def silver_testing_view(test_id):
    conn = get_db()
    try:
        test = conn.execute("SELECT * FROM silver_tests WHERE id = ?", (test_id,)).fetchone()
        if not test:
            flash("Silver testing record not found.", "danger")
            return redirect(url_for("silver_testing_list"))
        items = conn.execute("SELECT * FROM silver_test_items WHERE test_id = ? ORDER BY id", (test_id,)).fetchall()
    finally:
        conn.close()

    return render_template("silver_testing/bill_view.html", test=test, items=items)


@app.route("/silver-testing/<int:test_id>/pdf")
@login_required
def silver_testing_pdf(test_id):
    conn = get_db()
    try:
        test = conn.execute("SELECT * FROM silver_tests WHERE id = ?", (test_id,)).fetchone()
        if not test:
            flash("Record not found.", "danger")
            return redirect(url_for("silver_testing_list"))
        items = conn.execute("SELECT * FROM silver_test_items WHERE test_id = ? ORDER BY id", (test_id,)).fetchall()
    finally:
        conn.close()

    pdf_buffer = generate_silver_test_pdf(test, items)
    safe_name = "".join(c for c in test['customer_name'] if c.isalnum() or c in (' ', '_', '-')).strip()
    return send_file(pdf_buffer, mimetype="application/pdf",
                     as_attachment=True,
                     download_name=f"Silver_Assay_Bill_{test['receipt_no']}_{safe_name}.pdf")


@app.route("/silver-testing/sample")
@login_required
def silver_testing_sample():
    """View the realistic Silver Testing sample bill template."""
    conn = get_db()
    try:
        sample = conn.execute("SELECT * FROM silver_tests ORDER BY id ASC LIMIT 1").fetchone()
        if not sample:
            seed_sample_testing_data()
            sample = conn.execute("SELECT * FROM silver_tests ORDER BY id ASC LIMIT 1").fetchone()
        items = conn.execute("SELECT * FROM silver_test_items WHERE test_id = ? ORDER BY id", (sample["id"],)).fetchall()
    finally:
        conn.close()
    return render_template("silver_testing/bill_view.html", test=sample, items=items, is_sample=True)


@app.route("/silver-testing/<int:test_id>/delete", methods=["POST"])
@admin_required
def silver_testing_delete(test_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM silver_tests WHERE id = ?", (test_id,))
        conn.commit()
    finally:
        conn.close()
    flash("Silver testing record deleted.", "warning")
    return redirect(url_for("silver_testing_list"))


# ─────────────────────────────────────────────
# SILVER POLISH ROUTES
# ─────────────────────────────────────────────

@app.route("/silver")
@login_required
def silver_list():
    search = request.args.get("search", "").strip()
    conn = get_db()
    try:
        if search:
            q = f"%{search}%"
            entries = conn.execute("""
                SELECT e.*, u.name AS created_by_name FROM silver_entries e
                LEFT JOIN users u ON e.created_by = u.id
                WHERE e.customer_name LIKE ? OR e.contact_no LIKE ?
                ORDER BY e.date DESC, e.created_at DESC
            """, (q, q)).fetchall()
        else:
            entries = conn.execute("""
                SELECT e.*, u.name AS created_by_name FROM silver_entries e
                LEFT JOIN users u ON e.created_by = u.id
                ORDER BY e.date DESC, e.created_at DESC LIMIT 100
            """).fetchall()
    finally:
        conn.close()
    return render_template("silver/list.html", entries=entries, search=search)


@app.route("/silver/entry", methods=["GET", "POST"])
@login_required
def silver_entry():
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        entry_date    = request.form.get("date") or str(date.today())
        silver_weight = request.form.get("silver_weight")
        polish_type   = request.form.get("polish_type", "without_p")
        contact_no    = request.form.get("contact_no", "").strip()
        status        = request.form.get("status", "entry")
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO silver_entries
                (customer_name, date, silver_weight, polish_type, contact_no, status, created_by)
                VALUES (?,?,?,?,?,?,?)
            """, (customer_name, entry_date, silver_weight, polish_type, contact_no, status, session["user_id"]))
            conn.commit()
        finally:
            conn.close()
        flash("Silver entry added successfully!", "success")
        return redirect(url_for("silver_list"))
    return render_template("silver/entry.html", today=str(date.today()))


@app.route("/silver/entry/<int:entry_id>/status", methods=["POST"])
@login_required
def silver_update_status(entry_id):
    new_status = request.form.get("status")
    conn = get_db()
    try:
        conn.execute("UPDATE silver_entries SET status=? WHERE id=?", (new_status, entry_id))
        conn.commit()
    finally:
        conn.close()
    flash("Status updated.", "success")
    return redirect(url_for("silver_list"))


@app.route("/silver/entry/<int:entry_id>/delete", methods=["POST"])
@admin_required
def silver_delete_entry(entry_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM silver_entries WHERE id=?", (entry_id,))
        conn.commit()
    finally:
        conn.close()
    flash("Entry deleted.", "warning")
    return redirect(url_for("silver_list"))


@app.route("/silver/bill", methods=["GET", "POST"])
@login_required
def silver_bill():
    rates = get_rates()
    rate_dict = {k: v["price_per_gram"] for k, v in rates.items()}
    if request.method == "POST":
        customer_name   = request.form.get("customer_name", "").strip()
        bill_date       = request.form.get("date") or str(date.today())
        silver_weight   = float(request.form.get("silver_weight", 0))
        silver_price    = float(request.form.get("silver_price", 0))
        waste           = float(request.form.get("waste", 0))
        extra_weight    = float(request.form.get("extra_weight", 0))
        silver_gram     = float(request.form.get("silver_gram", 0))
        silver_gram_price = float(request.form.get("silver_gram_price", 0))
        contact_no      = request.form.get("contact_no", "").strip()
        entry_id        = request.form.get("entry_id") or None

        total_amount = (silver_weight * silver_price) - waste + extra_weight + (silver_gram * silver_gram_price)

        conn = get_db()
        try:
            cur = conn.execute("""
                INSERT INTO silver_bills
                (customer_name, date, silver_weight, silver_price, waste, extra_weight,
                 silver_gram, silver_gram_price, total_amount, contact_no, entry_id, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (customer_name, bill_date, silver_weight, silver_price, waste, extra_weight,
                  silver_gram, silver_gram_price, total_amount, contact_no, entry_id, session["user_id"]))
            bill_id = cur.lastrowid
            if entry_id:
                conn.execute("UPDATE silver_entries SET status='exit' WHERE id=?", (entry_id,))
            conn.commit()
        finally:
            conn.close()
        flash("Silver bill generated!", "success")
        return redirect(url_for("silver_bill_view", bill_id=bill_id))

    conn = get_db()
    try:
        open_entries = conn.execute(
            "SELECT id, customer_name, silver_weight, contact_no FROM silver_entries WHERE status='entry' ORDER BY date DESC"
        ).fetchall()
    finally:
        conn.close()
    return render_template("silver/bill.html", rates=rate_dict, open_entries=open_entries, today=str(date.today()))


@app.route("/silver/bill/<int:bill_id>")
@login_required
def silver_bill_view(bill_id):
    conn = get_db()
    try:
        bill = conn.execute("SELECT * FROM silver_bills WHERE id=?", (bill_id,)).fetchone()
    finally:
        conn.close()
    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("silver_list"))
    return render_template("silver/bill_view.html", bill=bill)


@app.route("/silver/bills")
@login_required
def silver_bills_list():
    search = request.args.get("search", "").strip()
    conn = get_db()
    try:
        if search:
            q = f"%{search}%"
            bills = conn.execute("""
                SELECT * FROM silver_bills WHERE customer_name LIKE ? OR contact_no LIKE ?
                ORDER BY date DESC LIMIT 100
            """, (q, q)).fetchall()
        else:
            bills = conn.execute("SELECT * FROM silver_bills ORDER BY date DESC LIMIT 100").fetchall()
    finally:
        conn.close()
    return render_template("silver/bills_list.html", bills=bills, search=search)


@app.route("/silver/bill/<int:bill_id>/pdf")
@login_required
def silver_bill_pdf(bill_id):
    conn = get_db()
    try:
        bill = conn.execute("SELECT * FROM silver_bills WHERE id=?", (bill_id,)).fetchone()
    finally:
        conn.close()
    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("silver_list"))
    pdf_buffer = generate_silver_pdf(bill)
    return send_file(pdf_buffer, mimetype="application/pdf",
                     as_attachment=True,
                     download_name=f"silver_bill_{bill_id}_{bill['customer_name']}.pdf")


@app.route("/silver/bill/<int:bill_id>/delete", methods=["POST"])
@admin_required
def silver_bill_delete(bill_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM silver_bills WHERE id=?", (bill_id,))
        conn.commit()
    finally:
        conn.close()
    flash("Bill deleted.", "warning")
    return redirect(url_for("silver_bills_list"))


# ─────────────────────────────────────────────
# GOLD POLISH ROUTES
# ─────────────────────────────────────────────

@app.route("/gold")
@login_required
def gold_list():
    search = request.args.get("search", "").strip()
    conn = get_db()
    try:
        if search:
            q = f"%{search}%"
            entries = conn.execute("""
                SELECT e.*, u.name AS created_by_name FROM gold_entries e
                LEFT JOIN users u ON e.created_by = u.id
                WHERE e.customer_name LIKE ? OR e.contact_no LIKE ?
                ORDER BY e.date DESC, e.created_at DESC
            """, (q, q)).fetchall()
        else:
            entries = conn.execute("""
                SELECT e.*, u.name AS created_by_name FROM gold_entries e
                LEFT JOIN users u ON e.created_by = u.id
                ORDER BY e.date DESC, e.created_at DESC LIMIT 100
            """).fetchall()
    finally:
        conn.close()
    return render_template("gold/list.html", entries=entries, search=search)


@app.route("/gold/entry", methods=["GET", "POST"])
@login_required
def gold_entry():
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        entry_date    = request.form.get("date") or str(date.today())
        gold_weight   = request.form.get("gold_weight")
        polish_type   = request.form.get("polish_type", "without_p")
        contact_no    = request.form.get("contact_no", "").strip()
        status        = request.form.get("status", "entry")
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO gold_entries
                (customer_name, date, gold_weight, polish_type, contact_no, status, created_by)
                VALUES (?,?,?,?,?,?,?)
            """, (customer_name, entry_date, gold_weight, polish_type, contact_no, status, session["user_id"]))
            conn.commit()
        finally:
            conn.close()
        flash("Gold entry added successfully!", "success")
        return redirect(url_for("gold_list"))
    return render_template("gold/entry.html", today=str(date.today()))


@app.route("/gold/entry/<int:entry_id>/status", methods=["POST"])
@login_required
def gold_update_status(entry_id):
    new_status = request.form.get("status")
    conn = get_db()
    try:
        conn.execute("UPDATE gold_entries SET status=? WHERE id=?", (new_status, entry_id))
        conn.commit()
    finally:
        conn.close()
    flash("Status updated.", "success")
    return redirect(url_for("gold_list"))


@app.route("/gold/entry/<int:entry_id>/delete", methods=["POST"])
@admin_required
def gold_delete_entry(entry_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM gold_entries WHERE id=?", (entry_id,))
        conn.commit()
    finally:
        conn.close()
    flash("Entry deleted.", "warning")
    return redirect(url_for("gold_list"))


@app.route("/gold/bill", methods=["GET", "POST"])
@login_required
def gold_bill():
    rates = get_rates()
    rate_dict = {k: v["price_per_gram"] for k, v in rates.items()}
    if request.method == "POST":
        customer_name  = request.form.get("customer_name", "").strip()
        bill_date      = request.form.get("date") or str(date.today())
        gold_weight    = float(request.form.get("gold_weight", 0))
        gold_price     = float(request.form.get("gold_price", 0))
        gold_gram      = float(request.form.get("gold_gram", 0))
        gold_gram_price = float(request.form.get("gold_gram_price", 0))
        contact_no     = request.form.get("contact_no", "").strip()
        entry_id       = request.form.get("entry_id") or None

        total_amount = (gold_weight * gold_price) + (gold_gram * gold_gram_price)

        conn = get_db()
        try:
            cur = conn.execute("""
                INSERT INTO gold_bills
                (customer_name, date, gold_weight, gold_price, gold_gram, gold_gram_price,
                 total_amount, contact_no, entry_id, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (customer_name, bill_date, gold_weight, gold_price, gold_gram, gold_gram_price,
                  total_amount, contact_no, entry_id, session["user_id"]))
            bill_id = cur.lastrowid
            if entry_id:
                conn.execute("UPDATE gold_entries SET status='exit' WHERE id=?", (entry_id,))
            conn.commit()
        finally:
            conn.close()
        flash("Gold bill generated!", "success")
        return redirect(url_for("gold_bill_view", bill_id=bill_id))

    conn = get_db()
    try:
        open_entries = conn.execute(
            "SELECT id, customer_name, gold_weight, contact_no FROM gold_entries WHERE status='entry' ORDER BY date DESC"
        ).fetchall()
    finally:
        conn.close()
    return render_template("gold/bill.html", rates=rate_dict, open_entries=open_entries, today=str(date.today()))


@app.route("/gold/bill/<int:bill_id>")
@login_required
def gold_bill_view(bill_id):
    conn = get_db()
    try:
        bill = conn.execute("SELECT * FROM gold_bills WHERE id=?", (bill_id,)).fetchone()
    finally:
        conn.close()
    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("gold_list"))
    return render_template("gold/bill_view.html", bill=bill)


@app.route("/gold/bills")
@login_required
def gold_bills_list():
    search = request.args.get("search", "").strip()
    conn = get_db()
    try:
        if search:
            q = f"%{search}%"
            bills = conn.execute("""
                SELECT * FROM gold_bills WHERE customer_name LIKE ? OR contact_no LIKE ?
                ORDER BY date DESC LIMIT 100
            """, (q, q)).fetchall()
        else:
            bills = conn.execute("SELECT * FROM gold_bills ORDER BY date DESC LIMIT 100").fetchall()
    finally:
        conn.close()
    return render_template("gold/bills_list.html", bills=bills, search=search)


@app.route("/gold/bill/<int:bill_id>/pdf")
@login_required
def gold_bill_pdf(bill_id):
    conn = get_db()
    try:
        bill = conn.execute("SELECT * FROM gold_bills WHERE id=?", (bill_id,)).fetchone()
    finally:
        conn.close()
    if not bill:
        flash("Bill not found.", "danger")
        return redirect(url_for("gold_list"))
    pdf_buffer = generate_gold_pdf(bill)
    return send_file(pdf_buffer, mimetype="application/pdf",
                     as_attachment=True,
                     download_name=f"gold_bill_{bill_id}_{bill['customer_name']}.pdf")


@app.route("/gold/bill/<int:bill_id>/delete", methods=["POST"])
@admin_required
def gold_bill_delete(bill_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM gold_bills WHERE id=?", (bill_id,))
        conn.commit()
    finally:
        conn.close()
    flash("Bill deleted.", "warning")
    return redirect(url_for("gold_bills_list"))


# ─────────────────────────────────────────────
# JEWELRY BOX ROUTES
# ─────────────────────────────────────────────

@app.route("/jewelry")
@login_required
def jewelry_list():
    search = request.args.get("search", "").strip()
    conn = get_db()
    try:
        if search:
            q = f"%{search}%"
            items = conn.execute("""
                SELECT j.*, u.name AS created_by_name FROM jewelry_items j
                LEFT JOIN users u ON j.created_by = u.id
                WHERE j.customer_name LIKE ? OR j.item_name LIKE ?
                ORDER BY j.date DESC LIMIT 100
            """, (q, q)).fetchall()
        else:
            items = conn.execute("""
                SELECT j.*, u.name AS created_by_name FROM jewelry_items j
                LEFT JOIN users u ON j.created_by = u.id
                ORDER BY j.date DESC LIMIT 100
            """).fetchall()
    finally:
        conn.close()
    return render_template("jewelry/list.html", items=items, search=search)


@app.route("/jewelry/add", methods=["GET", "POST"])
@login_required
def jewelry_add():
    if request.method == "POST":
        item_name     = request.form.get("item_name", "").strip()
        category      = request.form.get("category", "").strip()
        rate          = float(request.form.get("rate", 0))
        quantity      = int(request.form.get("quantity", 1))
        customer_name = request.form.get("customer_name", "").strip()
        item_date     = request.form.get("date") or str(date.today())
        total_price   = rate * quantity
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO jewelry_items
                (item_name, category, rate, quantity, total_price, customer_name, date, created_by)
                VALUES (?,?,?,?,?,?,?,?)
            """, (item_name, category, rate, quantity, total_price, customer_name, item_date, session["user_id"]))
            conn.commit()
        finally:
            conn.close()
        flash("Jewelry item added!", "success")
        return redirect(url_for("jewelry_list"))
    return render_template("jewelry/add.html", today=str(date.today()))


@app.route("/jewelry/<int:item_id>/delete", methods=["POST"])
@admin_required
def jewelry_delete(item_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM jewelry_items WHERE id=?", (item_id,))
        conn.commit()
    finally:
        conn.close()
    flash("Item deleted.", "warning")
    return redirect(url_for("jewelry_list"))


# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────

@app.route("/reports")
@login_required
def reports():
    report_type = request.args.get("type", "daily")
    sel_date    = request.args.get("date", str(date.today()))
    conn = get_db()
    try:
        if report_type == "daily":
            silver_summary = conn.execute(
                "SELECT COALESCE(SUM(total_amount),0) AS total, COUNT(*) AS cnt FROM silver_bills WHERE date=?", (sel_date,)
            ).fetchone()
            gold_summary = conn.execute(
                "SELECT COALESCE(SUM(total_amount),0) AS total, COUNT(*) AS cnt FROM gold_bills WHERE date=?", (sel_date,)
            ).fetchone()
            jewelry_summary = conn.execute(
                "SELECT COALESCE(SUM(total_price),0) AS total, COUNT(*) AS cnt FROM jewelry_items WHERE date=?", (sel_date,)
            ).fetchone()
            gold_test_summary = conn.execute(
                "SELECT COALESCE(SUM(grand_total),0) AS total, COUNT(*) AS cnt FROM gold_tests WHERE test_date=?", (sel_date,)
            ).fetchone()
            silver_test_summary = conn.execute(
                "SELECT COALESCE(SUM(grand_total),0) AS total, COUNT(*) AS cnt FROM silver_tests WHERE test_date=?", (sel_date,)
            ).fetchone()

            silver_records = conn.execute(
                "SELECT customer_name, silver_weight, total_amount FROM silver_bills WHERE date=? ORDER BY created_at", (sel_date,)
            ).fetchall()
            gold_records = conn.execute(
                "SELECT customer_name, gold_weight, total_amount FROM gold_bills WHERE date=? ORDER BY created_at", (sel_date,)
            ).fetchall()

            chart_labels = [r["customer_name"] for r in silver_records]
            chart_data   = [float(r["total_amount"]) for r in silver_records]
            gold_chart_labels = [r["customer_name"] for r in gold_records]
            gold_chart_data   = [float(r["total_amount"]) for r in gold_records]
        else:
            start = (date.today() - timedelta(days=29)).isoformat()
            chart_labels, chart_data, gold_chart_data = [], [], []
            for i in range(29, -1, -1):
                d = date.today() - timedelta(days=i)
                d_str = d.isoformat()
                chart_labels.append(d.strftime("%d %b"))
                sv = float(conn.execute("SELECT COALESCE(SUM(total_amount),0) AS r FROM silver_bills WHERE date=?", (d_str,)).fetchone()["r"])
                gv = float(conn.execute("SELECT COALESCE(SUM(total_amount),0) AS r FROM gold_bills WHERE date=?", (d_str,)).fetchone()["r"])
                jv = float(conn.execute("SELECT COALESCE(SUM(total_price),0) AS r FROM jewelry_items WHERE date=?", (d_str,)).fetchone()["r"])
                gt = float(conn.execute("SELECT COALESCE(SUM(grand_total),0) AS r FROM gold_tests WHERE test_date=?", (d_str,)).fetchone()["r"])
                st = float(conn.execute("SELECT COALESCE(SUM(grand_total),0) AS r FROM silver_tests WHERE test_date=?", (d_str,)).fetchone()["r"])
                chart_data.append(sv + gv + jv + gt + st)
                gold_chart_data.append(gv + gt)
            gold_chart_labels = chart_labels

            silver_summary  = conn.execute("SELECT COALESCE(SUM(total_amount),0) AS total, COUNT(*) AS cnt FROM silver_bills WHERE date >= ?", (start,)).fetchone()
            gold_summary    = conn.execute("SELECT COALESCE(SUM(total_amount),0) AS total, COUNT(*) AS cnt FROM gold_bills WHERE date >= ?", (start,)).fetchone()
            jewelry_summary = conn.execute("SELECT COALESCE(SUM(total_price),0) AS total, COUNT(*) AS cnt FROM jewelry_items WHERE date >= ?", (start,)).fetchone()
            gold_test_summary = conn.execute("SELECT COALESCE(SUM(grand_total),0) AS total, COUNT(*) AS cnt FROM gold_tests WHERE test_date >= ?", (start,)).fetchone()
            silver_test_summary = conn.execute("SELECT COALESCE(SUM(grand_total),0) AS total, COUNT(*) AS cnt FROM silver_tests WHERE test_date >= ?", (start,)).fetchone()
            silver_records = []
            gold_records   = []
    finally:
        conn.close()

    total_rev = (float(silver_summary["total"]) + float(gold_summary["total"]) + 
                 float(jewelry_summary["total"]) + float(gold_test_summary["total"]) + 
                 float(silver_test_summary["total"]))

    return render_template("reports.html",
        report_type=report_type, sel_date=sel_date,
        silver_summary=silver_summary, gold_summary=gold_summary, jewelry_summary=jewelry_summary,
        gold_test_summary=gold_test_summary, silver_test_summary=silver_test_summary,
        total_rev=total_rev,
        silver_records=silver_records, gold_records=gold_records,
        chart_labels=chart_labels, chart_data=chart_data,
        gold_chart_labels=gold_chart_labels, gold_chart_data=gold_chart_data
    )


# ─────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────

@app.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    conn = get_db()
    try:
        if request.method == "POST":
            action = request.form.get("action")

            if action == "update_rates":
                silver_rate = request.form.get("silver_rate")
                gold_rate   = request.form.get("gold_rate")
                conn.execute("UPDATE rates SET price_per_gram=?, updated_at=datetime('now') WHERE metal='silver'", (silver_rate,))
                conn.execute("UPDATE rates SET price_per_gram=?, updated_at=datetime('now') WHERE metal='gold'", (gold_rate,))
                conn.commit()
                flash("Metal rates updated successfully!", "success")

            elif action == "update_testing_charges":
                gold_rate   = float(request.form.get("gold_test_rate", 100))
                silver_rate = float(request.form.get("silver_test_rate", 50))
                conn.execute("""
                    INSERT INTO service_charges (service_type, default_rate, updated_at) 
                    VALUES ('gold_testing', ?, datetime('now'))
                    ON CONFLICT(service_type) DO UPDATE SET default_rate=excluded.default_rate, updated_at=datetime('now')
                """, (gold_rate,))
                conn.execute("""
                    INSERT INTO service_charges (service_type, default_rate, updated_at) 
                    VALUES ('silver_testing', ?, datetime('now'))
                    ON CONFLICT(service_type) DO UPDATE SET default_rate=excluded.default_rate, updated_at=datetime('now')
                """, (silver_rate,))
                conn.commit()
                flash("Testing service charges updated successfully!", "success")

            elif action == "add_user":
                name     = request.form.get("new_name", "").strip()
                email    = request.form.get("new_email", "").strip().lower()
                password = request.form.get("new_password", "")
                role     = request.form.get("new_role", "user")
                pw_hash  = bcrypt.generate_password_hash(password).decode("utf-8")
                try:
                    conn.execute(
                        "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
                        (name, email, pw_hash, role)
                    )
                    conn.commit()
                    flash(f"User '{name}' created successfully!", "success")
                except Exception:
                    conn.rollback()
                    flash("Email already exists.", "danger")

            elif action == "delete_user":
                user_id = int(request.form.get("user_id"))
                if user_id == session["user_id"]:
                    flash("Cannot delete yourself.", "danger")
                else:
                    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
                    conn.commit()
                    flash("User deleted.", "warning")

        rates_rows = conn.execute("SELECT metal, price_per_gram, updated_at FROM rates ORDER BY metal").fetchall()
        rates = {r["metal"]: r for r in rates_rows}
        charges_rows = conn.execute("SELECT service_type, default_rate, unit, updated_at FROM service_charges").fetchall()
        service_charges = {r["service_type"]: r for r in charges_rows}
        users = conn.execute("SELECT id, name, email, role, created_at FROM users ORDER BY created_at").fetchall()
    finally:
        conn.close()
    return render_template("settings.html", rates=rates, service_charges=service_charges, users=users)


# ─────────────────────────────────────────────
# SEARCH API
# ─────────────────────────────────────────────

@app.route("/api/search")
@login_required
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    like = f"%{q}%"
    conn = get_db()
    results = []
    try:
        # Gold Tests
        for row in conn.execute("""
            SELECT 'Gold Test' AS type, id, receipt_no, customer_name, test_date AS date, contact_no 
            FROM gold_tests 
            WHERE customer_name LIKE ? OR contact_no LIKE ? OR receipt_no LIKE ? LIMIT 4
        """, (like, like, like)).fetchall():
            results.append({
                "type": row["type"], "id": row["id"], "receipt_no": row["receipt_no"],
                "customer_name": row["customer_name"], "date": str(row["date"]), 
                "contact_no": row["contact_no"],
                "url": url_for("gold_testing_view", test_id=row["id"])
            })

        # Silver Tests
        for row in conn.execute("""
            SELECT 'Silver Test' AS type, id, receipt_no, customer_name, test_date AS date, contact_no 
            FROM silver_tests 
            WHERE customer_name LIKE ? OR contact_no LIKE ? OR receipt_no LIKE ? LIMIT 4
        """, (like, like, like)).fetchall():
            results.append({
                "type": row["type"], "id": row["id"], "receipt_no": row["receipt_no"],
                "customer_name": row["customer_name"], "date": str(row["date"]), 
                "contact_no": row["contact_no"],
                "url": url_for("silver_testing_view", test_id=row["id"])
            })

        # Polish entries & bills
        for row in conn.execute("SELECT 'Silver Entry' AS type, id, customer_name, date, contact_no FROM silver_entries WHERE customer_name LIKE ? OR contact_no LIKE ? LIMIT 3", (like, like)).fetchall():
            results.append({"type": row["type"], "id": row["id"], "customer_name": row["customer_name"], "date": str(row["date"]), "contact_no": row["contact_no"], "url": url_for("silver_list")})
        for row in conn.execute("SELECT 'Gold Entry' AS type, id, customer_name, date, contact_no FROM gold_entries WHERE customer_name LIKE ? OR contact_no LIKE ? LIMIT 3", (like, like)).fetchall():
            results.append({"type": row["type"], "id": row["id"], "customer_name": row["customer_name"], "date": str(row["date"]), "contact_no": row["contact_no"], "url": url_for("gold_list")})
        for row in conn.execute("SELECT 'Silver Bill' AS type, id, customer_name, date, contact_no FROM silver_bills WHERE customer_name LIKE ? OR contact_no LIKE ? LIMIT 3", (like, like)).fetchall():
            results.append({"type": row["type"], "id": row["id"], "customer_name": row["customer_name"], "date": str(row["date"]), "contact_no": row["contact_no"], "url": url_for("silver_bill_view", bill_id=row["id"])})
        for row in conn.execute("SELECT 'Gold Bill' AS type, id, customer_name, date, contact_no FROM gold_bills WHERE customer_name LIKE ? OR contact_no LIKE ? LIMIT 3", (like, like)).fetchall():
            results.append({"type": row["type"], "id": row["id"], "customer_name": row["customer_name"], "date": str(row["date"]), "contact_no": row["contact_no"], "url": url_for("gold_bill_view", bill_id=row["id"])})
    finally:
        conn.close()
    return jsonify(results)


# ─────────────────────────────────────────────
# PDF GENERATORS
# ─────────────────────────────────────────────

def _build_pdf_base():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"],
                                  fontSize=18, textColor=colors.HexColor("#1a1a2e"),
                                  spaceAfter=2, alignment=TA_CENTER)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"],
                                fontSize=10, textColor=colors.HexColor("#555555"),
                                spaceAfter=10, alignment=TA_CENTER)
    return buffer, doc, styles, title_style, sub_style


def generate_silver_pdf(bill):
    buffer, doc, styles, title_style, sub_style = _build_pdf_base()
    story = []
    story.append(Paragraph("Siddhanth Firm", title_style))
    story.append(Paragraph("Silver Polish Receipt", sub_style))
    story.append(Spacer(1, 0.3*cm))

    info_data = [
        ["Bill No:", f"SB-{bill['id']:04d}", "Date:", str(bill["date"])],
        ["Customer:", bill["customer_name"], "Contact:", bill["contact_no"] or "—"],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TEXTCOLOR", (0,0), (0,-1), colors.HexColor("#555")),
        ("TEXTCOLOR", (2,0), (2,-1), colors.HexColor("#555")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4*cm))

    sw = float(bill["silver_weight"]); sp = float(bill["silver_price"])
    waste = float(bill["waste"]); extra = float(bill["extra_weight"])
    sg = float(bill["silver_gram"]); sgp = float(bill["silver_gram_price"])

    data = [
        ["Description", "Rate", "Weight / Qty", "Amount (₹)"],
        ["Silver Processing", f"Rs. {sp:.2f}/g", f"{sw:.3f} g", f"Rs. {sw*sp:.2f}"],
        ["Waste Deduction", "—", f"-{waste:.3f} g", f"-Rs. {waste:.2f}"],
        ["Extra Weight", "—", f"+{extra:.3f} g", f"+Rs. {extra:.2f}"],
        ["Silver Gram Charge", f"Rs. {sgp:.2f}/g", f"{sg:.3f} g", f"Rs. {sg*sgp:.2f}"],
        ["", "", "TOTAL", f"Rs. {float(bill['total_amount']):.2f}"],
    ]
    tbl = Table(data, colWidths=[7*cm, 4*cm, 3.5*cm, 3.5*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f5f5f5")]),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#e8f0fe")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,-1), (-1,-1), 12),
        ("GRID", (0,0), (-1,-2), 0.5, colors.HexColor("#cccccc")),
        ("LINEABOVE", (0,-1), (-1,-1), 1.5, colors.HexColor("#1a1a2e")),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Thank you for your business!", ParagraphStyle("thanks",
        fontSize=11, textColor=colors.HexColor("#888"), alignment=TA_CENTER)))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_gold_pdf(bill):
    buffer, doc, styles, title_style, sub_style = _build_pdf_base()
    story = []
    story.append(Paragraph("Siddhanth Firm", title_style))
    story.append(Paragraph("Gold Polish Receipt", sub_style))
    story.append(Spacer(1, 0.3*cm))

    info_data = [
        ["Bill No:", f"GB-{bill['id']:04d}", "Date:", str(bill["date"])],
        ["Customer:", bill["customer_name"], "Contact:", bill["contact_no"] or "—"],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TEXTCOLOR", (0,0), (0,-1), colors.HexColor("#555")),
        ("TEXTCOLOR", (2,0), (2,-1), colors.HexColor("#555")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4*cm))

    gw = float(bill["gold_weight"]); gp = float(bill["gold_price"])
    gg = float(bill["gold_gram"]); ggp = float(bill["gold_gram_price"])

    data = [
        ["Description", "Rate", "Weight / Qty", "Amount (₹)"],
        ["Gold Processing", f"Rs. {gp:.2f}/g", f"{gw:.3f} g", f"Rs. {gw*gp:.2f}"],
        ["Gold Gram Charge", f"Rs. {ggp:.2f}/g", f"{gg:.3f} g", f"Rs. {gg*ggp:.2f}"],
        ["", "", "TOTAL", f"Rs. {float(bill['total_amount']):.2f}"],
    ]
    tbl = Table(data, colWidths=[7*cm, 4*cm, 3.5*cm, 3.5*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#7B5E1A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#fffbf0")]),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#fff3cd")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,-1), (-1,-1), 12),
        ("GRID", (0,0), (-1,-2), 0.5, colors.HexColor("#cccccc")),
        ("LINEABOVE", (0,-1), (-1,-1), 1.5, colors.HexColor("#7B5E1A")),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Thank you for your business!", ParagraphStyle("thanks",
        fontSize=11, textColor=colors.HexColor("#888"), alignment=TA_CENTER)))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_gold_test_pdf(test, items):
    """Generate professional printable PDF for Gold Testing Certificate & Invoice."""
    buffer, doc, styles, _, _ = _build_pdf_base()
    story = []

    gold_dark = colors.HexColor("#996515")
    navy_dark = colors.HexColor("#1a1a2e")
    gray_bg   = colors.HexColor("#f8f9fa")

    # Firm Header
    header_data = [
        [
            Paragraph("<font size=16 color='#996515'><b>SHREE SIDDHNATH BULLION TUNCH</b></font><br/>"
                      "<font size=10 color='#444444'>Approved Computerized Assay & Precious Metal Testing Laboratory</font><br/>"
                      "<font size=8 color='#666666'>Kashinath Seth Gali, Ashraf Tola, Hardoi - 241001 (U.P.) | Mob: 7376226999, 9936538678</font>",
                      ParagraphStyle("head_left", parent=styles["Normal"], alignment=TA_LEFT, leading=14)),
            Paragraph("<font size=11 color='#996515'><b>★ 100% ★</b></font><br/>"
                      "<font size=12 color='#1a1a2e'><b>ASSAY</b></font><br/>"
                      "<font size=8 color='#666666'>XRF TESTED</font>",
                      ParagraphStyle("head_stamp", parent=styles["Normal"], alignment=TA_CENTER, leading=13))
        ]
    ]
    header_tbl = Table(header_data, colWidths=[14*cm, 4*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LINEBOTTOM", (0,0), (-1,-1), 1.5, gold_dark),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.3*cm))

    # Certificate Title
    title_text = "<font size=11 color='#996515'><b>GOLD ASSAY CERTIFICATE & TAX INVOICE</b></font>"
    story.append(Paragraph(title_text, ParagraphStyle("cert_title", parent=styles["Normal"], alignment=TA_CENTER, spaceAfter=8)))

    # Metadata Grid
    meta_data = [
        [
            Paragraph(f"<b>Certificate No:</b> <font color='#996515'>{test['receipt_no']}</font>", styles["Normal"]),
            Paragraph(f"<b>Customer / Party:</b> <b>{test['customer_name']}</b>", styles["Normal"])
        ],
        [
            Paragraph(f"<b>Testing Date:</b> {str(test['test_date'])}", styles["Normal"]),
            Paragraph(f"<b>Contact No:</b> {test['contact_no'] or '—'}", styles["Normal"])
        ],
        [
            Paragraph(f"<b>Testing Method:</b> {items[0]['testing_method'] if items else 'Computerized XRF Assay'}", styles["Normal"]),
            Paragraph(f"<b>Address:</b> {test['address'] or 'Hardoi'}", styles["Normal"])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[9*cm, 9*cm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BACKGROUND", (0,0), (-1,-1), gray_bg),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.4*cm))

    # Items Table
    item_rows = [
        ["#", "Item Description", "Gross (g)", "Net (g)", "Purity (K)", "Gold %", "Fine Gold (g)", "Qty", "Amount (Rs.)"]
    ]
    for idx, itm in enumerate(items, 1):
        item_rows.append([
            str(idx),
            itm["item_name"],
            f"{float(itm['gross_weight']):.3f}",
            f"{float(itm['net_weight'] or itm['gross_weight']):.3f}",
            f"{float(itm['purity_karat']):.2f} K",
            f"{float(itm['purity_percent'] or (itm['purity_karat']/24*100)):.2f}%",
            f"{float(itm['fine_gold_weight'] or (itm['net_weight']*(itm['purity_karat']/24))):.3f}",
            str(itm["quantity"]),
            f"Rs. {float(itm['total_charge']):.2f}"
        ])

    items_tbl = Table(item_rows, colWidths=[0.8*cm, 4.2*cm, 2*cm, 2*cm, 2*cm, 1.8*cm, 2.2*cm, 1*cm, 2*cm])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), navy_dark),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (2,0), (-1,-1), "RIGHT"),
        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("ALIGN", (4,0), (5,-1), "CENTER"),
        ("ALIGN", (7,0), (7,-1), "CENTER"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#fffdf5")]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Summary and Notes Grid
    terms_para = Paragraph(
        "<b>Terms & Conditions:</b><br/>"
        "1. Standard accuracy is within ±0.30% under non-destructive computerized XRF assay.<br/>"
        "2. Laboratory is not responsible for internal melting defects or non-homogeneous alloys.<br/>"
        "3. All disputes subject to Hardoi jurisdiction.<br/>"
        f"<b>Remarks:</b> {test['notes'] or 'Standard XRF Assay Testing Certified'}",
        ParagraphStyle("terms", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#555"))
    )

    summary_rows = [
        ["Subtotal:", f"Rs. {float(test['subtotal']):.2f}"],
        ["Add Charges:", f"+Rs. {float(test['additional_charges']):.2f}"],
        ["Discount:", f"-Rs. {float(test['discount']):.2f}"],
        ["Grand Total:", f"Rs. {float(test['grand_total']):.2f}"],
        ["Received:", f"Rs. {float(test['amount_received']):.2f}"],
        ["Balance Due:", f"Rs. {float(test['balance_amount']):.2f}"],
    ]
    summary_tbl = Table(summary_rows, colWidths=[4*cm, 3*cm])
    summary_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("LINEBELOW", (0,3), (1,3), 1, gold_dark),
        ("FONTNAME", (0,3), (1,3), "Helvetica-Bold"),
        ("BACKGROUND", (0,3), (1,3), colors.HexColor("#fff8e1")),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    bottom_grid = Table([[terms_para, summary_tbl]], colWidths=[11*cm, 7*cm])
    bottom_grid.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(bottom_grid)
    story.append(Spacer(1, 0.8*cm))

    # Signatures
    sig_data = [
        [
            Paragraph("<font size=8>____________________________<br/>Customer Acknowledgement</font>", ParagraphStyle("sig1", parent=styles["Normal"], alignment=TA_CENTER)),
            Paragraph("<font size=8 color='#996515'><b>SHREE SIDDHNATH BULLION TUNCH</b><br/>____________________________<br/>Authorised Signatory / Assayer</font>", ParagraphStyle("sig2", parent=styles["Normal"], alignment=TA_CENTER))
        ]
    ]
    sig_tbl = Table(sig_data, colWidths=[9*cm, 9*cm])
    sig_tbl.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(sig_tbl)
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<font size=8 color='#996515'>Purity is Our Surety · Thank You, Visit Again!</font>",
                           ParagraphStyle("thx", parent=styles["Normal"], alignment=TA_CENTER)))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_silver_test_pdf(test, items):
    """Generate professional printable PDF for Silver Testing Certificate & Invoice."""
    buffer, doc, styles, _, _ = _build_pdf_base()
    story = []

    silver_dark = colors.HexColor("#475569")
    navy_dark   = colors.HexColor("#1e293b")
    gray_bg     = colors.HexColor("#f8fafc")

    # Firm Header
    header_data = [
        [
            Paragraph("<font size=16 color='#334155'><b>SHREE SIDDHNATH BULLION TUNCH</b></font><br/>"
                      "<font size=10 color='#444444'>Approved Silver Assay, Testing & Refining Laboratory</font><br/>"
                      "<font size=8 color='#666666'>Kashinath Seth Gali, Ashraf Tola, Hardoi - 241001 (U.P.) | Mob: 7376226999, 9936538678</font>",
                      ParagraphStyle("shead_left", parent=styles["Normal"], alignment=TA_LEFT, leading=14)),
            Paragraph("<font size=11 color='#334155'><b>★ 100% ★</b></font><br/>"
                      "<font size=12 color='#1e293b'><b>SILVER</b></font><br/>"
                      "<font size=8 color='#666666'>PURITY TESTED</font>",
                      ParagraphStyle("shead_stamp", parent=styles["Normal"], alignment=TA_CENTER, leading=13))
        ]
    ]
    header_tbl = Table(header_data, colWidths=[14*cm, 4*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LINEBOTTOM", (0,0), (-1,-1), 1.5, silver_dark),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.3*cm))

    # Certificate Title
    title_text = "<font size=11 color='#334155'><b>SILVER PURITY ASSAY CERTIFICATE & TAX INVOICE</b></font>"
    story.append(Paragraph(title_text, ParagraphStyle("scert_title", parent=styles["Normal"], alignment=TA_CENTER, spaceAfter=8)))

    # Metadata Grid
    meta_data = [
        [
            Paragraph(f"<b>Certificate No:</b> <font color='#334155'>{test['receipt_no']}</font>", styles["Normal"]),
            Paragraph(f"<b>Customer / Party:</b> <b>{test['customer_name']}</b>", styles["Normal"])
        ],
        [
            Paragraph(f"<b>Testing Date:</b> {str(test['test_date'])}", styles["Normal"]),
            Paragraph(f"<b>Contact No:</b> {test['contact_no'] or '—'}", styles["Normal"])
        ],
        [
            Paragraph(f"<b>Testing Method:</b> {items[0]['testing_method'] if items else 'Computerized XRF Assay'}", styles["Normal"]),
            Paragraph(f"<b>Address:</b> {test['address'] or 'Hardoi'}", styles["Normal"])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[9*cm, 9*cm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BACKGROUND", (0,0), (-1,-1), gray_bg),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.4*cm))

    # Items Table
    item_rows = [
        ["#", "Item Description", "Gross (g)", "Net (g)", "Purity / Fineness (Chinha)", "Qty", "Amount (Rs.)"]
    ]
    for idx, itm in enumerate(items, 1):
        item_rows.append([
            str(idx),
            itm["item_name"],
            f"{float(itm['gross_weight']):.3f}",
            f"{float(itm['net_weight'] or itm['gross_weight']):.3f}",
            itm["purity_fineness"],
            str(itm["quantity"]),
            f"Rs. {float(itm['total_charge']):.2f}"
        ])

    items_tbl = Table(item_rows, colWidths=[1*cm, 5.5*cm, 2.5*cm, 2.5*cm, 4*cm, 1*cm, 2.5*cm])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), navy_dark),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ALIGN", (2,0), (3,-1), "RIGHT"),
        ("ALIGN", (4,0), (4,-1), "CENTER"),
        ("ALIGN", (5,0), (5,-1), "CENTER"),
        ("ALIGN", (6,0), (6,-1), "RIGHT"),
        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Summary and Notes Grid
    terms_para = Paragraph(
        "<b>Terms & Conditions:</b><br/>"
        "1. Note 1: Standard assay testing tolerance within 25/30 points.<br/>"
        "2. Note 2: Firm not responsible for cut pieces or external melting defects.<br/>"
        "3. All disputes subject to Hardoi jurisdiction.<br/>"
        f"<b>Remarks:</b> {test['notes'] or 'Scientific Silver Assay Certified (Pandurang Mumbai Wale)'}",
        ParagraphStyle("sterms", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#555"))
    )

    summary_rows = [
        ["Subtotal:", f"Rs. {float(test['subtotal']):.2f}"],
        ["Add Charges:", f"+Rs. {float(test['additional_charges']):.2f}"],
        ["Discount:", f"-Rs. {float(test['discount']):.2f}"],
        ["Grand Total:", f"Rs. {float(test['grand_total']):.2f}"],
        ["Received:", f"Rs. {float(test['amount_received']):.2f}"],
        ["Balance Due:", f"Rs. {float(test['balance_amount']):.2f}"],
    ]
    summary_tbl = Table(summary_rows, colWidths=[4*cm, 3*cm])
    summary_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("LINEBELOW", (0,3), (1,3), 1, silver_dark),
        ("FONTNAME", (0,3), (1,3), "Helvetica-Bold"),
        ("BACKGROUND", (0,3), (1,3), colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    bottom_grid = Table([[terms_para, summary_tbl]], colWidths=[11*cm, 7*cm])
    bottom_grid.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(bottom_grid)
    story.append(Spacer(1, 0.8*cm))

    # Signatures
    sig_data = [
        [
            Paragraph("<font size=8>____________________________<br/>Customer Acknowledgement</font>", ParagraphStyle("ssig1", parent=styles["Normal"], alignment=TA_CENTER)),
            Paragraph("<font size=8 color='#334155'><b>SHREE SIDDHNATH BULLION TUNCH</b><br/>____________________________<br/>Authorised Signatory (Pandurang Mumbai Wale)</font>", ParagraphStyle("ssig2", parent=styles["Normal"], alignment=TA_CENTER))
        ]
    ]
    sig_tbl = Table(sig_data, colWidths=[9*cm, 9*cm])
    sig_tbl.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(sig_tbl)
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<font size=8 color='#475569'>Purity is Our Surety · Thank You, Visit Again!</font>",
                           ParagraphStyle("sthx", parent=styles["Normal"], alignment=TA_CENTER)))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import threading
    import webbrowser

    port = int(os.environ.get("PORT", 5000))
    is_frozen = getattr(sys, "frozen", False)
    host = "127.0.0.1" if is_frozen else "0.0.0.0"

    # In standalone EXE mode, automatically pop open the user's browser
    if is_frozen:
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")

        threading.Thread(target=open_browser, daemon=True).start()
        print("=" * 65)
        print("   SHREE SIDDHNATH BULLION & TESTING MANAGEMENT SYSTEM")
        print("=" * 65)
        print(f"   Application running at: http://localhost:{port}")
        print("   Your web browser will open automatically in a moment.")
        print("   Keep this terminal window open while using the software.")
        print("   To stop the application, press Ctrl+C or close this window.")
        print("=" * 65)

    app.run(debug=os.environ.get("FLASK_ENV") == "development" and not is_frozen,
            host=host, port=port)
