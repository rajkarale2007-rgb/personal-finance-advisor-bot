from datetime import datetime
import io
import csv
import os
import sys

# Ensure UTF-8 output encoding on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from local_advisor import local_model

# Load environment variables from .env
load_dotenv()

# Initialize Flask application
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "finance-advisor-secret-key-change-in-prod"
)
database_url = os.environ.get("DATABASE_URL", "sqlite:///finance.db")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Database & Login Manager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "info"
login_manager.init_app(app)

# Configure Gemini AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Warning: Failed to configure Gemini API: {e}")


# ==========================================
# Database Models
# ==========================================
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    gemini_api_key = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    incomes = db.relationship("Income", backref="user", lazy=True, cascade="all, delete-orphan")
    expenses = db.relationship("Expense", backref="user", lazy=True, cascade="all, delete-orphan")
    goals = db.relationship("Goal", backref="user", lazy=True, cascade="all, delete-orphan")

    def __init__(self, username: str, email: str, password_hash: str = "", gemini_api_key: str | None = None):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.gemini_api_key = gemini_api_key

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Income(db.Model):
    __tablename__ = "incomes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # Format: 'YYYY-MM'
    source = db.Column(db.String(100), nullable=False, default="Primary Income")  # e.g., Salary, Client A, Freelance
    amount = db.Column(db.Float, nullable=False, default=0.0)
    date = db.Column(db.String(10), nullable=False)  # Format: 'YYYY-MM-DD'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id: int, month: str, amount: float, date: str, source: str = "Primary Income"):
        self.user_id = user_id
        self.month = month
        self.source = source
        self.amount = amount
        self.date = date


class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # Format: 'YYYY-MM'
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    date = db.Column(db.String(10), nullable=False)  # Format: 'YYYY-MM-DD'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id: int, month: str, category: str, amount: float, date: str, description: str = ""):
        self.user_id = user_id
        self.month = month
        self.category = category
        self.amount = amount
        self.description = description
        self.date = date


class Goal(db.Model):
    __tablename__ = "goals"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., 'Emergency Fund', 'New Laptop'
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False, default=0.0)
    deadline = db.Column(db.String(10), nullable=True)  # Format: 'YYYY-MM-DD'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id: int, name: str, target_amount: float, current_amount: float = 0.0, deadline: str | None = None):
        self.user_id = user_id
        self.name = name
        self.target_amount = target_amount
        self.current_amount = current_amount
        self.deadline = deadline


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Create database tables and perform lightweight auto-migration
with app.app_context():
    db.create_all()
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        columns = [c["name"] for c in inspector.get_columns("users")]
        if "gemini_api_key" not in columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN gemini_api_key VARCHAR(255)"))
                conn.commit()
    except Exception as e:
        print(f"Schema migration note: {e}")


# ==========================================
# Helper Functions: Financial Analysis & AI
# ==========================================
def get_financial_insights(
    income, total_expenses, category_breakdown, income_sources=None, goals=None, user_api_key=None
):
    """
    Generates insights using Gemini AI if the user supplied their personal API key or if
    the server has GEMINI_API_KEY configured.
    Otherwise, automatically falls back to the embedded Local Finance Advisor Model
    (Offline AI Engine) which runs locally right out of the box with zero setup.
    """
    api_key = (user_api_key or "").strip() or os.environ.get("GEMINI_API_KEY")
    is_user_key = bool((user_api_key or "").strip())

    # 1. Try Cloud Gemini AI Integration if configured
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            goals_summary = [
                f"{g.name}: ${g.current_amount:.2f} of ${g.target_amount:.2f}"
                for g in (goals or [])
            ]
            prompt = (
                "You are an expert personal finance advisor. Analyze this individual's monthly budget:\n"
                f"- Total Income: ${income:.2f}\n"
                f"- Total Expenses: ${total_expenses:.2f}\n"
                f"- Net Savings: ${income - total_expenses:.2f}\n"
                f"- Category Breakdown: {category_breakdown}\n"
                f"- Active Savings Goals: {', '.join(goals_summary) if goals_summary else 'None set'}\n\n"
                "Provide 3-4 concise, highly actionable, encouraging financial recommendations formatted as clear bullet points. "
                "Include guidance on 50/30/20 budget principles, identifying any overspending category, and optimizing savings towards goals."
            )
            response = model.generate_content(prompt)
            if response and response.text:
                insights = [
                    line.strip("-* ").strip()
                    for line in response.text.split("\n")
                    if line.strip() and not line.strip().startswith("#")
                ]
                if insights:
                    label = "Gemini 1.5 Flash (Your API Key)" if is_user_key else "Gemini 1.5 Flash (Cloud AI)"
                    return insights[:4], label
        except Exception as e:
            print(f"Gemini API Error (fallback to local model): {e}")

    # 2. Out-of-the-box Embedded Local Advisor Model (Offline AI Engine)
    local_insights = local_model.analyze(
        income=income,
        total_expenses=total_expenses,
        category_breakdown=category_breakdown,
        income_sources=income_sources,
        goals=goals,
    )
    return local_insights, "Local Advisor AI (Offline Model)"



# ==========================================
# Authentication & View Routes
# ==========================================
@app.route("/register", methods=["GET", "POST"])
def register():
    """Handles user account registration."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already taken. Please choose another.", "danger")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login instead.", "danger")
            return render_template("register.html")

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in to your account.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handles user login authentication."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username_or_email = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("Invalid credentials. Please check your username/email and password.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Logs out the active user and clears the session."""
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    """Renders the main interactive dashboard for the authenticated user."""
    return render_template("index.html", user=current_user)


# ==========================================
# REST API Endpoints (User-Scoped)
# ==========================================
@app.route("/api/data", methods=["GET"])
@login_required
def get_dashboard_data():
    """Retrieves all incomes, expenses, categories, goals, and AI insights for a given month."""
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))

    # Incomes for current user and month
    incomes = (
        Income.query.filter_by(user_id=current_user.id, month=month)
        .order_by(Income.date.desc())
        .all()
    )
    total_income = sum(inc.amount for inc in incomes)

    # Expenses for current user and month
    expenses = (
        Expense.query.filter_by(user_id=current_user.id, month=month)
        .order_by(Expense.date.desc())
        .all()
    )
    total_expenses = sum(exp.amount for exp in expenses)
    net_savings = total_income - total_expenses

    # Breakdown by category
    category_breakdown = {}
    for exp in expenses:
        category_breakdown[exp.category] = (
            category_breakdown.get(exp.category, 0.0) + exp.amount
        )

    # Goals for current user
    goals = Goal.query.filter_by(user_id=current_user.id).all()
    goals_data = [
        {
            "id": g.id,
            "name": g.name,
            "target_amount": g.target_amount,
            "current_amount": g.current_amount,
            "progress_pct": min(
                100.0,
                round((g.current_amount / g.target_amount) * 100, 1)
                if g.target_amount > 0
                else 0.0,
            ),
            "deadline": g.deadline or "Ongoing",
        }
        for g in goals
    ]

    income_list = [
        {
            "id": inc.id,
            "source": inc.source,
            "amount": inc.amount,
            "date": inc.date,
        }
        for inc in incomes
    ]

    transaction_list = [
        {
            "id": exp.id,
            "date": exp.date,
            "category": exp.category,
            "amount": exp.amount,
            "description": exp.description,
        }
        for exp in expenses
    ]

    # Generate Insights using Gemini Cloud AI (User Key or Server Key) or embedded Local Advisor AI
    insights, ai_engine = get_financial_insights(
        total_income,
        total_expenses,
        category_breakdown,
        income_list,
        goals,
        user_api_key=current_user.gemini_api_key,
    )

    return jsonify(
        {
            "month": month,
            "username": current_user.username,
            "income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net_savings,
            "category_breakdown": category_breakdown,
            "income_sources": income_list,
            "transactions": transaction_list,
            "goals": goals_data,
            "insights": insights,
            "ai_engine": ai_engine,
            "has_user_api_key": bool(current_user.gemini_api_key),
        }
    )


@app.route("/api/user/ai-settings", methods=["GET", "POST"])
@login_required
def user_ai_settings():
    """Retrieve or update personal Gemini API key for the authenticated user."""
    if request.method == "POST":
        data = request.get_json() or {}
        new_key = data.get("api_key", "").strip()
        if new_key:
            current_user.gemini_api_key = new_key
            msg = "Personal Gemini API key saved! AI insights will now use your key."
        else:
            current_user.gemini_api_key = None
            msg = "Personal API key removed. Using built-in Local Advisor AI."
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "message": msg,
                "has_key": bool(current_user.gemini_api_key),
                "masked_key": f"...{current_user.gemini_api_key[-4:]}"
                if current_user.gemini_api_key
                else None,
            }
        )

    # GET
    has_key = bool(current_user.gemini_api_key)
    masked_key = (
        f"...{current_user.gemini_api_key[-4:]}" if has_key else None
    )
    return jsonify(
        {
            "has_key": has_key,
            "masked_key": masked_key,
            "server_has_default_key": bool(os.environ.get("GEMINI_API_KEY")),
        }
    )


@app.route("/api/income", methods=["POST"])
@login_required

def add_income():
    """Logs an itemized income entry (salary, freelance, client, etc.)."""
    data = request.get_json() or {}
    month = data.get("month")
    source = data.get("source", "Primary Income").strip() or "Primary Income"
    amount = float(data.get("amount", 0.0))
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    if not month or amount <= 0:
        return jsonify({"error": "Valid month and amount are required."}), 400

    new_income = Income(
        user_id=current_user.id,
        month=month,
        source=source,
        amount=amount,
        date=date,
    )
    db.session.add(new_income)
    db.session.commit()

    return jsonify({"message": "Income successfully recorded", "id": new_income.id}), 201


@app.route("/api/income/<int:income_id>", methods=["DELETE"])
@login_required
def delete_income(income_id):
    """Deletes an income entry owned by current user."""
    income_record = Income.query.filter_by(id=income_id, user_id=current_user.id).first_or_404()
    db.session.delete(income_record)
    db.session.commit()
    return jsonify({"message": "Income deleted successfully"})


@app.route("/api/expense", methods=["POST"])
@login_required
def add_expense():
    """Logs a new expense entry."""
    data = request.get_json() or {}
    month = data.get("month")
    category = data.get("category")
    amount = float(data.get("amount", 0.0))
    description = data.get("description", "").strip()
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    if not month or not category or amount <= 0:
        return jsonify({"error": "Invalid input parameters provided."}), 400

    new_expense = Expense(
        user_id=current_user.id,
        month=month,
        category=category,
        amount=amount,
        description=description,
        date=date,
    )
    db.session.add(new_expense)
    db.session.commit()

    return jsonify({"message": "Expense successfully recorded", "id": new_expense.id}), 201


@app.route("/api/expense/<int:expense_id>", methods=["DELETE"])
@login_required
def delete_expense(expense_id):
    """Deletes an expense item owned by current user."""
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    return jsonify({"message": "Expense deleted successfully"})


@app.route("/api/goals", methods=["GET", "POST"])
@login_required
def handle_goals():
    """Lists or creates savings goals for current user."""
    if request.method == "POST":
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        target_amount = float(data.get("target_amount", 0.0))
        deadline = data.get("deadline", "")

        if not name or target_amount <= 0:
            return jsonify({"error": "Valid name and target amount are required."}), 400

        goal = Goal(
            user_id=current_user.id,
            name=name,
            target_amount=target_amount,
            current_amount=0.0,
            deadline=deadline if deadline else None,
        )
        db.session.add(goal)
        db.session.commit()
        return jsonify({"message": "Goal created successfully", "id": goal.id}), 201

    goals = Goal.query.filter_by(user_id=current_user.id).all()
    return jsonify(
        [
            {
                "id": g.id,
                "name": g.name,
                "target_amount": g.target_amount,
                "current_amount": g.current_amount,
                "deadline": g.deadline,
            }
            for g in goals
        ]
    )


@app.route("/api/goals/<int:goal_id>/contribute", methods=["POST"])
@login_required
def contribute_goal(goal_id):
    """Adds a contribution to an existing savings goal."""
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    amount = float(data.get("amount", 0.0))

    if amount <= 0:
        return jsonify({"error": "Contribution amount must be greater than zero."}), 400

    goal.current_amount += amount
    db.session.commit()
    return jsonify({"message": f"Contributed ${amount:.2f} to {goal.name}!"})


@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
@login_required
def delete_goal(goal_id):
    """Deletes a goal owned by current user."""
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"message": "Goal deleted successfully"})


@app.route("/api/export/csv", methods=["GET"])
@login_required
def export_csv():
    """Generates a downloadable CSV summary report for the requested month."""
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    incomes = Income.query.filter_by(user_id=current_user.id, month=month).all()
    expenses = Expense.query.filter_by(user_id=current_user.id, month=month).all()
    goals = Goal.query.filter_by(user_id=current_user.id).all()

    total_inc = sum(i.amount for i in incomes)
    total_exp = sum(e.amount for e in expenses)
    net_sav = total_inc - total_exp

    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Summary Section
    writer.writerow(["PERSONAL FINANCE ADVISOR BOT - MONTHLY REPORT"])
    writer.writerow(["User", current_user.username])
    writer.writerow(["Month", month])
    writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])
    writer.writerow(["SUMMARY METRICS"])
    writer.writerow(["Total Income", f"${total_inc:.2f}"])
    writer.writerow(["Total Expenses", f"${total_exp:.2f}"])
    writer.writerow(["Net Savings", f"${net_sav:.2f}"])
    savings_rate = (net_sav / total_inc * 100) if total_inc > 0 else 0
    writer.writerow(["Savings Rate", f"{savings_rate:.1f}%"])
    writer.writerow([])

    # 2. Income Details
    writer.writerow(["INCOME BREAKDOWN"])
    writer.writerow(["Date", "Source / Client", "Amount"])
    for inc in incomes:
        writer.writerow([inc.date, inc.source, f"${inc.amount:.2f}"])
    if not incomes:
        writer.writerow(["No income logged for this month."])
    writer.writerow([])

    # 3. Expense Details
    writer.writerow(["EXPENSE TRANSACTIONS"])
    writer.writerow(["Date", "Category", "Description", "Amount"])
    for exp in expenses:
        writer.writerow([exp.date, exp.category, exp.description or "-", f"${exp.amount:.2f}"])
    if not expenses:
        writer.writerow(["No expenses recorded for this month."])
    writer.writerow([])

    # 4. Goals Progress
    writer.writerow(["ACTIVE SAVINGS GOALS"])
    writer.writerow(["Goal Name", "Target Amount", "Saved Amount", "Progress (%)", "Deadline"])
    for g in goals:
        pct = (g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0
        writer.writerow([g.name, f"${g.target_amount:.2f}", f"${g.current_amount:.2f}", f"{pct:.1f}%", g.deadline or "Ongoing"])
    if not goals:
        writer.writerow(["No active goals set."])

    csv_data = output.getvalue()
    filename = f"finance_report_{current_user.username}_{month}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"},
    )


# ==========================================
# Main Entry Point with Optional Ngrok Support
# ==========================================
if __name__ == "__main__":
    # Check if Ngrok flag was passed or enabled via env
    use_ngrok = "--ngrok" in sys.argv or os.environ.get("USE_NGROK", "").lower() in ("true", "1")
    port = int(os.environ.get("PORT", 5000))

    if use_ngrok:
        try:
            from pyngrok import ngrok
            # Configure authtoken if present in .env or environment
            auth_token = os.environ.get("NGROK_AUTHTOKEN")
            if auth_token:
                ngrok.set_auth_token(auth_token.strip())
            # Open HTTP tunnel on port 5000
            public_url = ngrok.connect(addr=str(port)).public_url
            print("\n" + "=" * 60)
            print(">>> NGROK TUNNEL ACTIVE <<<")
            print(f"[*] Public URL: {public_url}")
            print(f"[*] Local URL:  http://127.0.0.1:{port}")
            print("=" * 60 + "\n")
        except Exception as e:
            print("\n" + "=" * 60)
            print("[!] Ngrok Tunnel Notice:")
            print(f"   {e}")
            print("[*] Tip: Ngrok requires a free auth token to create tunnels.")
            print("   1. Sign up for free: https://dashboard.ngrok.com/signup")
            print("   2. Copy your authtoken: https://dashboard.ngrok.com/get-started/your-authtoken")
            print("   3. Add to your .env file: NGROK_AUTHTOKEN=your_token_here")
            print("=" * 60 + "\n")
            print("Continuing in local-only mode.")

    debug_mode = os.environ.get("FLASK_ENV") == "development" or os.environ.get("DEBUG", "").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)