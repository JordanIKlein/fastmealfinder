# Fast Meal Finder 🍟
Location: https://www.fastmealfinder.com

Changelog:
- v1.0 (coming-soon): Coming Soon Page. Released with HTTPS. **12/17/2024**
- v1.1 Upcoming Work (initial-launch): Beta Product Release. **4/3/2025**
- v1.2 Stable (main): Launch with OSM data and basic reward links **4/8/2025**
- v2.0 Stable (august-update):  Relaunched with Boston focus **8/25/2025**
- v2.1 Stable (dev): Addressing formatting/stylistic choices, Doordash and Uber Eats integration **9/21/2025**
- v2.2 Stable (dev): Adding deals to existing restaurants **TBD**

## Quickstart (Windows)

This guide shows how to install and run Fast Meal Finder locally on Windows using a PostgreSQL database with the PostGIS extension.

### Prerequisites
- Python 3.10+ (recommend 64-bit) and `pip`
- PostgreSQL (14+ recommended)
- PostGIS extension for PostgreSQL
- Optional: `psql` CLI on your PATH for running SQL commands

Links: Install PostgreSQL using the official installer; during or after installation, add PostGIS using Stack Builder or your package’s PostGIS option. After install, you’ll enable the extension inside your database with `CREATE EXTENSION postgis;`.

### 1) Clone and set up Python env
```cmd
cd c:\GitHub
git clone https://github.com/JordanIKlein/fastmealfinder.git
cd fastmealfinder

python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Create the database (PostgreSQL + PostGIS)
Create a database user and database, then enable PostGIS and load the schema. Replace passwords/usernames if desired.

Using `psql` from a terminal:
```cmd
psql -U postgres -h localhost -c "CREATE USER fmf_user WITH PASSWORD 'fmf_password';"
psql -U postgres -h localhost -c "CREATE DATABASE fastmealfinder OWNER fmf_user;"
psql -U postgres -h localhost -d fastmealfinder -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -U fmf_user -h localhost -d fastmealfinder -f SQL\schema.sql
```

Notes:
- If `psql` isn’t recognized, add PostgreSQL’s `bin` folder to your PATH or run the commands via pgAdmin’s Query Tool.
- The current schema (`SQL/schema.sql`) doesn’t require PostGIS types yet, but PostGIS must be installed/enabled for upcoming geospatial features.

### 3) Configure environment variables (.env)
Create a `.env` file in the project root using the provided example, and update values for your environment.
```cmd
copy .env.example .env
```
Then edit `.env` and set at minimum the DB fields and a secret key:
- `DB_NAME=fastmealfinder`
- `DB_USER=fmf_user`
- `DB_PASSWORD=fmf_password`
- `DB_HOST=localhost`
- `FLASK_SECRET_KEY=` a random string (generate one below)

Generate a strong secret key (copy the output into `.env`):
```cmd
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Optional variables (feature toggles):
- `MAILCHIMP_API_KEY` and `MAILCHIMP_LIST_ID` for email signups
- `GOOGLE_ANALYTICS_ID` if you want analytics locally

### 4) Run the app
```cmd
.venv\Scripts\activate
python app.py
```
Visit http://127.0.0.1:5000 in your browser.

## Troubleshooting
- "Failed to create connection pool": check `.env` values (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`) and that PostgreSQL is running.
- `psql` not found: add PostgreSQL’s `bin` folder to PATH or use pgAdmin to run the SQL.
- PostGIS errors: ensure you ran `CREATE EXTENSION postgis;` while connected to the `fastmealfinder` database.

## Environment Variables
The app loads environment variables via `python-dotenv` from a `.env` file in the repo root. The main variables are:

Required for DB connection (used by `pool_connection.py`):
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`

Recommended:
- `FLASK_SECRET_KEY`: any strong random string for Flask session security

Optional integrations:
- `MAILCHIMP_API_KEY`, `MAILCHIMP_LIST_ID`
- `GOOGLE_ANALYTICS_ID`

## Notes
- Local dev server runs on port 5000 with `debug=True` (see `app.py`).
- Database schema is in `SQL/schema.sql`. You can re-run it safely on a fresh DB.
- Static assets are served from `/static`; HTML templates live in `/templates`.