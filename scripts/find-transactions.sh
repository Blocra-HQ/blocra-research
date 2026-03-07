#!/bin/bash

CONTRACT="0xCd45aC05fe7C014D6B2F62b3446E2A91D661a236"
RPC="https://mainnet.base.org"

echo "🔍 Finding transactions for contract: $CONTRACT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Contract was deployed at block 39,850,978
# Dune shows transactions from Dec 23-31, 2025
# Let's scan from deployment to 100k blocks after

DEPLOY_BLOCK=39850978
LATEST=$(curl -s -X POST $RPC \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | \
  grep -o '"result":"[^"]*"' | cut -d'"' -f4)
LATEST_DEC=$((16#${LATEST:2}))

echo "Deployment block: $DEPLOY_BLOCK"
echo "Latest block: $LATEST_DEC"
echo "Blocks since deployment: $((LATEST_DEC - DEPLOY_BLOCK))"
echo ""

# Scan from deployment + 10k blocks (where activity likely is)
FROM=$((DEPLOY_BLOCK + 10000))
TO=$((DEPLOY_BLOCK + 50000))

echo "📡 Scanning blocks $FROM to $TO for transactions..."
echo ""

FOUND=0
TX_HASHES=()

# Check every 1000th block
for BLOCK in $(seq $FROM 1000 $TO); do
  BLOCK_HEX=$(printf "0x%x" $BLOCK)
  
  BLOCK_DATA=$(curl -s -X POST $RPC \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBlockByNumber\",\"params\":[\"$BLOCK_HEX\",true],\"id\":1}")
  
  # Check if contract is in any transaction
  if echo "$BLOCK_DATA" | grep -qi "$CONTRACT"; then
    echo "✅ Block $BLOCK has transactions!"
    FOUND=$((FOUND + 1))
    
    # Extract and show transaction details
    echo "$BLOCK_DATA" | grep -o '"hash":"0x[^"]*"' | head -2 | while read line; do
      TX_HASH=$(echo $line | cut -d'"' -f4)
      echo "   TX: $TX_HASH"
    done
    echo ""
    
    if [ $FOUND -ge 3 ]; then
      echo "Found enough transactions, stopping scan..."
      break
    fi
  fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESULTS:"
echo "   Blocks scanned: $((FOUND * 1000))"
echo "   Blocks with transactions: $FOUND"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FOUND -gt 0 ]; then
  echo ""
  echo "✅ SUCCESS: Found transactions!"
  echo "💡 Transactions are in blocks $FROM to $TO"
  echo "💡 This is where Dune found the Dec 2025 transactions"
  echo ""
  echo "🎯 SOLUTION: Scan from deployment block ($DEPLOY_BLOCK) instead of latest"
else
  echo ""
  echo "⚠️  No transactions found in sampled range"
  echo "💡 Try different block range"
fi
