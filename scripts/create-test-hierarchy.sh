#!/bin/bash
# Create test data for hierarchical navigation testing

BASE_URL="http://localhost:8020/api/v1"
ADMIN_EMAIL="admin@backcast.org"
ADMIN_PASSWORD="adminadmin"

echo "Creating hierarchical test data..."
echo ""

# Get auth token
echo "1. Authenticating..."
TOKEN=$(curl -s -X POST "${BASE_URL}/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${ADMIN_EMAIL}&password=${ADMIN_PASSWORD}" \
    | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Authentication failed"
    exit 1
fi
echo "   ✓ Authenticated"
echo ""

# Create a test project
echo "2. Creating test project..."
PROJECT_RESPONSE=$(curl -s -X POST "${BASE_URL}/projects" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
   -d '{
        "code": "TEST-001",
        "name": "Hierarchical Navigation Test Project",
        "budget": 1000000,
        "contract_value": 950000,
        "status": "Active",
        "description": "Test project for hierarchical WBE navigation"
    }')

PROJECT_ID=$(echo $PROJECT_RESPONSE | grep -o '"project_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$PROJECT_ID" ]; then
    echo "   ❌ Failed to create project"
    echo "   Response: $PROJECT_RESPONSE"
    exit 1
fi
echo "   ✓ Project created: $PROJECT_ID"
echo ""

# Create root WBE 1.0
echo "3. Creating root WBE (1.0 Site Preparation)..."
WBE_10_RESPONSE=$(curl -s -X POST "${BASE_URL}/wbes" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"code\": \"1.0\",
        \"name\": \"Site Preparation\",
        \"budget_allocation\": 100000,
        \"level\": 1,
        \"parent_wbe_id\": null,
        \"description\": \"Site preparation and initial work\"
    }")

WBE_10_ID=$(echo $WBE_10_RESPONSE | grep -o '"wbe_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$WBE_10_ID" ]; then
    echo "   ❌ Failed to create WBE 1.0"
    echo "   Response: $WBE_10_RESPONSE"
    exit 1
fi
echo "   ✓ WBE 1.0 created: $WBE_10_ID"
echo ""

# Create root WBE 2.0
echo "4. Creating root WBE (2.0 Assembly)..."
WBE_20_RESPONSE=$(curl -s -X POST "${BASE_URL}/wbes" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"code\": \"2.0\",
        \"name\": \"Assembly\",
        \"budget_allocation\": 200000,
        \"level\": 1,
        \"parent_wbe_id\": null,
        \"description\": \"Assembly work\"
    }")

WBE_20_ID=$(echo $WBE_20_RESPONSE | grep -o '"wbe_id":"[^"]*' | cut -d'"' -f4)
echo "   ✓ WBE 2.0 created: $WBE_20_ID"
echo ""

# Create child WBE 1.1 (child of 1.0)
echo "5. Creating child WBE (1.1 Foundation - child of 1.0)..."
WBE_11_RESPONSE=$(curl -s -X POST "${BASE_URL}/wbes" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"code\": \"1.1\",
        \"name\": \"Foundation\",
        \"budget_allocation\": 40000,
        \"level\": 2,
        \"parent_wbe_id\": \"${WBE_10_ID}\",
        \"description\": \"Foundation work\"
    }")

WBE_11_ID=$(echo $WBE_11_RESPONSE | grep -o '"wbe_id":"[^"]*' | cut -d'"' -f4)
echo "   ✓ WBE 1.1 created: $WBE_11_ID"
echo ""

# Create child WBE 1.2 (child of 1.0)
echo "6. Creating child WBE (1.2 Electrical - child of 1.0)..."
WBE_12_RESPONSE=$(curl -s -X POST "${BASE_URL}/wbes" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"code\": \"1.2\",
        \"name\": \"Electrical Conduit\",
        \"budget_allocation\": 30000,
        \"level\": 2,
        \"parent_wbe_id\": \"${WBE_10_ID}\",
        \"description\": \"Electrical conduit installation\"
    }")

WBE_12_ID=$(echo $WBE_12_RESPONSE | grep -o '"wbe_id":"[^"]*' | cut -d'"' -f4)
echo "   ✓ WBE 1.2 created: $WBE_12_ID"
echo ""

# Create nested child WBE 1.1.1 (child of 1.1)
echo "7. Creating nested child WBE (1.1.1 Excavation - child of 1.1)..."
WBE_111_RESPONSE=$(curl -s -X POST "${BASE_URL}/wbes" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"code\": \"1.1.1\",
        \"name\": \"Excavation\",
        \"budget_allocation\": 20000,
        \"level\": 3,
        \"parent_wbe_id\": \"${WBE_11_ID}\",
        \"description\": \"Site excavation\"
    }")

WBE_111_ID=$(echo $WBE_111_RESPONSE | grep -o '"wbe_id":"[^"]*' | cut -d'"' -f4)
echo "   ✓ WBE 1.1.1 created: $WBE_111_ID"
echo ""

echo "=========================================="
echo "Test Data Created Successfully!"
echo "=========================================="
echo "Project: TEST-001 ($PROJECT_ID)"
echo "Hierarchy:"
echo "  1.0 Site Preparation ($WBE_10_ID)"
echo "    ├─ 1.1 Foundation ($WBE_11_ID)"
echo "    │   └─ 1.1.1 Excavation ($WBE_111_ID)"
echo "    └─ 1.2 Electrical Conduit ($WBE_12_ID)"
echo "  2.0 Assembly ($WBE_20_ID)"
echo ""
echo "Now run: ./scripts/test-hierarchical-api.sh"
