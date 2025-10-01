#!/bin/bash

# Multi-Provider Email System API Tests
# Tests all endpoints without destructive operations

API_BASE="http://localhost:3020"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Multi-Provider Email System - API Integration Tests      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local name="$1"
    local endpoint="$2"
    local expected_key="$3"

    echo -n "Testing: $name... "

    response=$(curl -s "$API_BASE$endpoint")

    if echo "$response" | jq -e ".$expected_key" > /dev/null 2>&1; then
        echo "✓ PASS"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo "✗ FAIL"
        echo "  Response: $response"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 1: Account Management API
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Account Management API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_endpoint "List Accounts" "/api/accounts?userId=default" "accounts"

if [ $? -eq 0 ]; then
    echo "  Details:"
    curl -s "$API_BASE/api/accounts?userId=default" | jq -r '.accounts[] | "    - \(.provider): \(.email_address)"'
fi

test_endpoint "Gmail OAuth URL" "/api/accounts/oauth/gmail/url?userId=default" "authUrl"

echo ""

# Test 2: Provider Capabilities
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Provider Capabilities"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_endpoint "Provider Capabilities" "/api/providers/capabilities" "gmail"

if [ $? -eq 0 ]; then
    echo "  Gmail:"
    curl -s "$API_BASE/api/providers/capabilities" | jq -r '.gmail | "    Batch: \(.maxBatchSize), Rate: \(.rateLimitPerSecond)/s, Webhooks: \(.supportsWebhooks)"'
    echo "  Exchange:"
    curl -s "$API_BASE/api/providers/capabilities" | jq -r '.exchange | "    Batch: \(.maxBatchSize), Rate: \(.rateLimitPerSecond)/s, Webhooks: \(.supportsWebhooks)"'
    echo "  IMAP:"
    curl -s "$API_BASE/api/providers/capabilities" | jq -r '.imap | "    Batch: \(.maxBatchSize), Rate: \(.rateLimitPerSecond)/s, Webhooks: \(.supportsWebhooks)"'
fi

echo ""

# Test 3: Calendar Integration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Calendar Integration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_endpoint "Pending Invites" "/api/calendar/pending-invites" "invites"

if [ $? -eq 0 ]; then
    echo "  Invites found:"
    curl -s "$API_BASE/api/calendar/pending-invites" | jq -r '.invites[] | "    - \(.eventTitle): AI suggests \(.autoRsvpSuggestion.response) (\(.autoRsvpSuggestion.confidence * 100)% confidence)"'
fi

echo ""

# Test 4: Auto-RSVP Rules
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Auto-RSVP Rules"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_endpoint "Auto-RSVP Rules" "/api/rules/auto-rsvp" "rules"

if [ $? -eq 0 ]; then
    echo "  Rules configured:"
    curl -s "$API_BASE/api/rules/auto-rsvp" | jq -r '.rules[] | "    - \(.name) (\(.ruleType)): \(.action.response) | Priority: \(.priority) | Enabled: \(.enabled)"'
fi

echo ""

# Test 5: Automation Stats
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Automation Statistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_endpoint "Automation Stats" "/api/stats/automation?days=30" "totalActions"

if [ $? -eq 0 ]; then
    echo "  Statistics:"
    stats=$(curl -s "$API_BASE/api/stats/automation?days=30")
    echo "    Total Actions: $(echo $stats | jq -r '.totalActions')"
    echo "    Time Saved: $(echo $stats | jq -r '.totalTimeSavedHours') hours"
    echo "    Inbox Zero Rate: $(echo $stats | jq -r '(.inboxZeroRate * 100 | floor)')%"
    echo "    Avg Actions/Day: $(echo $stats | jq -r '.avgActionsPerDay')"
    echo "    Breakdown:"
    echo "      Auto-RSVP: $(echo $stats | jq -r '.breakdown.autoRsvp')"
    echo "      Archived: $(echo $stats | jq -r '.breakdown.emailArchived')"
    echo "      Flags Synced: $(echo $stats | jq -r '.breakdown.flagsSync')"
fi

echo ""

# Test 6: Flag Sync (Mock)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Flag Sync"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -n "Testing: Flag Sync (POST)... "
response=$(curl -s -X POST "$API_BASE/api/flags/sync" \
  -H "Content-Type: application/json" \
  -d '{"emailId":123,"flags":{"seen":true},"direction":"toProvider"}')

if echo "$response" | jq -e '.success' > /dev/null 2>&1; then
    echo "✓ PASS"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "  Synced to: $(echo $response | jq -r '.syncedTo')"
else
    echo "✗ FAIL"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Test 7: RSVP (Mock)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. RSVP Workflow"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -n "Testing: RSVP (POST)... "
response=$(curl -s -X POST "$API_BASE/api/calendar/rsvp" \
  -H "Content-Type: application/json" \
  -d '{"emailId":1,"response":"accepted"}')

if echo "$response" | jq -e '.success' > /dev/null 2>&1; then
    echo "✓ PASS"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "  Actions taken:"
    echo "$response" | jq -r '.actions[] | "    - \(.)"'
else
    echo "✗ FAIL"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Summary
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                        TEST SUMMARY                           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
    echo ""
    echo "Tested Components:"
    echo "  ✓ Account Management API"
    echo "  ✓ OAuth Flow (mock)"
    echo "  ✓ Provider Capabilities"
    echo "  ✓ Calendar Integration"
    echo "  ✓ Auto-RSVP Rules"
    echo "  ✓ Flag Sync (mock)"
    echo "  ✓ Automation Statistics"
    echo "  ✓ RSVP Workflow (mock)"
    echo ""
    echo "🔒 NO DESTRUCTIVE OPERATIONS PERFORMED"
    echo "  • No emails deleted"
    echo "  • No emails archived"
    echo "  • No emails moved"
    echo "  • Only read operations and mock responses tested"
    echo ""
    exit 0
else
    echo "❌ SOME TESTS FAILED"
    exit 1
fi
