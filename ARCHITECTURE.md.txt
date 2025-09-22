# PromptHub – Architecture

This document explains the architecture and design decisions of PromptHub, a minimal chatbot platform.

---

## 1. High-Level Overview

PromptHub is a Flask-based web app that allows users to:
- Register and log in
- Create projects/agents
- Define a system prompt per project
- Chat with projects through the OpenRouter API
- Upload files into projects

The system is intentionally minimal but designed with extensibility in mind.

---

## 2. Core Components

### 2.1 Frontend (Browser)
- Rendered via Jinja2 templates (`base.html`, `dashboard.html`, `project.html`).
- Provides forms for registration, login, and project creation.
- Project page contains:
  - Editable project name and system prompt
  - A chat interface with bubbles (JavaScript fetch calls to the backend)
  - A file upload form and list of uploaded files

### 2.2 Backend (Flask App)
- **Auth & Sessions**
  - Simple cookie-based session authentication (`session["uid"]`).
  - Login required for all project and chat routes.
- **Project Management**
  - CRUD operations for projects linked to a user.
  - System prompt stored per project.
- **Chat API**
  - `/api/projects/<id>/chat`
  - Accepts a user message, prepends the system prompt, forwards to OpenRouter, and returns the response.
- **File Uploads**
  - `/projects/<id>/files` (POST multipart form data)
  - Saves files under `instance/uploads/<project_id>/`
  - `/projects/<id>/files` (GET) returns JSON file list
  - `/projects/<id>/files/<filename>` serves files back for download

### 2.3 Database
- SQLite via SQLAlchemy ORM
- Tables:
  - `users(id, email, password_hash)`
  - `projects(id, user_id, name, system_prompt)`
- Minimal schema to keep the demo lightweight.

### 2.4 External API
- **OpenRouter Completion API**
  - Endpoint: `https://openrouter.ai/api/v1/chat/completions`
  - Headers: Authorization with API key
  - Payload: System + user messages
  - Response: Extracts first message content

---

## 3. Request Flows

### 3.1 Authentication
1. User submits email/password to `/login`.
2. Flask checks DB → sets `session["uid"]`.
3. Protected routes use `@login_required`.

### 3.2 Project Lifecycle
1. User posts to `/projects/create`.
2. New project is stored in DB with name + system prompt.
3. User can update via `/projects/<id>/update`.

### 3.3 Chat
1. JS in browser calls `/api/projects/<id>/chat` with message.
2. Flask loads project/system prompt.
3. Flask calls OpenRouter → returns reply JSON.
4. Browser renders chat bubble.

### 3.4 File Upload
1. User submits form with file.
2. Flask saves under `instance/uploads/<project_id>/`.
3. Filenames listed and linked on project page.

---

## 4. Diagram

![Architecture Diagram](architecture_diagram.png)

---

## 5. Non-Functional Requirements

- **Scalability**  
  - Multi-user support via `user_id` scoping.  
  - SQLite for demo; can be swapped for Postgres/MySQL.

- **Security**  
  - Session auth, password hashing via `passlib[bcrypt]`.  
  - Basic ownership checks on project and file routes.  
  - For production: HTTPS, CSRF protection, stricter auth (JWT/OAuth).

- **Extensibility**  
  - Clear separation of users, projects, chat.  
  - Easy to add analytics, integrations, or alternate LLM providers.

- **Performance**  
  - Low latency: small Flask app, direct API calls.  
  - Could add response streaming (Server-Sent Events).

- **Reliability**  
  - Error handling on external API calls.  
  - Safe file storage with `secure_filename`.

---

## 6. Trade-offs

- Simplicity favored over production-hardening:
  - Session auth over JWT.
  - Local file storage instead of cloud storage.
  - SQLite instead of a full RDBMS.
- These choices make the system easier to set up and demonstrate, but less suitable for scaling without modification.

---

## 7. Future Improvements

- Switch to JWT/OAuth2 for API clients.  
- Add support for multiple models/providers.  
- Store chat history in DB.  
- Move uploads to cloud (S3/GCS).  
- Add streaming responses for better UX.  
- Deploy on Render/Fly/Railway for public demo.

---

**Summary:**  
PromptHub is a deliberately minimal implementation that covers all core assignment requirements while leaving room for clear future improvements. It demonstrates user/project management, prompt storage, chat integration with OpenRouter, and per-project file uploads.
