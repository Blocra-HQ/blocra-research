#!/bin/bash

CONTRACT="0xCd45aC05fe7C014D6B2F62b3446E2A91D661a236"
RPC="https://mainnet.base.org"

echo "🔍 Finding December 2025 transactions"
echo "Contract: $CONTRACT"
echo "Deployed: Block 39,850,978"
echo ""

# Scan from deployment block forward (first 50k blocks after deployment)
DEPLOY=39850978
SCAN_RANGE=50000

echo "📦 Scanning blocks $DEPLOY to $((DEPLOY + SCAN_RANGE))..."
echo ""

FOUND=0
# Check every 1000th block
for i in {0..50}; do
  BLOCK=$((DEPLOY + i * 1000))
  BLOCK_HEX=$(printf "0x%x" $BLOCK)
  
  printf "Checking block %d..." $BLOCK
  
  BLOCK_DATA=$(curl -s -X POST $RPC \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBlockByNumber\",\"params\":[\"$BLOCK_HEX\",true],\"id\":1}")
  
  if echo "$BLOCK_DATA" | grep -qi "$(echo $CONTRACT | tr '[:upper:]' '[:lower:]')"; then
    echo " ✅ FOUND!"
    FOUND=$((FOUND + 1))
    
    # Get timestamp
    TIMESTAMP=$(echo "$BLOCK_DATA" | grep -o '"timestamp":"0x[^"]*"' | head -1 | cut -d'"' -f4)
    if [ ! -z "$TIMESTAMP" ]; then
      TS_DEC=$((16#${TIMESTAMP:2}))
      DATE=$(date -d @$TS_DEC 2>/dev/null || date -r $TS_DEC 2>/dev/null || echo "N/A")
      echo "   Date: $DATE"
    fi
    
    # Extract transaction details
    echo "$BLOCK_DATA" | grep -o '"hash":"0x[^"]*"' | head -3 | while read line; do
      TX_HASH=$(echo $line | cut -d'"' -f4)
      echo "   TX: $TX_HASH"
    done
    echo ""
  else
    echo " no activity"
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESULTS:"
echo "   Blocks scanned: 51"
echo "   Blocks with activity: $FOUND"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FOUND -gt 0 ]; then
  echo "✅ SUCCESS: Found transaction activity!"
  echo "💡 These transactions will appear in the analytics table"
else
  echo "⚠️  No transactions found in scanned range"
  echo "💡 Transactions might be in a different block range"
fi
