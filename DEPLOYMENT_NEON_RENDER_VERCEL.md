# RailOS Production Deployment Guide
## Frontend on Vercel · Backend on Render · Database & Storage on Neon

This step-by-step guide explains how to deploy the entire RailOS architecture to production using cloud-native managed services:

```
┌─────────────────────────────────┐
│     Vercel (Frontend)           │
│   Next.js 16 Control Center     │
│   https://railos.vercel.app     │
└────────────────┬────────────────┘
                 │ REST / SSE
                 ▼
┌─────────────────────────────────┐
│     Render (Backend API)        │
│   FastAPI + CP-SAT Optimizer    │
│   https://railos-api.onrender.com
└───────┬─────────────────┬───────┘
        │ SQL             │ S3 / Blob
        ▼                 ▼
┌──────────────────┐    ┌─────────────────────────┐
│ Neon PostgreSQL  │    │ Neon / S3 Object Store  │
│ (State / Audit)  │    │ (Field USFD Evidence)   │
└──────────────────┘    └─────────────────────────┘
```

---

## Prerequisites

1. GitHub account with access to [https://github.com/AditRaj-dev/railOS](https://github.com/AditRaj-dev/railOS).
2. [Neon Account](https://neon.tech) (Free tier available).
3. [Render Account](https://render.com) (Free tier available).
4. [Vercel Account](https://vercel.com) (Free tier available).

---

## Phase 1: Database & Storage Setup on Neon

### Step 1.1: Create a PostgreSQL Database
1. Log in to [Neon Console](https://console.neon.tech/).
2. Click **Create Project**:
   * **Project Name**: `railos-production`
   * **Postgres Version**: `16` or `17`
   * **Region**: Select a region close to your Render deployment (e.g. `US East (N. Virginia)` or `EU Central (Frankfurt)`).
3. Once created, copy the **Connection String** from the dashboard.
4. Ensure it has `sslmode=require`, for example:
   ```text
   postgresql://neondb_owner:npg_xxxxxx@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   *(RailOS automatically runs the initial schema migration and seeds default state on first connect).*

### Step 1.2: Set Up Neon / S3 Object Storage Bucket
If you are storing field photographs and USFD flaw evidence:
1. In your Neon console (or an S3-compatible provider such as AWS S3, Cloudflare R2, or MinIO), obtain:
   * **Bucket Name**: e.g., `railos-evidence`
   * **Access Key ID**: e.g., `NEON_ACCESS_KEY`
   * **Secret Access Key**: e.g., `NEON_SECRET_KEY`
   * **Endpoint URL**: e.g., `https://<account-id>.r2.cloudflarestorage.com` or `https://s3.us-east-2.amazonaws.com`

---

## Phase 2: Backend API Deployment on Render

RailOS includes both a Dockerfile (`Dockerfile.api`) and a Render Blueprint (`render.yaml`).

### Method A: 1-Click Blueprint Deploy (Recommended)
1. Go to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** → **Blueprint**.
3. Select your repository: `AditRaj-dev/railOS`.
4. Render will read `render.yaml` and prompt you for the un-synced variables:
   * **`DATABASE_URL`**: Paste your Neon connection string from Phase 1.
   * **`NEON_STORAGE_BUCKET`**: (Optional) Your bucket name.
   * **`NEON_STORAGE_KEY`**: (Optional) Storage access key.
   * **`NEON_STORAGE_SECRET`**: (Optional) Storage secret key.
   * **`NEON_STORAGE_ENDPOINT`**: (Optional) Storage endpoint.
5. Click **Apply**. Render will automatically build the container and deploy the service.

---

### Method B: Manual Web Service Setup
If creating the service manually on Render:
1. Click **New +** → **Web Service**.
2. Connect your `AditRaj-dev/railOS` GitHub repository.
3. Configure the settings:
   * **Name**: `railos-api`
   * **Region**: Same or close to your Neon database region
   * **Language**: `Docker`
   * **Branch**: `main` (or `master`)
   * **Dockerfile Path**: `Dockerfile.api`
   * **Docker Context**: `.` *(root of the repository)*
   * **Instance Type**: `Free` (or higher)
4. Add the following **Environment Variables**:

| Key | Value | Notes |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port container listens on |
| `PYTHONUNBUFFERED` | `1` | Ensures real-time logs |
| `RAILOS_STORAGE_BACKEND` | `postgres` | Instructs API to connect to Neon |
| `DATABASE_URL` | `postgresql://neondb_owner:xxx@.../neondb?sslmode=require` | Your Neon Postgres URI |
| `RAILOS_JWT_SECRET` | *(Generate a 32+ char random string)* | `openssl rand -hex 32` |
| `RAILOS_CORS_ORIGINS` | `https://*.vercel.app,http://localhost:3000` | Whitelists Vercel frontend |
| `ENABLE_SYNTHETIC_AUTH` | `true` | Enables role-switching in demo |
| `NEON_STORAGE_BUCKET` | *(Optional)* `railos-evidence` | Evidence photo bucket |
| `NEON_STORAGE_KEY` | *(Optional)* AWS/Neon Key | Bucket Key |
| `NEON_STORAGE_SECRET` | *(Optional)* AWS/Neon Secret | Bucket Secret |
| `NEON_STORAGE_ENDPOINT` | *(Optional)* S3 Endpoint URL | Custom endpoint if applicable |

5. Under **Health Check Path**, set:
   ```text
   /docs
   ```
6. Click **Create Web Service**.

### Step 2.3: Verify Backend
Once deployment completes (Status: *Live*), note your Render URL (e.g. `https://railos-api.onrender.com`).
Visit:
* `https://railos-api.onrender.com/docs` (Swagger UI)
* `https://railos-api.onrender.com/health` (Should return `{"status":"ok","storageBackend":"postgres"}`)

---

## Phase 3: Frontend Web Control Center Deployment on Vercel

### Step 3.1: Import Project in Vercel
1. Go to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository: `AditRaj-dev/railOS`.

### Step 3.2: Configure Root Directory & Build Settings
1. In the **Project Settings**:
   * **Framework Preset**: `Next.js`
   * **Root Directory**: Click **Edit** and choose `apps/control-center`.
2. Expand **Environment Variables** and add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_RAILOS_API_URL` | `https://railos-api.onrender.com` | Your deployed Render backend URL (no trailing slash) |
| `NEXT_PUBLIC_MAP_STYLE_URL` | `street` | Basemap preset (`street`, `dark`, `satellite`, `topo`) |
| `NEXT_PUBLIC_RAILOS_MODE` | `production` | Production mode |

3. Click **Deploy**.

### Step 3.3: Verify Frontend
Once the build completes (usually ~45-60 seconds):
1. Click the generated Vercel domain (e.g., `https://railos-control-center.vercel.app`).
2. Verify:
   * **Live Territory & Map**: Pan and zoom the geographic India track network.
   * **Possessions Board**: `/possessions` displays active railway possessions.
   * **API Event Stream**: The status bar shows a green connected indicator.

---

## Phase 4: Final Linkage & CORS Hardening

Once you know your exact Vercel production domain:
1. Go back to your **Render Dashboard** → `railos-api` → **Environment**.
2. Update `RAILOS_CORS_ORIGINS`:
   ```text
   https://railos-control-center.vercel.app,https://*.vercel.app,http://localhost:3000
   ```
3. Save changes. Render will automatically perform a zero-downtime redeploy with the updated CORS policy.

---

## Summary of Secrets Matrix

| Secret / Config | Destination Service | Example |
| :--- | :--- | :--- |
| Neon Postgres URI | Render (`DATABASE_URL`) | `postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require` |
| Neon Storage S3 Credentials | Render (`NEON_STORAGE_*`) | Bucket name, Access Key, Secret Key |
| JWT Signing Secret | Render (`RAILOS_JWT_SECRET`) | 64-char hexadecimal string |
| Render API Public URL | Vercel (`NEXT_PUBLIC_RAILOS_API_URL`) | `https://railos-api.onrender.com` |
| Vercel Production Domain | Render (`RAILOS_CORS_ORIGINS`) | `https://railos-control-center.vercel.app` |

---

## Troubleshooting

### 1. Render Free Tier Cold Starts
* The Render free tier spins down instances after 15 minutes of inactivity. The first request from Vercel may take 30–50 seconds to wake up the service.
* To prevent spin-downs during demos, set up a free uptime monitor (such as [UptimeRobot](https://uptimerobot.com)) to ping `https://<your-backend>.onrender.com/health` every 10 minutes.

### 2. Neon SSL Connection Errors
* Ensure the connection string includes `?sslmode=require`. The Python `psycopg` driver requires SSL when connecting to Neon clusters.

### 3. Vercel Static Map Tiles
* If your organization restricts third-party tile access, change `NEXT_PUBLIC_MAP_STYLE_URL` in Vercel to `dark` or provide a custom vector style URL in Vercel's environment variables.
