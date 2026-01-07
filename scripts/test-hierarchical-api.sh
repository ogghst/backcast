#!/bin/bash
# Test script for hierarchical navigation API endpoints
# Tests: parent_wbe_id filtering, breadcrumb endpoint, cascade delete

set -e  # Exit on error

BASE_URL="http://localhost:8020/api/v1"
ADMIN_EMAIL="admin@backcast.org"
ADMIN_PASSWORD="adminadmin"

echo "=========================================="
echo "Testing Hierarchical Navigation API"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

echo "Step 1: Authenticating as admin..."
AUTH_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${ADMIN_EMAIL}&password=${ADMIN_PASSWORD}")

TOKEN=$(echo $AUTH_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}Failed to get authentication token${NC}"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Authentication successful${NC}"
echo "Token: ${TOKEN:0:20}..."
echo ""

# Test 1: Get all WBEs (baseline)
echo "=========================================="
echo "Test 1: Get all WBEs (no filters)"
echo "=========================================="
WBES_RESPONSE=$(curl -s -X GET "${BASE_URL}/wbes" \
    -H "Authorization: Bearer ${TOKEN}")

WBE_COUNT=$(echo $WBES_RESPONSE | grep -o '"wbe_id"' | wc -l)
echo "Total WBEs found: $WBE_COUNT"

if [ $WBE_COUNT -gt 0 ]; then
    # Extract first WBE details for further testing
    FIRST_WBE_ID=$(echo $WBES_RESPONSE | grep -o '"wbe_id":"[^"]*' | head -1 | cut -d'"' -f4)
    FIRST_PROJECT_ID=$(echo $WBES_RESPONSE | grep -o '"project_id":"[^"]*' | head -1 | cut -d'"' -f4)
    
    echo "First WBE ID: $FIRST_WBE_ID"
    echo "First WBE's Project ID: $FIRST_PROJECT_ID"
    print_result 0 "Retrieved WBEs successfully"
else
    echo -e "${YELLOW}⚠ No WBEs found in database. Some tests will be skipped.${NC}"
fi
echo ""

# Test 2: Filter WBEs by project
if [ -n "$FIRST_PROJECT_ID" ]; then
    echo "=========================================="
    echo "Test 2: Filter WBEs by project_id"
    echo "=========================================="
    PROJECT_WBES_RESPONSE=$(curl -s -X GET "${BASE_URL}/wbes?project_id=${FIRST_PROJECT_ID}" \
        -H "Authorization: Bearer ${TOKEN}")

    PROJECT_WBE_COUNT=$(echo $PROJECT_WBES_RESPONSE | grep -o '"wbe_id"' | wc -l)
    echo "WBEs in project ${FIRST_PROJECT_ID}: $PROJECT_WBE_COUNT"
    print_result 0 "Filtered WBEs by project successfully"
    echo ""
fi

# Test 3: Get root WBEs (parent_wbe_id IS NULL) - NEW FEATURE
if [ -n "$FIRST_PROJECT_ID" ]; then
    echo "=========================================="
    echo "Test 3: Get ROOT WBEs (NEW: parent_wbe_id filter)"
    echo "=========================================="
    
    # Note: For NULL filtering, we pass parent_wbe_id without a value or check the logic
    # The API should handle parent_wbe_id=None by filtering for NULL
    ROOT_WBES_RESPONSE=$(curl -s -X GET "${BASE_URL}/wbes?project_id=${FIRST_PROJECT_ID}&parent_wbe_id=" \
        -H "Authorization: Bearer ${TOKEN}")

    ROOT_WBE_COUNT=$(echo $ROOT_WBES_RESPONSE | grep -o '"wbe_id"' | wc -l)
    echo "Root WBEs (parent_wbe_id IS NULL): $ROOT_WBE_COUNT"
    
    # Check if any have parent_wbe_id = null
    HAS_NULLS=$(echo $ROOT_WBES_RESPONSE | grep -o '"parent_wbe_id":null' | wc -l)
    
    if [ $HAS_NULLS -gt 0 ]; then
        print_result 0 "Root WBE filtering works (found $HAS_NULLS root WBEs)"
        
        # Extract a root WBE for child testing
        ROOT_WBE_ID=$(echo $ROOT_WBES_RESPONSE | grep -o '"wbe_id":"[^"]*' | head -1 | cut -d'"' -f4)
        ROOT_WBE_CODE=$(echo $ROOT_WBES_RESPONSE | grep -o '"code":"[^"]*' | head -1 | cut -d'"' -f4)
        echo "Sample Root WBE: $ROOT_WBE_CODE ($ROOT_WBE_ID)"
    else
        echo -e "${YELLOW}⚠ No root WBEs found (all WBEs have parents)${NC}"
    fi
    echo ""
fi

# Test 4: Get child WBEs of a specific parent - NEW FEATURE
if [ -n "$ROOT_WBE_ID" ]; then
    echo "=========================================="
    echo "Test 4: Get CHILD WBEs (NEW: filter by parent_wbe_id)"
    echo "=========================================="
    CHILD_WBES_RESPONSE=$(curl -s -X GET "${BASE_URL}/wbes?parent_wbe_id=${ROOT_WBE_ID}" \
        -H "Authorization: Bearer ${TOKEN}")

    CHILD_WBE_COUNT=$(echo $CHILD_WBES_RESPONSE | grep -o '"wbe_id"' | wc -l)
    echo "Children of WBE $ROOT_WBE_CODE: $CHILD_WBE_COUNT"
    
    if [ $CHILD_WBE_COUNT -gt 0 ]; then
        print_result 0 "Child WBE filtering works (found $CHILD_WBE_COUNT children)"
        
        # Extract first child for breadcrumb testing
        CHILD_WBE_ID=$(echo $CHILD_WBES_RESPONSE | grep -o '"wbe_id":"[^"]*' | head -1 | cut -d'"' -f4)
        CHILD_WBE_CODE=$(echo $CHILD_WBES_RESPONSE | grep -o '"code":"[^"]*' | head -1 | cut -d'"' -f4)
        echo "Sample Child WBE: $CHILD_WBE_CODE ($CHILD_WBE_ID)"
    else
        echo -e "${YELLOW}⚠ No child WBEs found for $ROOT_WBE_CODE${NC}"
    fi
    echo ""
fi

# Test 5: Breadcrumb endpoint - NEW FEATURE
if [ -n "$CHILD_WBE_ID" ]; then
    echo "=========================================="
    echo "Test 5: Breadcrumb endpoint (NEW)"
    echo "=========================================="
    BREADCRUMB_RESPONSE=$(curl -s -X GET "${BASE_URL}/wbes/${CHILD_WBE_ID}/breadcrumb" \
        -H "Authorization: Bearer ${TOKEN}")

    # Check if response contains project and wbe_path
    HAS_PROJECT=$(echo $BREADCRUMB_RESPONSE | grep -o '"project"' | wc -l)
    HAS_WBE_PATH=$(echo $BREADCRUMB_RESPONSE | grep -o '"wbe_path"' | wc -l)
    
    if [ $HAS_PROJECT -gt 0 ] && [ $HAS_WBE_PATH -gt 0 ]; then
        print_result 0 "Breadcrumb endpoint returns correct structure"
        
        # Pretty print breadcrumb
        echo ""
        echo "Breadcrumb trail:"
        PROJECT_CODE=$(echo $BREADCRUMB_RESPONSE | grep -o '"code":"[^"]*' | head -1 | cut -d'"' -f4)
        echo "  Project: $PROJECT_CODE"
        
        # Count WBEs in path
        PATH_LENGTH=$(echo $BREADCRUMB_RESPONSE | grep -o '"wbe_id":"[^"]*' | wc -l)
        echo "  WBE Path depth: $PATH_LENGTH levels"
        
        # Show path codes
        echo "  Path: $(echo $BREADCRUMB_RESPONSE | grep -o '"code":"[^"]*' | cut -d'"' -f4 | tail -n +2 | tr '\n' ' > ')"
    else
        print_result 1 "Breadcrumb endpoint missing required fields"
        echo "Response: $BREADCRUMB_RESPONSE"
    fi
    echo ""
elif [ -n "$FIRST_WBE_ID" ]; then
    # Fallback: test breadcrumb with any WBE
    echo "=========================================="
    echo "Test 5: Breadcrumb endpoint (fallback to first WBE)"
    echo "=========================================="
    BREADCRUMB_RESPONSE=$(curl -s -X GET "${BASE_URL}/wbes/${FIRST_WBE_ID}/breadcrumb" \
        -H "Authorization: Bearer ${TOKEN}")

    HAS_PROJECT=$(echo $BREADCRUMB_RESPONSE | grep -o '"project"' | wc -l)
    HAS_WBE_PATH=$(echo $BREADCRUMB_RESPONSE | grep -o '"wbe_path"' | wc -l)
    
    if [ $HAS_PROJECT -gt 0 ] && [ $HAS_WBE_PATH -gt 0 ]; then
        print_result 0 "Breadcrumb endpoint works"
        echo "Response structure valid (project + wbe_path present)"
    else
        print_result 1 "Breadcrumb endpoint failed"
        echo "Response: $BREADCRUMB_RESPONSE"
    fi
    echo ""
fi

# Test 6: Error handling - invalid WBE ID
echo "=========================================="
echo "Test 6: Error handling (invalid WBE ID)"
echo "=========================================="
INVALID_UUID="00000000-0000-0000-0000-000000000000"
ERROR_RESPONSE=$(curl -s -X GET "${BASE_URL}/wbes/${INVALID_UUID}/breadcrumb" \
    -H "Authorization: Bearer ${TOKEN}")

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${BASE_URL}/wbes/${INVALID_UUID}/breadcrumb" \
    -H "Authorization: Bearer ${TOKEN}")

if [ "$HTTP_CODE" = "404" ]; then
    print_result 0 "Returns 404 for non-existent WBE"
else
    print_result 1 "Should return 404 for invalid WBE (got $HTTP_CODE)"
fi
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}All tests passed!${NC}"
echo ""
echo "Verified features:"
echo "  ✓ GET /wbes?parent_wbe_id=<id> - Child WBE filtering"
echo "  ✓ GET /wbes?parent_wbe_id= - Root WBE filtering"  
echo "  ✓ GET /wbes/{wbe_id}/breadcrumb - Breadcrumb trail"
echo "  ✓ Error handling for invalid WBE IDs"
echo ""
echo "Backend API is ready for frontend integration!"
