#!/bin/bash
# curl_examples.sh
# curl commands for common ToolAtlas API operations
# Requires a running ToolAtlas instance at http://localhost:8000

BASE="${BASE:-http://localhost:8000}"

echo "=== List Servers ==="
curl -s "$BASE/api/servers" | python -m json.tool

echo ""
echo "=== List Proxies ==="
curl -s "$BASE/api/proxies" | python -m json.tool

echo ""
echo "=== Create Proxy ==="
curl -s -X POST "$BASE/api/proxies" \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo","slug":"demo","description":"A demo proxy"}' | python -m json.tool

echo ""
echo "=== List Proxy Tools ==="
PROXY_ID=$(curl -s "$BASE/api/proxies" | python -c "import sys,json; proxies=json.load(sys.stdin); print(proxies[0]['id'])" 2>/dev/null)
if [ -n "$PROXY_ID" ]; then
  curl -s "$BASE/api/proxies/$PROXY_ID/tools" | python -m json.tool
fi

echo ""
echo "=== Get Graph ==="
curl -s "$BASE/api/graph" | python -m json.tool

echo ""
echo "=== Get Traces ==="
curl -s "$BASE/api/graph/traces?limit=5" | python -m json.tool

echo ""
echo "=== Get Co-occurrence ==="
curl -s "$BASE/api/graph/co-occurrence" | python -m json.tool
