#!/usr/bin/env bash
# worktree-up.sh — 워크트리에서 개발 서버 기동
# 위치: infra/worktree-up.sh
#
# 실행:
#   cd infra
#   bash worktree-up.sh [up|down|restart]
#
# 전제조건:
#   - .env.local 에 OPENAI_API_KEY 설정
#   - Docker Desktop 실행 중

set -e

INFRA_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKTREE_ROOT="$(cd "$INFRA_DIR/.." && pwd)"
ENV_FILE="$INFRA_DIR/.env.local"
CMD="${1:-up}"

# ── 최상위 .env 에서 키 로드 ─────────────────────────────────

MAIN_REPO="$(git -C "$WORKTREE_ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null | xargs dirname 2>/dev/null || echo "")"
MAIN_ENV="$MAIN_REPO/infra/.env"
MAIN_KEY=""
if [ -f "$MAIN_ENV" ]; then
  MAIN_KEY=$(grep "^OPENAI_API_KEY=" "$MAIN_ENV" | cut -d= -f2-)
fi

# ── .env.local 준비 ──────────────────────────────────────────

if [ ! -f "$ENV_FILE" ]; then
  if [ -z "$MAIN_KEY" ]; then
    echo "⚠️  .env.local 없음 → 템플릿 생성"
    cat > "$ENV_FILE" <<EOF
OPENAI_API_KEY=sk-your-key-here
DB_TYPE=file
LOG_LEVEL=DEBUG
WORKTREE_ROOT=${WORKTREE_ROOT}
EOF
    echo "✏️  $ENV_FILE 에 OPENAI_API_KEY 를 설정하고 다시 실행하세요."
    exit 1
  fi
  echo "📄 .env.local 자동 생성 (최상위 .env 참조)"
  cat > "$ENV_FILE" <<EOF
OPENAI_API_KEY=${MAIN_KEY}
DB_TYPE=file
LOG_LEVEL=DEBUG
WORKTREE_ROOT=${WORKTREE_ROOT}
EOF
fi

# WORKTREE_ROOT 갱신 (경로가 바뀐 경우 대비)
if grep -q "^WORKTREE_ROOT=" "$ENV_FILE"; then
  sed -i '' "s|^WORKTREE_ROOT=.*|WORKTREE_ROOT=${WORKTREE_ROOT}|" "$ENV_FILE"
else
  echo "WORKTREE_ROOT=${WORKTREE_ROOT}" >> "$ENV_FILE"
fi

# OPENAI_API_KEY — main repo .env 에서 동기화 (sk- prefix 누락 방지)
if [ -n "$MAIN_KEY" ]; then
  if grep -q "^OPENAI_API_KEY=" "$ENV_FILE"; then
    sed -i '' "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${MAIN_KEY}|" "$ENV_FILE"
  else
    echo "OPENAI_API_KEY=${MAIN_KEY}" >> "$ENV_FILE"
  fi
  echo "🔑 OPENAI_API_KEY ← main repo .env 동기화"
fi

echo "📂 WORKTREE_ROOT: $WORKTREE_ROOT"

# ── down 처리 ─────────────────────────────────────────────────

if [ "$CMD" = "down" ]; then
  docker compose --env-file "$ENV_FILE" \
    -f docker-compose.local.yml \
    -f docker-compose.dev.yml \
    -f docker-compose.worktree.yml \
    down
  echo "✅ 서비스 종료"
  exit 0
fi

# ── 데이터 파일 초기화 ────────────────────────────────────────

MAIN_REPO="$(git -C "$WORKTREE_ROOT" rev-parse --path-format=absolute --git-common-dir | xargs dirname 2>/dev/null || echo "")"

init_data_file() {
  local target="$1"
  if [ -d "$target" ]; then
    echo "🧹 빈 디렉토리 제거: $target"
    rm -rf "$target"
  fi
  if [ ! -f "$target" ]; then
    local filename
    filename="$(basename "$target")"
    local main_file="$MAIN_REPO/$filename"
    if [ -n "$MAIN_REPO" ] && [ -f "$main_file" ]; then
      echo "📋 복사: $main_file → $target"
      cp "$main_file" "$target"
    else
      echo "📄 빈 파일 생성: $target"
      echo "[]" > "$target"
    fi
  fi
}

init_data_file "$WORKTREE_ROOT/nodes.json"
init_data_file "$WORKTREE_ROOT/edges.json"

# backend/data/ 동기화 (Mac Docker 중첩 bind mount 우선순위 문제 우회)
# WORKTREE_ROOT/nodes.json 이 정본(master). backend/data/ 로 복사해 두면
# contents-manager-backend 볼륨 마운트가 올바른 데이터를 읽는다.
BACKEND_DATA="$WORKTREE_ROOT/apps/contents-manager/backend/data"
mkdir -p "$BACKEND_DATA"
for name in nodes.json edges.json; do
  target="$BACKEND_DATA/$name"
  if [ -d "$target" ]; then
    echo "🧹 backend/data/$name 빈 디렉토리 제거"
    rm -rf "$target"
  fi
  if [ ! -f "$target" ] || [ ! -s "$target" ]; then
    echo "📋 backend/data/$name ← WORKTREE_ROOT/$name 복사"
    cp "$WORKTREE_ROOT/$name" "$target"
  fi
done

# ── 서비스 기동 ───────────────────────────────────────────────

echo "🚀 서비스 기동 중..."
docker compose --env-file "$ENV_FILE" \
  -f docker-compose.local.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.worktree.yml \
  up -d --build

echo ""
echo "✅ 완료"
echo "   Frontend : http://localhost:3000"
echo "   Backend  : http://localhost:8010"
echo "   Gateway  : http://localhost:9000"
