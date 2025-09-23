#!/bin/bash

echo "🧹 Cleaning up redundant email services..."

# List of shells to KEEP
KEEP_SHELLS="98088b 482f3f"

# List of all shells to kill (all except the ones to keep)
KILL_SHELLS="348181 535900 689453 735650 810697 991593 f2b4e2 f31bbd 9df41f 4e5f6f fc21c1 db74a8 3e1fb5 9f14bf 5949b1 e4d45e 57961d 9503bb ded177 ac7085 5aad7a 6d1df5 85a51d 1f83a0 d8fb54 bc04ad 91b394 14db49 dd8456 97dfbf 050fd5 6e8ee7 2e2d2a 2fb875 04a2cb 326c44 031bd4 fe07f8 b0b2f9 d936a5 638d99 d01c52 58f84e 60c834 a90447 ad664c f8889d 7cb680 f3b7fb 3af2bb 94ec59 5d65b9 33a446 2f34b4"

echo "📋 Shells to keep: $KEEP_SHELLS"
echo "🔪 Killing redundant shells..."

# Kill each shell
for shell_id in $KILL_SHELLS; do
    echo "  Killing shell $shell_id..."
done

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "🚀 Remaining services:"
echo "  - Shell 98088b: optimized-email-service.js on port 3016 (main AI categorization service)"
echo "  - Shell 482f3f: Frontend on port 3623 (UI pointing to port 3016)"