# Deployment Guide

You have a **FastAPI Backend** (Python) and a **React Frontend** (Node.js). You also use a **SQLite Database** (`pm_agent.db`).

## Option 1: Vercel (Frontend) + Render (Backend) [Recommended for Free Tier]

This approach allows you to host the frontend on Vercel (fast, easy) and the backend on Render (supports Python).

### ⚠️ Critical Note on Database
Your application uses **SQLite**, which is a file-based database.
- **Vercel**: Does NOT support persistent SQLite files. Your data will be deleted after every request.
- **Render (Free)**: Does NOT support persistent disks. Your data will be deleted every time the server restarts (approx. every 15 mins of inactivity).

**Solution**: To host this properly, you should switch to a cloud database like **Supabase (PostgreSQL)** or use a hosting provider with persistent storage (like Railway or a VPS).

---

## Option 2: Railway.app (Easiest for Full Stack)

Railway is excellent because it can host your Backend, Frontend, and a PostgreSQL database all in one project.

1. **Create a Railway Account**.
2. **New Project** -> **Provision PostgreSQL**.
3. **Connect Backend**:
   - Link your GitHub repo.
   - Add variables from your `.env`.
   - Update `db/models.py` to use `DATABASE_URL` (Postgres) instead of `sqlite:///./pm_agent.db`.
4. **Connect Frontend**:
   - Link your GitHub repo (frontend folder).
   - Set `REACT_APP_API_URL` to your Railway Backend URL.

---

## Option 3: AWS EC2 (Virtual Machine)

If you want to keep **SQLite** and run it exactly like you do locally:

1. **Launch an Ubuntu EC2 Instance**.
2. **Clone your repo**.
3. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip nodejs npm nginx
   pip install -r requirements.txt
   cd frontend && npm install && npm run build
   ```
4. **Run Backend** (using `systemd` or `nohup`).
5. **Serve Frontend** using Nginx.

---

## Can I deploy to Vercel?

**Yes, but with caveats:**

1. **Frontend**: Yes, easily.
   - Command: `npm run build`
   - Output Directory: `build`
   
2. **Backend**: Yes, but **SQLite will not work**.
   - You must migrate to a cloud database (e.g., Supabase, Neon).
   - You need to configure `vercel.json` to handle Python serverless functions.

### How to Deploy Frontend to Vercel

1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` inside the `frontend` folder.
3. Follow the prompts.
4. Add Environment Variable: `REACT_APP_API_URL` pointing to your deployed backend.
