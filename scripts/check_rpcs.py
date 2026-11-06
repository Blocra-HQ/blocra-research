#!/usr/bin/env python3
"""Check which public RPC endpoints actually work, and which a browser can call.

For every endpoint in chains.json (or a flat {label: url} file) this tries the probe that matches the chain's
protocol (Stellar/Soroban getLatestLedger, EVM eth_blockNumber, Solana getSlot,
Starknet starknet_blockNumber, CometBFT status, Sui checkpoint), and only counts an endpoint as alive when it
returns a real head block/slot, not a JSON error, and only counts it as fresh
when that head block is less than an hour old (a node, or a whole chain, that
stopped producing blocks still answers with its last head). It then sends a CORS
preflight like a browser would, because the BlocRA web app calls RPCs directly
from the page.

Usage:
    python3 scripts/check_rpcs.py                 # every RPC in chains.json
    python3 scripts/check_rpcs.py --out rpc_results.json

Standard library only.
"""
import argparse
import concurrent.futures
import datetime
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ORIGIN = "https://blocra.app"
TIMEOUT = 8
# Same limit as the backend: an older head block means the node is not synced.
STALE_AFTER_SECS = 3600

PROBES = [
    ("stellar", {"jsonrpc": "2.0", "id": 1, "method": "getLatestLedger"},
     lambda r: int(r["sequence"])),
    ("evm", {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
     lambda r: int(r, 16)),
    ("solana", {"jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []},
     lambda r: int(r)),
    ("starknet", {"jsonrpc": "2.0", "id": 1, "method": "starknet_blockNumber", "params": []},
     lambda r: int(r)),
    ("cometbft", {"jsonrpc": "2.0", "id": 1, "method": "status", "params": {}},
     lambda r: int(r["sync_info"]["latest_block_height"])),
    ("sui", {"jsonrpc": "2.0", "id": 1, "method": "sui_getLatestCheckpointSequenceNumber", "params": []},
     lambda r: int(r)),
]


def post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Origin": ORIGIN, "User-Agent": "blocra-rpc-check"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode() or "null"), resp.headers


def cors_ok(url):
    """True if a browser on another origin may POST JSON to this endpoint."""
    req = urllib.request.Request(
        url,
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
            # Cloudflare-fronted RPCs reject Python's default User-Agent.
            "User-Agent": "blocra-rpc-check",
        },
        method="OPTIONS",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            allow = resp.headers.get("Access-Control-Allow-Origin", "")
            return allow in ("*", ORIGIN)
    except Exception:
        return False


def iso_seconds(text):
    """Unix seconds from an RFC 3339 time with any number of fractional digits."""
    return datetime.datetime.strptime(text[:19], "%Y-%m-%dT%H:%M:%S").replace(
        tzinfo=datetime.timezone.utc).timestamp()


def head_time(url, protocol, head, probe_result):
    """Unix time of the head block, or None when the protocol has no cheap way to get it."""
    if protocol == "stellar":
        return int(probe_result["closeTime"])
    if protocol == "cometbft":
        return iso_seconds(probe_result["sync_info"]["latest_block_time"])
    if protocol == "evm":
        data, _ = post(url, {"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": ["latest", False]})
        return int(data["result"]["timestamp"], 16)
    if protocol == "starknet":
        data, _ = post(url, {"jsonrpc": "2.0", "id": 1, "method": "starknet_getBlockWithTxHashes", "params": ["latest"]})
        return int(data["result"]["timestamp"])
    if protocol == "solana":
        data, _ = post(url, {"jsonrpc": "2.0", "id": 1, "method": "getBlockTime", "params": [head]})
        return int(data["result"])
    return None


def check(chain, url):
    result = {"chain": chain, "url": url, "alive": False, "protocol": None,
              "head": None, "head_age_s": None, "fresh": None, "latency_ms": None,
              "browser_ok": False, "error": None}
    for protocol, payload, parse in PROBES:
        start = time.time()
        try:
            data, _ = post(url, payload)
        except urllib.error.HTTPError as e:
            result["error"] = f"HTTP {e.code}"
            continue
        except Exception as e:  # timeouts, DNS, TLS, non-JSON pages
            result["error"] = type(e).__name__
            continue
        if not isinstance(data, dict) or data.get("result") is None:
            continue
        try:
            head = parse(data["result"])
        except Exception:
            continue
        result.update(alive=True, protocol=protocol, head=head, error=None,
                      latency_ms=round((time.time() - start) * 1000))
        try:
            when = head_time(url, protocol, head, data["result"])
        except Exception:
            when = None
        if when is not None:
            result["head_age_s"] = max(0, round(time.time() - when))
            result["fresh"] = result["head_age_s"] <= STALE_AFTER_SECS
        break
    if result["alive"]:
        result["browser_ok"] = cors_ok(url)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--rpcs", default=str(Path(__file__).resolve().parent.parent / "chains.json"))
    parser.add_argument("--out", default="rpc_results.json")
    args = parser.parse_args()

    raw = json.loads(Path(args.rpcs).read_text())
    # chains.json: {id: {name, rpcs: [...]}}; flat files: {label: url}.
    endpoints = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            for i, url in enumerate(value["rpcs"]):
                endpoints[f"{value['name']} #{i + 1}" if i else value["name"]] = url
        else:
            endpoints[key] = value
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
        results = list(pool.map(lambda kv: check(*kv), endpoints.items()))
    results.sort(key=lambda r: (not r["alive"], r["chain"].lower()))

    alive = [r for r in results if r["alive"]]
    stale = [r for r in alive if r["fresh"] is False]
    print(f"{len(alive)}/{len(results)} endpoints alive, {len(stale)} of them stale, "
          f"{sum(r['browser_ok'] for r in alive)} callable from a browser\n")
    for r in results:
        if r["alive"]:
            cors = "browser ok" if r["browser_ok"] else "server only"
            age = r["head_age_s"]
            age_text = "age ?" if age is None else f"age {age // 86400}d" if age > 86400 else f"age {age}s"
            print(f"  {'STALE' if r['fresh'] is False else 'OK   '} {r['chain']:22} {r['protocol']:9} "
                  f"head {r['head']:>12}  {age_text:>9}  {r['latency_ms']:>5} ms  {cors:11}  {r['url']}")
    for r in results:
        if not r["alive"]:
            print(f"  DEAD {r['chain']:22} {r['error'] or 'no valid result':16} {r['url']}")

    Path(args.out).write_text(json.dumps(results, indent=2) + "\n")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
