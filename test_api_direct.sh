#!/bin/bash

# Curriculum Manager API 직접 테스트 스크립트

API_URL="http://localhost:8010"
echo "🧪 Curriculum Manager API 통합 테스트"
echo "========================================"

# Test 1: 헬스 체크
echo -e "\n📋 Test 1: 헬스 체크"
echo "GET $API_URL/health"
curl -s "$API_URL/health" | head -5
echo ""

# 서버가 응답하지 않으면 종료
if [ $? -ne 0 ]; then
    echo "❌ 서버가 응답하지 않습니다. Docker-compose 상태를 확인해주세요."
    docker-compose -f infra/docker-compose.test.yml ps
    exit 1
fi

# Test 2: DRAFT 생성
echo -e "\n📋 Test 2: DRAFT - 샘플 데이터 생성"
echo "POST $API_URL/api/curriculum/generate/draft"
DRAFT_RESPONSE=$(curl -s -X POST "$API_URL/api/curriculum/generate/draft" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Machine Learning Basics",
    "description": "Introduction to ML concepts"
  }')
echo "$DRAFT_RESPONSE" | python -m json.tool 2>/dev/null || echo "$DRAFT_RESPONSE"

# Test 3: STATUS 조회
echo -e "\n📋 Test 3: STATUS - 커리큘럼 상태 조회"
echo "GET $API_URL/api/curriculum/status"
STATUS_RESPONSE=$(curl -s "$API_URL/api/curriculum/status")
echo "$STATUS_RESPONSE" | python -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"

# Test 4: LINK 생성
echo -e "\n📋 Test 4: LINK - 엔티티 간 관계 생성"
echo "POST $API_URL/api/curriculum/generate/link"
LINK_RESPONSE=$(curl -s -X POST "$API_URL/api/curriculum/generate/link" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "Concept",
    "target_type": "Skill"
  }')
echo "$LINK_RESPONSE" | python -m json.tool 2>/dev/null || echo "$LINK_RESPONSE"

# Test 5: 여러 주제 DRAFT
echo -e "\n📋 Test 5: 여러 주제 순차 생성"
for subject in "Web Development" "Database Design" "Cloud Computing"; do
  echo "  - Generating: $subject"
  curl -s -X POST "$API_URL/api/curriculum/generate/draft" \
    -H "Content-Type: application/json" \
    -d "{\"subject\": \"$subject\"}" > /dev/null
  sleep 1
done

# Test 6: 최종 상태 확인
echo -e "\n📋 Test 6: 최종 상태 확인"
echo "GET $API_URL/api/curriculum/status"
FINAL_STATUS=$(curl -s "$API_URL/api/curriculum/status")
echo "$FINAL_STATUS" | python -m json.tool 2>/dev/null || echo "$FINAL_STATUS"

# Test 7: 데이터 파일 확인
echo -e "\n📋 Test 7: 데이터 파일 지속성 검증"
if [ -f "nodes.json" ]; then
    NODES_COUNT=$(python -c "import json; data=json.load(open('nodes.json')); print(len(data))")
    echo "✅ nodes.json 파일 존재 - 총 $NODES_COUNT개 노드"
    echo "   첫 번째 노드 샘플:"
    python -c "import json; data=json.load(open('nodes.json')); print('   ', json.dumps(data[0], indent=6, default=str)[:200])" 2>/dev/null
else
    echo "⚠️  nodes.json 파일이 없습니다"
fi

if [ -f "edges.json" ]; then
    EDGES_COUNT=$(python -c "import json; data=json.load(open('edges.json')); print(len(data))")
    echo "✅ edges.json 파일 존재 - 총 $EDGES_COUNT개 엣지"
else
    echo "⚠️  edges.json 파일이 없습니다"
fi

echo -e "\n========================================"
echo "✅ 테스트 완료!"
