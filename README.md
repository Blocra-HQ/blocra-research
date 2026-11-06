# blocra-research

The data research behind [BlocRA](https://github.com/Blocra-HQ): which public blockchain RPC endpoints
actually work, and which of them a web page can call directly.

BlocRA's frontend talks to RPC nodes from the browser, and its backend calls them from the server. A public
endpoint that is down, rate-limited, or blocks cross-origin requests silently breaks dashboards. This repo
keeps a verified list of endpoints and the tool that verifies them.

## Contents

| Path | What it is |
|------|------------|
| [`chains.json`](chains.json) | The verified chain registry: 37 chains, each with its currency, block explorer and RPC endpoints in priority order |
| [`scripts/check_rpcs.py`](scripts/check_rpcs.py) | Checks every endpoint: is it alive, is its head block current, and can a browser call it? |
| [`scripts/gen_chains_ts.py`](scripts/gen_chains_ts.py) | Generates the frontend's `src/config/chains.ts` from `chains.json` |
| [`RPC.ipynb`](RPC.ipynb) | The original exploration notebook (superseded by the checker; see below) |
| `scripts/*.sh` | One-off research and setup scripts (see [Other scripts](#other-scripts)) |
| [`migration.json`](migration.json) | A legacy SQL migration (see [Legacy files](#legacy-files)) |

## The chain registry

`chains.json` maps a chain id to its settings:

```json
"stellar": {
  "name": "Stellar",
  "type": "stellar",
  "currency": "XLM",
  "explorer": "https://stellar.expert/explorer/public",
  "rpcs": ["https://mainnet.sorobanrpc.com", "..."],
  "horizon": ["https://horizon.stellar.org", "https://horizon.stellar.lobstr.co"]
}
```

- **Stellar comes first.** BlocRA is built for Stellar, so it is listed first with four Soroban RPC
  endpoints and two Horizon servers.
- **The other 36 chains** are Starknet, Solana, 31 EVM networks (Ethereum, Base, Arbitrum, Optimism,
  Polygon, BNB Chain and more) and three CometBFT chains.
- **Order matters.** RPCs are listed in priority order. Clients try the first one and fall back to the
  next on failure.
- **Retired chains are removed.** Blast (wound down after its 26 October 2026 exit deadline; its RPC
  domain no longer resolves) and Moonbeam and Moonriver (no blocks since 10 August 2026, after the
  network's announced shutdown) were dropped on 2026-11-06. Every public endpoint for them is either
  gone or still serves their final block.

Who uses it:

| Consumer | How |
|----------|-----|
| [blocra-frontend](https://github.com/Blocra-HQ/blocra-frontend) | `src/config/chains.ts` is generated from this file by `scripts/gen_chains_ts.py` (CometBFT chains become type `cosmos`) |
| [blocra-backend](https://github.com/Blocra-HQ/blocra-backend) | Embeds a copy as `src/config/chains.json` for its multi-chain dashboard stats; its built-in Stellar Horizon and Starknet RPC lists are also taken from here |

## Checking endpoints

`scripts/check_rpcs.py` needs only the Python standard library.

```bash
python3 scripts/check_rpcs.py                          # every RPC in chains.json
python3 scripts/check_rpcs.py --out results.json       # choose the output file
python3 scripts/check_rpcs.py --rpcs other.json        # a flat {"label": "url"} file also works
```

For each endpoint it:

1. **Probes with the chain's own protocol.** It tries Stellar `getLatestLedger`, EVM `eth_blockNumber`,
   Solana `getSlot`, Starknet `starknet_blockNumber`, CometBFT `status` and Sui
   `sui_getLatestCheckpointSequenceNumber`.
2. **Counts an endpoint as alive only if it returns a real head block, ledger or slot.** A JSON error
   reply, an HTML landing page or a timeout counts as dead.
3. **Checks that the head block is current.** It reads the head block's timestamp and marks the endpoint
   `STALE` when it is more than an hour old, the same limit the backend uses. A node that stopped
   syncing, or a chain that stopped producing blocks, still answers with its last head.
4. **Sends a browser-style CORS preflight.** This shows whether the web app can call the endpoint
   directly ("browser ok") or only a server can ("server only").

Example output, from the endpoints of the retired chains plus one healthy one:

```
3/4 endpoints alive, 2 of them stale, 3 callable from a browser

  OK    Ethereum               evm       head     26353567    age 11s   1136 ms  browser ok   https://eth.drpc.org
  STALE Moonbeam               evm       head     16796699    age 87d   1342 ms  browser ok   https://1rpc.io/glmr
  STALE Moonriver              evm       head     17381654    age 87d   1372 ms  browser ok   https://moonriver.drpc.org
  DEAD Blast                  URLError         https://rpc.blast.io
```

Results are written to `rpc_results.json`, which is gitignored because it changes on every run.

## Adding or changing a chain

1. Edit `chains.json`. Put browser-callable endpoints first.
2. Run `python3 scripts/check_rpcs.py` and confirm every endpoint is alive and fresh, and at least one
   per chain is "browser ok".
3. Regenerate the frontend's chain list and copy the registry to the backend:

   ```bash
   python3 scripts/gen_chains_ts.py ../blocra-frontend/src/config/chains.ts
   cp chains.json ../blocra-backend/src/config/chains.json
   ```

   If you changed the Stellar Horizon or Starknet endpoints, update the backend's built-in lists in
   `src/services/stellar.rs` and `src/services/rpc.rs` as well.

## RPC.ipynb

The notebook that started this work. It pings about 100 endpoints. Two things make its results
unreliable, which is why the checker replaced it:

- **One probe for every chain.** It calls `eth_blockNumber` everywhere, which non-EVM chains (Cosmos,
  Aptos, Sui, Solana) don't support.
- **Errors counted as alive.** Any JSON reply marked an endpoint alive, including error replies. Many
  dead hosts and landing pages showed up as healthy.

It is kept for reference. Its Blast and Moonriver endpoints belong to chains that have since shut down.

## Other scripts

| Script | Purpose |
|--------|---------|
| `scripts/find-transactions.sh` | Scans Base mainnet for transactions to contract `0xCd45…a236` from its deployment block |
| `scripts/find-december-transactions.sh` | The same scan, limited to the first 50,000 blocks after deployment (December 2025) |
| `scripts/fetch-base-transactions.sh` | Fetches recent transactions for the same Base contract |
| `scripts/setup-gpt-oss.sh` | Installs the tooling to serve the open-weight gpt-oss model locally (vLLM, Transformers or Ollama). The backend's AI analyst can use it through `AI_BASE_URL` / `AI_MODEL` |

The Base scripts were one-off investigations into a single contract's history. They call the public
`mainnet.base.org` endpoint with `curl`.

## Legacy files

`migration.json` holds a PostgreSQL migration from an earlier version of BlocRA that used Supabase. It
creates `queries` and `query_results` tables with row-level security policies. The current backend
uses SQLite with its own migrations, so nothing runs this file.

## Related repositories

| Repo | Purpose |
|------|---------|
| [blocra-frontend](https://github.com/Blocra-HQ/blocra-frontend) | The web app |
| [blocra-backend](https://github.com/Blocra-HQ/blocra-backend) | The Rust API |
| [blocra-contracts](https://github.com/Blocra-HQ/blocra-contracts) | The Soroban report registry contract |
