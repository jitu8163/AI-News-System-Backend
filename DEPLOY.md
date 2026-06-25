# Deployment (Docker Compose) — two separate repos

The app is split into two independent GitHub repos:

- **backend** (this repo) — FastAPI + scheduler, the `docker-compose.yml`, and `.env`
- **frontend** — the React/Vite app + its nginx config

`docker-compose.yml` lives here in the backend repo and builds the frontend from
a sibling `../frontend` clone. On the server you clone **both** repos side-by-side.

## Architecture

```
            :80
 Internet ──────► [ frontend / nginx ]  ── /api ──► [ backend (uvicorn :8001) ] ──► [ db (postgres) ]
                   (frontend repo)              (this repo)                          volume: pgdata
```

The frontend calls the API at the relative path `/api`, so nginx is the only
component that needs to know where the backend is (`backend:8001`, the compose
service name).

## 1. Firewall / security group
Allow inbound **22** (SSH) and **80** (HTTP).

## 2. Install Docker (first time only, Ubuntu)
```bash
ssh -i python_server_key.pem ubuntu@<SERVER_IP>
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # then log out/in so the group applies
docker compose version
```

## 3. Clone both repos as siblings
The folder names **must** be `backend` and `frontend` (the compose file builds `../frontend`):
```bash
mkdir -p ~/wohana && cd ~/wohana
git clone https://github.com/jitu8163/wohana_news_backend.git  backend
git clone https://github.com/jitu8163/wohana_news_frontend.git frontend
```

## 4. Configure secrets (in the backend repo)
```bash
cd ~/wohana/backend
cp .env.example .env
nano .env     # set POSTGRES_PASSWORD, SECRET_KEY, GROQ_API_KEY, ADMIN_PASSWORD
```
`DATABASE_URL` must use host `db` and the same password as `POSTGRES_PASSWORD`
(URL-encode special chars, e.g. `@` → `%40`).

## 5. Build and start (run from the backend repo)
```bash
cd ~/wohana/backend
docker compose up -d --build
```
On first boot the backend waits for Postgres, runs Alembic migrations, and seeds
the admin user + keywords.

## 6. Verify
```bash
docker compose ps
docker compose logs -f backend
curl -fsS http://localhost/api/health
```
Open **http://<SERVER_IP>**, log in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`, and hit
**Fetch Now** on the dashboard.

## Redeploying after code changes
```bash
cd ~/wohana/backend && git pull        # backend changes
cd ~/wohana/frontend && git pull       # frontend changes
cd ~/wohana/backend && docker compose up -d --build
```

## Common operations (run from ~/wohana/backend)
```bash
docker compose logs -f backend
docker compose restart backend
docker compose down            # stop (keeps the pgdata volume)
docker compose down -v         # stop AND delete the DB volume (DESTRUCTIVE)
docker compose exec db psql -U postgres -d wohana_news -c "\dt"
```

## Adding HTTPS later
Point a domain at the server IP, then add Certbot/Let's Encrypt + a `:443` server
block to the frontend repo's `nginx.conf`, or front the stack with Caddy /
Cloudflare / an ALB terminating TLS on port 80.
