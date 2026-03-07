#!/bin/bash

CONTRACT="0xCd45aC05fe7C014D6B2F62b3446E2A91D661a236"
RPC="https://mainnet.base.org"

echo "🔍 Fetching transactions for Base contract: $CONTRACT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get latest block
echo "📊 Getting latest block..."
LATEST=$(curl -s -X POST $RPC \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | \
  grep -o '"result":"[^"]*"' | cut -d'"' -f4)

LATEST_DEC=$((16#${LATEST:2}))
echo "✅ Latest block: $LATEST_DEC"

# Calculate range (last 100 blocks for quick test)
FROM_DEC=$((LATEST_DEC - 100))
FROM_HEX=$(printf "0x%x" $FROM_DEC)

echo "📦 Scanning blocks: $FROM_DEC to $LATEST_DEC (100 blocks)"
echo ""

# Check a few blocks for transactions
FOUND=0
for i in {0..10}; do
  BLOCK=$((FROM_DEC + i * 10))
  BLOCK_HEX=$(printf "0x%x" $BLOCK)
  
  echo "🔍 Checking block $BLOCK..."
  
  BLOCK_DATA=$(curl -s -X POST $RPC \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBlockByNumber\",\"params\":[\"$BLOCK_HEX\",true],\"id\":1}")
  
  # Check if contract is in any transaction
  if echo "$BLOCK_DATA" | grep -qi "$CONTRACT"; then
    echo "   ✅ Found transaction(s) involving contract!"
    FOUND=$((FOUND + 1))
    
    # Extract transaction hashes
    echo "$BLOCK_DATA" | grep -o '"hash":"0x[^"]*"' | head -3 | while read line; do
      TX_HASH=$(echo $line | cut -d'"' -f4)
      echo "      TX: $TX_HASH"
    done
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESULTS:"
echo "   Blocks checked: 11"
echo "   Blocks with transactions: $FOUND"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FOUND -gt 0 ]; then
  echo "✅ SUCCESS: Contract has transaction activity!"
  echo "💡 The transaction table WILL show data for this contract"
else
  echo "⚠️  No transactions found in sampled blocks"
  echo "💡 Try scanning more blocks or a different range"
fi
