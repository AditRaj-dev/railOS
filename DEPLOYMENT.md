# RailOS — Deployment Guide

This guide outlines deployment options for RailOS services: the FastAPI backend optimizer and the Next.js 16 Web Control Center.

---

## 1. Quick Start with Docker Compose (Recommended)

To deploy the entire RailOS stack locally or on any cloud VM (AWS EC2, GCP Compute Engine, DigitalOcean, Hetzner):

```bash
# Clone the repository
git clone https://github.com/AditRaj-dev/railOS.git
cd railOS

# Build and launch all services
docker compose up --build -d
```

### Endpoints
* **Web Control Center**: `http://<your-host>:3000`
* **RailOS API & Optimizer**: `http://<your-host>:8000`
* **Interactive API Documentation (Swagger)**: `http://<your-host>:8000/docs`

---

## 2. Cloud Platform Deployments

### A. Vercel (Frontend Control Center)
1. Import `https://github.com/AditRaj-dev/railOS` in Vercel.
2. Set **Root Directory** to `apps/control-center`.
3. Set **Framework Preset** to `Next.js`.
4. Configure Environment Variables:
   * `NEXT_PUBLIC_RAILOS_API_URL`: `https://<your-backend-domain>`
   * `NEXT_PUBLIC_MAP_STYLE_URL`: `street`
   * `NEXT_PUBLIC_RAILOS_MODE`: `synthetic`
5. Deploy.

### B. Railway / Render / Fly.io (Backend API)
* **Build Context**: Root of repository (`.`)
* **Dockerfile**: `Dockerfile.api`
* **Port**: `8000`
* **Environment Variables**:
  * `PORT`: `8000`
  * `PYTHONUNBUFFERED`: `1`
  * `RAILOS_STORAGE_BACKEND`: `memory` (or `postgres` with `DATABASE_URL` configured)

---

## 3. Flutter Android Field App Build

The field app's API base URL now defaults to the deployed Render backend
(`https://railos-api.onrender.com`), so a plain release build already points
at production:

```bash
cd apps/field-app
flutter pub get
flutter build apk --release
```

To point at a different backend instead (a staging deploy, or a local
server for testing), override the default:

```bash
flutter build apk --release --dart-define=RAILOS_API_BASE=https://<your-backend-api-url>
```

The output APK will be generated at:
`apps/field-app/build/app/outputs/flutter-apk/app-release.apk`
