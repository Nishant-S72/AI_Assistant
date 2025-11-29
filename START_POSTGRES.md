# Starting Postgres for AI Chief-of-Staff

## Option 1: Using Docker (Recommended)

If you have Docker installed:

```bash
# Start Postgres
docker compose up -d postgres

# Check status
docker compose ps postgres

# View logs
docker compose logs postgres
```

## Option 2: Install Postgres via Homebrew

```bash
# Install Postgres
brew install postgresql@16

# Start Postgres service
brew services start postgresql@16

# Or run manually
pg_ctl -D /opt/homebrew/var/postgresql@16 start
```

## Option 3: Install Docker Desktop

If you don't have Docker:

1. Download Docker Desktop for Mac: https://www.docker.com/products/docker-desktop
2. Install and start Docker Desktop
3. Then run: `docker compose up -d postgres`

## Verify Postgres is Running

```bash
# Check if Postgres is accepting connections
pg_isready -h localhost -p 5432

# Or test connection
psql -h localhost -U postgres -d aichief -c "SELECT 1;"
```

## Database Connection String

The backend expects:
```
DATABASE_URL=postgres://postgres:postgres@localhost:5432/aichief
```

## Quick Start Script

Once Postgres is running, restart the backend:

```bash
cd backend
npm run build
PORT=3000 npm start
```

Then test the API:
```bash
curl http://localhost:3000/api/messages
```

You should see `[]` (empty array) or message data if seeded.

