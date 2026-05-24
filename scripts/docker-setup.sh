#!/usr/bin/env bash
# docker-setup.sh — start the Plane · Kiwi TCMS · Wiki.js · Harness CD stack
# and print a post-startup checklist.
#
# Run from the project root: bash scripts/docker-setup.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()  { echo -e "${CYAN}[setup]${RESET} $*"; }
ok()    { echo -e "${GREEN}[setup] ✓${RESET} $*"; }
warn()  { echo -e "${YELLOW}[setup] ⚠${RESET} $*"; }

# ── 1. Validate PLANE_SECRET_KEY ─────────────────────────────────────────────
if [[ ! -f .env ]]; then
  cp .env.docker .env
  info "Created .env from .env.docker"
fi

if ! grep -qE '^PLANE_SECRET_KEY=.+' .env 2>/dev/null; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
           openssl rand -hex 32)
  # Append or replace the key in .env
  if grep -q '^PLANE_SECRET_KEY=' .env; then
    sed -i.bak "s|^PLANE_SECRET_KEY=.*|PLANE_SECRET_KEY=${SECRET}|" .env && rm -f .env.bak
  else
    echo "PLANE_SECRET_KEY=${SECRET}" >> .env
  fi
  ok "Generated PLANE_SECRET_KEY and saved to .env"
fi

# ── 2. Pull images ────────────────────────────────────────────────────────────
info "Pulling images (this may take several minutes on first run)..."
docker compose pull --ignore-pull-failures

# ── 3. Start the stack ────────────────────────────────────────────────────────
info "Starting containers..."
docker compose up -d

# ── 4. Wait for each service ─────────────────────────────────────────────────

wait_healthy() {
  local name="$1" max="${2:-40}" delay="${3:-15}"
  info "Waiting for ${name} to be healthy..."
  for i in $(seq 1 "$max"); do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "missing")
    if [[ "$STATUS" == "healthy" ]]; then
      ok "${name} is healthy."
      return 0
    fi
    echo "  ($i/${max}) ${name}: ${STATUS} — retrying in ${delay}s..."
    sleep "$delay"
  done
  warn "${name} did not become healthy within the timeout. Check: docker compose logs ${name}"
  return 1
}

wait_healthy plane-api  30 20
wait_healthy kiwi       20 20
wait_healthy wikijs     15 15

# ── 5. Create Kiwi TCMS superuser (non-interactive, skips if already exists) ──
info "Running Kiwi TCMS database migrations..."
docker compose exec -T kiwi /Kiwi/manage.py migrate --noinput

info "Creating Kiwi TCMS superuser (admin / ${KIWI_PASSWORD:-admin1234!}) ..."
docker compose exec -T kiwi sh -c "
  DJANGO_SUPERUSER_PASSWORD='${KIWI_PASSWORD:-admin1234!}' \
  /Kiwi/manage.py createsuperuser \
    --username admin \
    --email admin@example.com \
    --noinput 2>&1 | grep -v 'already exists' || true
"

# ── 6. Load ports from .env for the summary ───────────────────────────────────
# shellcheck source=.env
source .env 2>/dev/null || true
PLANE_PORT="${PLANE_PORT:-80}"
KIWI_PORT="${KIWI_PORT:-8443}"
WIKIJS_PORT="${WIKIJS_PORT:-3000}"
UCD_PORT="${UCD_PORT:-8444}"

# ── 7. Print service summary ──────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo " Services are up. Complete first-time setup in your browser:"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo " Plane  (project management)"
echo "   URL   : http://localhost:${PLANE_PORT}"
echo "   Steps : Open URL → create account → create a workspace"
echo "           → create a project with identifier 'DEMO'"
echo "           → Settings → API Tokens → create token"
echo "           → paste token into .env as PLANE_API_TOKEN"
echo "           → paste workspace slug into .env as PLANE_WORKSPACE_SLUG"
echo "           → paste project ID into .env as PLANE_PROJECT_ID"
echo ""
echo " Kiwi TCMS  (test case management)"
echo "   URL   : https://localhost:${KIWI_PORT}  (accept self-signed cert)"
echo "   Login : admin / ${KIWI_PASSWORD:-admin1234!}"
echo "   Steps : Log in → top-right menu → Settings → API"
echo "           → Generate API Key → paste into .env as KIWI_API_KEY"
echo ""
echo " Wiki.js  (documentation wiki)"
echo "   URL   : http://localhost:${WIKIJS_PORT}"
echo "   Steps : Open URL → complete setup wizard (choose PostgreSQL,"
echo "           it is already running at wikijs-db:5432)"
echo "           → Administration → API Access → Generate API Key"
echo "           → paste into .env as WIKIJS_API_KEY"
echo ""
echo " Harness CD  (use decoy client — no Docker image required)"
echo "   The HarnessClient runs in decoy mode by default."
echo "   To connect to a real Harness instance:"
echo "     1. Obtain an API key from app.harness.io → Account Settings → API Keys"
echo "     2. Set HARNESS_API_KEY in .env"
echo "     3. Set use_decoy: false in config/settings.docker.yaml"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo " After setup, run the pipeline against the real stack:"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "   python scripts/run_pipeline.py \\"
echo "     --config config/settings.docker.yaml \\"
echo "     --issue DEMO-101 --env Production --version 1.0.0"
echo ""
echo " Useful commands:"
echo "   docker compose logs -f plane-api    # Plane backend logs"
echo "   docker compose logs -f kiwi         # Kiwi TCMS logs"
echo "   docker compose logs -f wikijs       # Wiki.js logs"
echo "   docker compose ps                   # container status"
echo ""
echo " Stop everything:"
echo "   docker compose down"
echo ""
echo " Destroy all data (volumes):"
echo "   docker compose down -v"
