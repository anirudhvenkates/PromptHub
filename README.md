# PromptHub

A minimal end‑to‑end implementation of the assignment:
- User **registration & login**
- Create **projects/agents**
- Store a **system prompt** per project
- **Chat interface** that calls the **OpenAI Responses API**

> Optional file uploads are omitted for brevity but can be added later.

## Tech
- Python 3.10+
- Flask, SQLAlchemy (SQLite)
- Simple session auth (cookies)
- OpenAI Responses API

## Run locally
```bash
# 1) Create virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install deps
pip install -r requirements.txt

# 3) Configure env
cp .env.example .env
# edit .env and set OPENAI_API_KEY, SECRET_KEY, JWT_SECRET_KEY if you want

# 4) Initialize DB
flask --app app.py init-db

# 5) Start dev server
flask --app app.py run
# open http://127.0.0.1:5000
```
