# OKF Knowledge Store (Cloud Deployment Ready)

A cloud-native system to store, search, and manage OKF (Open Knowledge Format) knowledge graphs in PostgreSQL. Exposes a **REST API**, a **Visual Web Dashboard**, and an **MCP (Model Context Protocol) SSE Server** for AI model integration.

---

## 🏗️ Architecture

```text
[ Markdown OKF Files ] ---> Local Ingest Script ---> [ Cloud PostgreSQL (Supabase/Railway) ]
                                                                  ▲
                                                                  │
                                                        [ FastAPI Cloud Service ]
                                                        (Railway / Render / Fly.io)
                                                        ├── Web Dashboard (JWT Auth)
                                                        ├── REST API (X-API-Key Auth)
                                                        └── MCP SSE Server (/mcp/sse)
```

---

## ☁️ Step-by-Step Cloud Deployment

### Step 1: Create a Free Cloud Database (Supabase)
1. Go to [Supabase.com](https://supabase.com) and create a free project.
2. In Project Settings -> **Database**, copy your **PostgreSQL Connection String** (URI).

### Step 2: Push Repository to GitHub
1. Push this folder to a GitHub repository (Public or Private).

### Step 3: Deploy API Service (Railway or Render)

#### Option A: Railway.app (Recommended)
1. Go to [Railway.app](https://railway.app) and create a new project.
2. Select **Deploy from GitHub repo** and choose your repository.
3. In **Variables**, add:
   - `DATABASE_URL`: *(Your Supabase Connection String)*
   - `API_KEY`: *(Your secret API key, e.g. `xvAEWCbZkT30J8zUdMPLsXO9G6B1V7Nw`)*
   - `JWT_SECRET`: *(A random secret for user logins)*
4. Railway will automatically detect the root `Dockerfile` and deploy.
5. Generate a domain under **Settings -> Networking -> Public Networking** (e.g. `https://okf-store-production.up.railway.app`).

---

### Step 4: Ingest your OKF Data into Cloud DB

Run the ingest script from your local machine to upload all OKF files directly to your cloud PostgreSQL database:

```powershell
pip install -r ingest/requirements.txt
python ingest/ingest.py -p "./output (5)" --db-url "YOUR_SUPABASE_DATABASE_URL"
```

---

## 🌐 Production Endpoints

Once deployed at `https://your-app.up.railway.app`:

- **Web Dashboard**: `https://your-app.up.railway.app/`
- **REST API Search**: `GET https://your-app.up.railway.app/api/search?q=...` (Header: `X-API-Key`)
- **MCP SSE Server**: `https://your-app.up.railway.app/mcp/sse?api_key=YOUR_API_KEY`
- **API Docs (Swagger)**: `https://your-app.up.railway.app/docs`

---

## 🤖 Connecting AI Models

### MCP Clients (Claude Desktop / Cursor)
Add to config:
```json
{
  "mcpServers": {
    "okf-knowledge": {
      "url": "https://your-app.up.railway.app/mcp/sse?api_key=YOUR_API_KEY"
    }
  }
}
```

### Python SDK / Gemini / OpenAI
Query `GET https://your-app.up.railway.app/api/search?q=query` with header `X-API-Key`.
# ark
