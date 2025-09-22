# PromptHub

A minimal end-to-end implementation of the chatbot platform assignment:

- User **registration & login** (session cookies)
- Create **projects/agents**
- Store a **system prompt** per project
- **Chat interface** that calls the **OpenRouter Completion API**
- **Per-project file uploads** (list and download)

## Tech
- Python 3.10+
- Flask, SQLAlchemy (SQLite)
- Simple session auth (cookies)
- OpenRouter API

## Run locally
```bash
# 1) Create virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install deps
pip install -r requirements.txt

# 3) Configure env
cp .env.example .env
# edit .env and set:
#   SECRET_KEY = any string
#   DATABASE_URL = sqlite:///app.db
#   OPENROUTER_API_KEY = your key from https://openrouter.ai
#   OPENROUTER_MODEL = (optional, defaults to openrouter/auto)

# 4) Initialize DB
flask --app app.py init-db

# 5) Start dev server
python3 app.py
# open http://127.0.0.1:5000

## Features
- Register and log in with email and password.
- Create multiple projects per user.
- Update project name and system prompt.
- Chat with a project using OpenRouter models.
- Upload files into a project; see them listed and download them back.
- Simple web UI with chat bubbles.

## Notes
- Uses SQLite by default; change DATABASE_URL to use Postgres/MySQL.
- Uploaded files are stored under instance/uploads/<project_id>/.
- Session-based authentication is used to keep it simple.
- Code is intended for demonstration, not production.