#!/usr/bin/env python3
"""Write the BlocRA frontend's src/config/chains.ts from chains.json.

The registry is the source of truth; the backend embeds a copy of it and the
frontend gets this generated TypeScript module, so the three always agree.
CometBFT chains get the frontend type 'cosmos'.

Usage:
    python3 scripts/gen_chains_ts.py ../blocra-frontend/src/config/chains.ts
    python3 scripts/gen_chains_ts.py -        # print to stdout

Standard library only.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

FRONTEND_TYPE = {"cometbft": "cosmos"}

HEADER = """\
// Chains BlocRA can analyze, with fallback RPCs in priority order. Stellar is
// first, so it is the default chain.
//
// Generated from blocra-research/chains.json by scripts/gen_chains_ts.py; do
// not edit by hand. Every endpoint is checked by scripts/check_rpcs.py (alive,
// fresh head block, callable from a browser). Last verified {date}. Re-run the
// checker before adding or changing RPCs. CometBFT chains have type 'cosmos'.

export interface ChainConfig {{
  id: string;
  name: string;
  rpcs: string[];
  type: 'stellar' | 'evm' | 'cosmos' | 'solana' | 'starknet' | 'substrate';
  /** Horizon servers (Stellar only). */
  horizon?: string[];
  nativeCurrency: string;
  explorer: string;
}}

export const SUPPORTED_CHAINS: ChainConfig[] = [
"""

FOOTER = """\
];

export function getChain(id: string): ChainConfig | undefined {
  return SUPPORTED_CHAINS.find((c) => c.id === id);
}

/** Starknet RPCs, with VITE_STARKNET_RPC_URL (if set) tried first. */
export const STARKNET_RPCS: string[] = [
  ...(import.meta.env.VITE_STARKNET_RPC_URL ? [import.meta.env.VITE_STARKNET_RPC_URL as string] : []),
  ...(getChain('starknet')?.rpcs ?? []),
];
"""


def ts(value):
    """A TypeScript single-quoted string literal."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def entry(chain_id, chain):
    lines = ["  {", f"    id: {ts(chain_id)},", f"    name: {ts(chain['name'])},", "    rpcs: ["]
    lines.append(",\n".join(f"      {ts(url)}" for url in chain["rpcs"]))
    lines.append("    ],")
    if chain.get("horizon"):
        lines.append(f"    horizon: [{', '.join(ts(u) for u in chain['horizon'])}],")
    lines.append(f"    type: {ts(FRONTEND_TYPE.get(chain['type'], chain['type']))},")
    lines.append(f"    nativeCurrency: {ts(chain['currency'])},")
    lines.append(f"    explorer: {ts(chain['explorer'])}")
    lines.append("  }")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", help="path to chains.ts, or - for stdout")
    parser.add_argument("--chains", default=str(Path(__file__).resolve().parent.parent / "chains.json"))
    parser.add_argument("--date", default=datetime.date.today().isoformat(), help="'Last verified' date")
    args = parser.parse_args()

    chains = json.loads(Path(args.chains).read_text())
    body = ",\n".join(entry(cid, c) for cid, c in chains.items())
    text = HEADER.format(date=args.date) + body + "\n" + FOOTER
    if args.out == "-":
        sys.stdout.write(text)
    else:
        Path(args.out).write_text(text)
        print(f"Wrote {len(chains)} chains to {args.out}")


if __name__ == "__main__":
    main()
