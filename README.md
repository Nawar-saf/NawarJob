# NawarJob

A Dockerized project discovery and lead-management system.

## Stack

- FastAPI
- PostgreSQL 17
- SQLAlchemy
- Docker Compose
- Static public site
- Private lead CRM

## Run locally

```bash
cp .env.example .env
# Replace the database password and ADMIN_KEY values in .env
docker compose up -d --build
```

Open:

- Public site: `http://localhost:8000`
- Admin CRM: `http://localhost:8000/admin`
- Health check: `http://localhost:8000/health`

The public application form writes directly to PostgreSQL through the FastAPI API. Leads are scored automatically and can be moved through:

`New -> Contacted -> Qualified -> Proposal -> Won / Lost`

## Before production

Use long random values for `POSTGRES_PASSWORD` and `ADMIN_KEY`, put the app behind HTTPS/reverse proxy, and do not commit `.env`.
