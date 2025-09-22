\
import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import bcrypt
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY","change-me")
db_url = os.getenv("DATABASE_URL","sqlite:///app.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    system_prompt = db.Column(db.Text, default="You are a helpful assistant.")

# --- Helpers ---
def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    return User.query.get(uid)

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

# --- Routes: Auth (session cookies for simplicity) ---
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not email or not password:
            flash("Email and password are required","error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered","error")
            return render_template("register.html")
        hashed = bcrypt.hash(password)
        u = User(email=email, password_hash=hashed)
        db.session.add(u)
        db.session.commit()
        flash("Registration successful. Please log in.","success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        u = User.query.filter_by(email=email).first()
        if not u or not bcrypt.verify(password, u.password_hash):
            flash("Invalid credentials","error")
            return render_template("login.html")
        session["uid"] = u.id
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=7)
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Routes: Projects ---
@app.route("/")
@login_required
def dashboard():
    u = current_user()
    projects = Project.query.filter_by(user_id=u.id).all()
    return render_template("dashboard.html", projects=projects, user=u)

@app.route("/projects/create", methods=["POST"])
@login_required
def create_project():
    name = request.form.get("name","Untitled Project").strip() or "Untitled Project"
    prompt = request.form.get("system_prompt","You are a helpful assistant.")
    p = Project(user_id=current_user().id, name=name, system_prompt=prompt)
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("project_detail", project_id=p.id))

@app.route("/projects/<int:project_id>")
@login_required
def project_detail(project_id):
    p = Project.query.filter_by(id=project_id, user_id=current_user().id).first_or_404()
    return render_template("project.html", project=p)

@app.route("/projects/<int:project_id>/update", methods=["POST"])
@login_required
def update_project(project_id):
    p = Project.query.filter_by(id=project_id, user_id=current_user().id).first_or_404()
    p.name = request.form.get("name", p.name)
    p.system_prompt = request.form.get("system_prompt", p.system_prompt)
    db.session.commit()
    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/api/projects/<int:project_id>/chat", methods=["POST"])
@login_required
def api_chat(project_id):
    p = Project.query.filter_by(id=project_id, user_id=current_user().id).first_or_404()
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    # --- OpenRouter only ---
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENROUTER_API_KEY not configured on server"}), 500

    model = os.getenv("OPENROUTER_MODEL", "openrouter/auto")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional but recommended:
        # "HTTP-Referer": os.getenv("APP_URL", "http://localhost:5000"),
        # "X-Title": "PromptHub",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": p.system_prompt or "You are a helpful assistant."},
            {"role": "user", "content": user_message},
        ],
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        j = resp.json()

        # Standard OpenAI-compatible extraction
        output_text = ""
        choices = (j or {}).get("choices") or []
        if choices and choices[0].get("message", {}).get("content"):
            output_text = choices[0]["message"]["content"]

        return jsonify({"reply": output_text or "[No response text received]"}), 200

    except requests.RequestException as e:
        return jsonify({"error": f"LLM request failed: {str(e)}"}), 502

# --- CLI: init DB ---
@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database initialized.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
