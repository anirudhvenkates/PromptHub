import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import bcrypt
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
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

# --- Simple uploads (per project; filesystem only) ---
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'txt','md','pdf','png','jpg','jpeg','gif','csv','json'}
def allowed_file(name: str) -> bool:
    return '.' in name and name.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def project_upload_dir(project_id: int) -> str:
    d = os.path.join(app.config['UPLOAD_FOLDER'], str(project_id))
    os.makedirs(d, exist_ok=True)
    return d

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
    # gather per-project files (names only)
    d = project_upload_dir(project_id)
    file_names = [f for f in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, f))]
    return render_template("project.html", project=p, files=file_names)

@app.route("/projects/<int:project_id>/update", methods=["POST"])
@login_required
def update_project(project_id):
    p = Project.query.filter_by(id=project_id, user_id=current_user().id).first_or_404()
    p.name = request.form.get("name", p.name)
    p.system_prompt = request.form.get("system_prompt", p.system_prompt)
    db.session.commit()
    return redirect(url_for("project_detail", project_id=project_id))

# --- Simple file upload/list/download ---
@app.post("/projects/<int:project_id>/files")
@login_required
def upload_file(project_id):
    # ownership check
    Project.query.filter_by(id=project_id, user_id=current_user().id).first_or_404()

    if 'file' not in request.files:
        flash("No file part","error")
        return redirect(url_for("project_detail", project_id=project_id))

    f = request.files['file']
    if f.filename == '':
        flash("No selected file","error")
        return redirect(url_for("project_detail", project_id=project_id))

    if not allowed_file(f.filename):
        flash("File type not allowed","error")
        return redirect(url_for("project_detail", project_id=project_id))

    safe = secure_filename(f.filename)
    dest_dir = project_upload_dir(project_id)
    dest_path = os.path.join(dest_dir, safe)

    # If same name exists, append a counter suffix (e.g., "file (1).pdf")
    base, ext = os.path.splitext(safe)
    i = 1
    while os.path.exists(dest_path):
        safe = f"{base} ({i}){ext}"
        dest_path = os.path.join(dest_dir, safe)
        i += 1

    f.save(dest_path)
    flash("File uploaded","success")
    return redirect(url_for("project_detail", project_id=project_id))

@app.get("/projects/<int:project_id>/files")
@login_required
def list_files(project_id):
    # ownership check
    Project.query.filter_by(id=project_id, user_id=current_user().id).first_or_404()
    d = project_upload_dir(project_id)
    files = []
    for fname in sorted(os.listdir(d)):
        pth = os.path.join(d, fname)
        if os.path.isfile(pth):
            files.append({"name": fname, "size": os.path.getsize(pth)})
    return jsonify(files), 200

@app.get("/projects/<int:project_id>/files/<path:filename>")
@login_required
def download_file(project_id, filename):
    # ownership check
    Project.query.filter_by(id=project_id, user_id=current_user().id).first_or_404()
    return send_from_directory(project_upload_dir(project_id), filename, as_attachment=True)

# --- Chat API (OpenRouter only) ---
@app.route("/api/projects/<int:project_id>/chat", methods=["POST"])
@login_required
def api_chat(project_id):
    p = Project.query.filter_by(id=project_id, user_id=current_user().id).first_or_404()
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENROUTER_API_KEY not configured on server"}), 500

    model = os.getenv("OPENROUTER_MODEL", "openrouter/auto")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
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
