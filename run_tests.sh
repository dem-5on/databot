#!/bin/bash
set -e

echo "📦 Installing testing dependencies..."
pip install -r requirements-test.txt > /dev/null

echo ""
echo "================================================="
echo "🧪 RUNNING TEST SUITE: UNIT TESTS (Logic/Crypto)"
echo "================================================="
pytest tests/unit/ -m unit --color=yes

echo ""
echo "================================================="
echo "🌐 RUNNING TEST SUITE: API ENDPOINTS"
echo "================================================="
pytest tests/api/ -m api --color=yes

echo ""
echo "================================================="
echo "⚙️ RUNNING TEST SUITE: INTEGRATION & FLOWS"
echo "================================================="
pytest tests/integration/ -m integration --color=yes

echo ""
echo "================================================="
echo "🛡️ RUNNING TEST SUITE: SECURITY & EDGE CASES"
echo "================================================="
pytest tests/security/ -m security --color=yes

echo ""
echo "✅ All tests completed successfully!"
