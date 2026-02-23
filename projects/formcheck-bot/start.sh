#!/bin/bash
# FORMCHECK — Start server + tunnel + auto-update Twilio webhook
# Usage: ./start.sh

set -e

cd "$(dirname "$0")"

# Load .env
export $(grep -v '^#' .env | xargs)

echo "🔥 Starting FORMCHECK server..."
source venv/bin/activate
PYTHONPATH=src python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src &
SERVER_PID=$!
sleep 2

echo "🌐 Starting Cloudflare tunnel..."
cloudflared tunnel --url http://localhost:8000 2>&1 | while read line; do
    echo "$line"
    # Extract tunnel URL
    if echo "$line" | grep -q "trycloudflare.com"; then
        URL=$(echo "$line" | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com')
        if [ -n "$URL" ]; then
            echo ""
            echo "✅ Tunnel URL: $URL"
            echo "📱 Webhook: $URL/webhook/whatsapp"
            
            # Update .env
            sed -i '' "s|BASE_URL=.*|BASE_URL=$URL|" .env
            echo "✅ .env updated"
            
            # Auto-update Twilio sandbox webhook
            echo "📞 Updating Twilio webhook..."
            curl -s -X POST "https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/IncomingPhoneNumbers.json" \
                -u "${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}" \
                --data-urlencode "SmsUrl=${URL}/webhook/whatsapp" \
                > /dev/null 2>&1
            
            # Update sandbox specifically
            curl -s -X POST "https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/Sandbox.json" \
                -u "${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}" \
                --data-urlencode "SmsUrl=${URL}/webhook/whatsapp" \
                --data-urlencode "StatusCallback=${URL}/webhook/whatsapp/status" \
                > /dev/null 2>&1
                
            echo "✅ Twilio webhook updated automatically!"
            echo ""
            echo "🎯 Ready! Send a video to WhatsApp sandbox: +14155238886"
        fi
    fi
done

wait $SERVER_PID
