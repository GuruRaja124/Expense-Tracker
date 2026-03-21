import os
import json
import sqlite3
from functools import wraps
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g
)

# App configuration
app = Flask(__name__)
app.secret_key = "expense_tracker_secret_key_2026"
DATABASE = os.path.join(os.path.dirname(__file__), "database.db")

# Database helpers
def get_db():
    """Open a database connection and store it on the 'g' object."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Close the database connection at the end of each request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Create all tables if they do not exist."""
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()

    # Users table – includes tracking and budget metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            username            TEXT NOT NULL,
            email               TEXT NOT NULL UNIQUE,
            password            TEXT NOT NULL,
            tracking_start_date TEXT,
            budget_amount       REAL DEFAULT 0,
            budget_set_date     TEXT
        )
    """)

    # Expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER NOT NULL,
            title    TEXT NOT NULL,
            amount   REAL NOT NULL,
            category TEXT NOT NULL,
            date     TEXT NOT NULL,
            notes    TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Quarterly archives
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarterly_archives (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            quarter_start  TEXT NOT NULL,
            quarter_end    TEXT NOT NULL,
            total_amount   REAL NOT NULL,
            category_data  TEXT,
            archived_on    TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    db.commit()
    db.close()

# Helpers – date / cycle calculations
def get_now():
    """Current IST datetime (UTC+5:30)."""
    from datetime import timezone
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist)


def get_today_str():
    """Today's date as ISO string in IST."""
    return get_now().strftime("%Y-%m-%d")

def needs_budget(user):
    """Return True if the user must set / update their monthly budget."""
    # No budget set yet
    if not user["budget_set_date"] or user["budget_amount"] is None or user["budget_amount"] == 0:
        return True
    # Budget older than 30 days
    budget_date = datetime.strptime(user["budget_set_date"], "%Y-%m-%d")
    today = datetime.strptime(get_today_str(), "%Y-%m-%d")
    return (today - budget_date).days >= 30


def get_cycle_boundaries(tracking_start_str):
    """
    Return the boundaries of the current daily / weekly / monthly / quarterly
    cycles relative to the tracking start date.

    Returns a dict with start-date strings for each window.
    """
    today = datetime.strptime(get_today_str(), "%Y-%m-%d")
    start = datetime.strptime(tracking_start_str, "%Y-%m-%d")

    elapsed = (today - start).days

    # Daily cycle: just today
    daily_start = today.strftime("%Y-%m-%d")

    # Weekly cycle: which 7-day window are we in?
    week_num = elapsed // 7
    weekly_start = (start + timedelta(days=week_num * 7)).strftime("%Y-%m-%d")

    # Monthly cycle: which 30-day window are we in?
    month_num = elapsed // 30
    monthly_start = (start + timedelta(days=month_num * 30)).strftime("%Y-%m-%d")

    # Quarterly cycle: which 120-day window are we in?
    quarter_num = elapsed // 120
    quarterly_start = (start + timedelta(days=quarter_num * 120)).strftime("%Y-%m-%d")

    return {
        "daily_start": daily_start,
        "weekly_start": weekly_start,
        "monthly_start": monthly_start,
        "quarterly_start": quarterly_start,
        "today": today.strftime("%Y-%m-%d"),
        "elapsed": elapsed,
        "days_left_week": 7 - (elapsed % 7),
        "days_left_month": 30 - (elapsed % 30),
        "days_left_quarter": 120 - (elapsed % 120),
    }

# Auth decorator
def login_required(f):
    """Redirect to login page if user is not logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# Budget-check middleware
@app.before_request
def check_budget():
    """If user is logged in and needs to set a budget, redirect them."""
    # Only check on normal page views, skip static files and budget route
    if request.endpoint in ("set_budget", "logout", "login", "register",
                            "home", "history", "static", None):
        return

    if "user_id" not in session:
        return

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?",
                      (session["user_id"],)).fetchone()
    if user and needs_budget(user):
        return redirect(url_for("set_budget"))

# Routes – Authentication
@app.route("/")
def home():
    """Redirect to dashboard if logged in, otherwise to login page."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # Validation
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("register"))

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing:
            flash("Email is already registered.", "danger")
            return redirect(url_for("register"))

        # Store user with plain-text password
        db.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, password),
        )
        db.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in an existing user."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear the session and redirect to login."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# Routes – Budget
@app.route("/set-budget", methods=["GET", "POST"])
@login_required
def set_budget():
    """Ask the user to set or update their monthly budget."""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?",
                      (session["user_id"],)).fetchone()

    if request.method == "POST":
        try:
            amount = float(request.form.get("budget", 0))
        except ValueError:
            amount = 0

        if amount <= 0:
            flash("Please enter a valid budget amount.", "danger")
            return redirect(url_for("set_budget"))

        today = get_today_str()
        db.execute(
            "UPDATE users SET budget_amount = ?, budget_set_date = ? WHERE id = ?",
            (amount, today, session["user_id"]),
        )
        db.commit()

        flash("Monthly budget set to ₹{:.2f}".format(amount), "success")
        return redirect(url_for("dashboard"))

    return render_template("set_budget.html", current_budget=user["budget_amount"])

# Routes – Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    """Show spending summaries based on cycle intervals."""
    db = get_db()
    user_id = session["user_id"]
    user = db.execute("SELECT * FROM users WHERE id = ?",
                      (user_id,)).fetchone()

    budget = user["budget_amount"] or 0
    tracking_start = user["tracking_start_date"]

    # If no expenses have been recorded yet, show empty dashboard
    if not tracking_start:
        return render_template(
            "dashboard.html",
            daily=0, weekly=0, monthly=0, quarterly=0,
            budget=budget, expense_pct=0, indicator="healthy",
            categories=[], recent=[],
            cycle_info=None, has_tracking=False,
        )

    # Check for quarterly archiving (120 days elapsed)
    today = datetime.strptime(get_today_str(), "%Y-%m-%d")
    start_dt = datetime.strptime(tracking_start, "%Y-%m-%d")
    elapsed = (today - start_dt).days

    if elapsed >= 120:
        _archive_quarter(db, user_id, tracking_start, elapsed)
        # Refresh user data after archive
        user = db.execute("SELECT * FROM users WHERE id = ?",
                          (user_id,)).fetchone()
        tracking_start = user["tracking_start_date"]

    # Calculate cycle boundaries
    cycles = get_cycle_boundaries(tracking_start)

    # Sum expenses for each cycle
    daily_total = _sum_expenses(db, user_id,
                                cycles["daily_start"], cycles["today"])
    weekly_total = _sum_expenses(db, user_id,
                                 cycles["weekly_start"], cycles["today"])
    monthly_total = _sum_expenses(db, user_id,
                                  cycles["monthly_start"], cycles["today"])
    quarterly_total = _sum_expenses(db, user_id,
                                    cycles["quarterly_start"], cycles["today"])

    # Expense percentage against monthly budget
    if budget > 0:
        expense_pct = round((monthly_total / budget) * 100, 1)
    else:
        expense_pct = 0

    # Spending indicator – three levels
    if expense_pct >= 100:
        indicator = "exceeded"
    elif expense_pct >= 80:
        indicator = "warning"
    elif expense_pct >= 60:
        indicator = "caution"
    else:
        indicator = "healthy"

    # Category breakdown (current month cycle)
    category_emojis = {
        "Food": "🍜", "Transport": "🚗", "Shopping": "🛍️",
        "Bills": "💡", "Entertainment": "🎬", "Health": "🏥",
        "Education": "📚", "Other": "📦",
    }
    categories_rows = db.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? AND date >= ? AND date <= ? "
        "GROUP BY category ORDER BY total DESC",
        (user_id, cycles["monthly_start"], cycles["today"]),
    ).fetchall()

    category_data = []
    pie_labels = []
    pie_values = []
    if monthly_total > 0:
        for row in categories_rows:
            pct = round((row["total"] / monthly_total) * 100)
            emoji = category_emojis.get(row["category"], "📦")
            category_data.append({
                "name": row["category"],
                "emoji": emoji,
                "total": row["total"],
                "percent": pct,
            })
            pie_labels.append("{} {}".format(emoji, row["category"]))
            pie_values.append(row["total"])

    # Weekly day-wise spending for bar chart (Mon–Sun of current week)
    week_start_dt = datetime.strptime(cycles["weekly_start"], "%Y-%m-%d")
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_values = []
    for i in range(7):
        d = (week_start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        day_total = _sum_expenses(db, user_id, d, d)
        day_values.append(day_total)

    # Recent expenses (last 5)
    recent = db.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT 5",
        (user_id,),
    ).fetchall()

    return render_template(
        "dashboard.html",
        daily=daily_total,
        weekly=weekly_total,
        monthly=monthly_total,
        quarterly=quarterly_total,
        budget=budget,
        expense_pct=expense_pct,
        indicator=indicator,
        categories=category_data,
        pie_labels=json.dumps(pie_labels),
        pie_values=json.dumps(pie_values),
        day_labels=json.dumps(day_labels),
        day_values=json.dumps(day_values),
        recent=recent,
        cycle_info=cycles,
        has_tracking=True,
    )


def _sum_expenses(db, user_id, start_date, end_date):
    """Sum expenses between two ISO date strings (inclusive)."""
    result = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses "
        "WHERE user_id = ? AND date >= ? AND date <= ?",
        (user_id, start_date, end_date),
    ).fetchone()
    return result[0]


def _archive_quarter(db, user_id, tracking_start, elapsed):
    """Archive the completed quarter and reset tracking start date."""
    quarter_num = elapsed // 120
    start_dt = datetime.strptime(tracking_start, "%Y-%m-%d")

    # Archive each completed 120-day block
    for i in range(quarter_num):
        q_start = (start_dt + timedelta(days=i * 120)).strftime("%Y-%m-%d")
        q_end = (start_dt + timedelta(days=(i + 1) * 120 - 1)).strftime("%Y-%m-%d")

        total = _sum_expenses(db, user_id, q_start, q_end)

        # Category summary as simple text
        cats = db.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? AND date >= ? AND date <= ? "
            "GROUP BY category",
            (user_id, q_start, q_end),
        ).fetchall()
        cat_text = ", ".join(
            "{}: {:.2f}".format(c["category"], c["total"]) for c in cats
        )

        db.execute(
            "INSERT INTO quarterly_archives "
            "(user_id, quarter_start, quarter_end, total_amount, category_data, archived_on) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, q_start, q_end, total, cat_text, get_today_str()),
        )

    # Set new tracking start to the beginning of the current quarter
    new_start = (start_dt + timedelta(days=quarter_num * 120)).strftime("%Y-%m-%d")
    db.execute(
        "UPDATE users SET tracking_start_date = ? WHERE id = ?",
        (new_start, user_id),
    )
    db.commit()

# Routes – Quarterly History
@app.route("/history")
@login_required
def history():
    """Show archived quarterly reports."""
    db = get_db()
    archives = db.execute(
        "SELECT * FROM quarterly_archives WHERE user_id = ? "
        "ORDER BY quarter_start DESC",
        (session["user_id"],),
    ).fetchall()

    # Parse category_data text into a list of dicts for display
    parsed = []
    for arc in archives:
        cats = []
        if arc["category_data"]:
            for pair in arc["category_data"].split(", "):
                parts = pair.rsplit(": ", 1)
                if len(parts) == 2:
                    cats.append({"name": parts[0], "total": float(parts[1])})
        parsed.append({
            "id": arc["id"],
            "quarter_start": arc["quarter_start"],
            "quarter_end": arc["quarter_end"],
            "total_amount": arc["total_amount"],
            "archived_on": arc["archived_on"],
            "categories": cats,
        })

    return render_template("history.html", archives=parsed)

# Routes – Expenses
@app.route("/add-expense")
@login_required
def add_expense():
    """Show the add-expense form."""
    return render_template("add_expense.html")


@app.route("/submit-expense", methods=["POST"])
@login_required
def submit_expense():
    """Save a new expense to the database."""
    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "")
    category = request.form.get("category", "").strip()
    expense_date = request.form.get("date", "").strip()
    notes = request.form.get("notes", "").strip()

    if not title or not amount or not category or not expense_date:
        flash("Please fill in all required fields.", "danger")
        return redirect(url_for("add_expense"))

    try:
        amount = float(amount)
    except ValueError:
        flash("Amount must be a valid number.", "danger")
        return redirect(url_for("add_expense"))

    db = get_db()
    user_id = session["user_id"]

    # Set tracking start date on first expense
    user = db.execute("SELECT tracking_start_date FROM users WHERE id = ?",
                      (user_id,)).fetchone()
    if not user["tracking_start_date"]:
        db.execute(
            "UPDATE users SET tracking_start_date = ? WHERE id = ?",
            (expense_date, user_id),
        )

    db.execute(
        "INSERT INTO expenses (user_id, title, amount, category, date, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, title, amount, category, expense_date, notes),
    )
    db.commit()

    flash("Expense added successfully!", "success")
    return redirect(url_for("expenses"))


@app.route("/expenses")
@login_required
def expenses():
    """List all expenses for the logged-in user."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC",
        (session["user_id"],),
    ).fetchall()
    return render_template("expenses.html", expenses=rows)


@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    """Delete an expense belonging to the logged-in user."""
    db = get_db()
    db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, session["user_id"]),
    )
    db.commit()
    flash("Expense deleted.", "info")
    return redirect(url_for("expenses"))

# Run the app
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
