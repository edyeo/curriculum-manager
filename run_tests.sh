#!/bin/bash

# Curriculum Manager API 테스트

API_URL="http://localhost:8010"
echo "========================================="
echo "🧪 Curriculum Manager API 통합 테스트"
echo "========================================="

# Test 1: Health Check
echo -e "\n📋 Test 1: Health Check"
HEALTH=$(curl -s "$API_URL/health" 2>/dev/null)
if [[ $HEALTH == *"healthy"* ]]; then
    echo "✅ PASS: Server is healthy"
    echo "   Response: $HEALTH"
else
    echo "❌ FAIL: Health check failed"
    exit 1
fi

# Test 2: DRAFT - 샘플 데이터 생성
echo -e "\n📋 Test 2: DRAFT - 샘플 데이터 생성"
DRAFT=$(curl -s -X POST "$API_URL/api/curriculum/generate/draft" \
  -H "Content-Type: application/json" \
  -d '{"subject": "Machine Learning Basics", "description": "Introduction to ML"}')

if [[ $DRAFT == *"success"* ]]; then
    NODES=$(echo "$DRAFT" | python -m json.tool 2>/dev/null | grep "nodes_count" | grep -oP '\d+')
    echo "✅ PASS: Generated $NODES nodes"
    echo "   Response: $DRAFT"
else
    echo "❌ FAIL: Draft generation failed"
    echo "   Response: $DRAFT"
fi

# Test 3: STATUS - 상태 조회
echo -e "\n📋 Test 3: STATUS - 상태 조회"
STATUS=$(curl -s "$API_URL/api/curriculum/status")
if [[ $STATUS == *"ready"* ]]; then
    NODES=$(echo "$STATUS" | python -m json.tool 2>/dev/null | grep "nodes_count" | grep -oP '\d+')
    EDGES=$(echo "$STATUS" | python -m json.tool 2>/dev/null | grep "edges_count" | grep -oP '\d+')
    echo "✅ PASS: Status retrieved"
    echo "   Nodes: $NODES, Edges: $EDGES"
else
    echo "⚠️  WARN: Status check returned unexpected response"
    echo "   Response: $STATUS"
fi

# Test 4: LINK - 엔티티 간 관계 생성
echo -e "\n📋 Test 4: LINK - 엔티티 간 관계 생성"
LINK=$(curl -s -X POST "$API_URL/api/curriculum/generate/link" \
  -H "Content-Type: application/json" \
  -d '{"source_type": "Concept", "target_type": "Skill"}')

if [[ $LINK == *"success"* ]]; then
    echo "✅ PASS: Link created successfully"
    echo "   Response: $LINK"
else
    echo "⚠️  WARN: Link generation returned unexpected response"
    echo "   Response: $LINK"
fi

# Test 5: 데이터 파일 확인
echo -e "\n📋 Test 5: 데이터 지속성 검증"
if [ -f "nodes.json" ]; then
    NODES_COUNT=$(python -c "import json; print(len(json.load(open('nodes.json'))))" 2>/dev/null)
    echo "✅ PASS: nodes.json exists with $NODES_COUNT nodes"
else
    echo "⚠️  WARN: nodes.json not found"
fi

if [ -f "edges.json" ]; then
    EDGES_COUNT=$(python -c "import json; print(len(json.load(open('edges.json'))))" 2>/dev/null)
    echo "✅ PASS: edges.json exists with $EDGES_COUNT edges"
else
    echo "⚠️  WARN: edges.json not found"
fi

echo -e "\n========================================="
echo "✅ 테스트 완료!"
echo "========================================="
