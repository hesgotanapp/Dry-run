#!/usr/bin/env python3
"""
New meme coin screener (Solana).

Pulls recently listed tokens from DexScreener, filters to pairs with real
liquidity/trading, runs a RugCheck safety report on survivors, and prints a
ranked list with a HEURISTIC score (0-100).

The score is NOT a probability of pumping. It measures:
  * safety  (0-55): mint/freeze authority, holder concentration, LP lock,
                    RugCheck risk flags
  * health  (0-45): liquidity depth, buy/sell balance, volume vs liquidity,
                    age, price action that is not an obvious spike-and-dump
Not financial advice. Most new meme coins go to zero.

Usage: python3 memecoin_screener.py [--top 8] [--min-liq 15000] [--max-age-h 72]
"""
import argparse
import json
import sys
import time
import urllib.request

DEX = "https://api.dexscreener.com"
RUG = "https://api.rugcheck.xyz/v1"
UA = {"User-Agent": "memecoin-screener/1.0"}


def get(url, retries=2):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.load(r)
        except Exception:
            if i == retries:
                return None
            time.sleep(1.5 * (i + 1))


def candidates():
    addrs = []
    for path in ("/token-profiles/latest/v1", "/token-boosts/latest/v1", "/token-boosts/top/v1"):
        data = get(DEX + path) or []
        for t in data:
            if t.get("chainId") == "solana":
                addrs.append(t["tokenAddress"])
    for path in ("/stats/recent", "/stats/trending", "/stats/new_tokens"):
        data = get(RUG + path) or []
        for t in data:
            m = t.get("mint") or (t.get("token") or {}).get("mint")
            if m:
                addrs.append(m)
    seen, out = set(), []
    for a in addrs:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


def fetch_pairs(addrs):
    best = {}
    for i in range(0, len(addrs), 30):
        chunk = addrs[i:i + 30]
        data = get(f"{DEX}/tokens/v1/solana/{','.join(chunk)}") or []
        for p in data:
            base = p["baseToken"]["address"]
            liq = (p.get("liquidity") or {}).get("usd") or 0
            if base not in best or liq > ((best[base].get("liquidity") or {}).get("usd") or 0):
                best[base] = p
        time.sleep(0.4)
    return best


def pct(x, lo, hi):
    """Linear 0..1 between lo and hi."""
    if x is None:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def score(pair, rc):
    flags, good = [], []
    liq = (pair.get("liquidity") or {}).get("usd") or 0
    vol24 = (pair.get("volume") or {}).get("h24") or 0
    tx = (pair.get("txns") or {}).get("h24") or {}
    buys, sells = tx.get("buys", 0), tx.get("sells", 0)
    pc = pair.get("priceChange") or {}
    age_h = (time.time() * 1000 - (pair.get("pairCreatedAt") or 0)) / 3.6e6

    # ---- safety (55)
    s = 55.0
    rep = rc or {}
    if rep.get("mintAuthority"):
        s -= 20
        flags.append("mint authority NOT renounced")
    else:
        good.append("mint renounced")
    if rep.get("freezeAuthority"):
        s -= 12
        flags.append("freeze authority active")
    top = sorted((rep.get("topHolders") or []), key=lambda h: -(h.get("pct") or 0))
    # exclude liquidity pools / known AMM accounts when RugCheck labels them
    holders = [h for h in top if not h.get("insider") and not (h.get("owner") or "") == ""] or top
    top10 = sum(h.get("pct", 0) for h in holders[:10])
    if holders:
        if top10 > 50:
            s -= 18
            flags.append(f"top10 holders {top10:.0f}%")
        elif top10 > 30:
            s -= 8
            flags.append(f"top10 holders {top10:.0f}%")
        else:
            good.append(f"top10 holders {top10:.0f}%")
    lp = None
    for m in rep.get("markets") or []:
        l = (m.get("lp") or {}).get("lpLockedPct")
        if l is not None:
            lp = max(lp or 0, l)
    if lp is not None:
        if lp < 50:
            s -= 12
            flags.append(f"LP only {lp:.0f}% locked/burned")
        elif lp >= 90:
            good.append(f"LP {lp:.0f}% locked/burned")
    danger = [r for r in (rep.get("risks") or []) if r.get("level") == "danger"]
    warn = [r for r in (rep.get("risks") or []) if r.get("level") == "warn"]
    if danger:
        s -= min(25, 12 * len(danger))
        flags += [f"RugCheck danger: {r.get('name')}" for r in danger[:3]]
    if warn:
        s -= min(8, 3 * len(warn))
        flags += [f"RugCheck warn: {r.get('name')}" for r in warn[:2]]
    if rep.get("rugged"):
        s = 0
        flags.append("RUGGED")
    s = max(0.0, s)

    # ---- health (45)
    h = 0.0
    h += 14 * pct(liq, 10_000, 250_000)                       # liquidity depth
    total = buys + sells
    if total >= 100:
        bal = buys / total
        h += 8 * (1 - abs(bal - 0.55) / 0.55)                  # balanced buys/sells
        good.append(f"{total} txns/24h, {bal*100:.0f}% buys")
    ratio = vol24 / liq if liq else 0
    h += 8 * (1 - min(abs(ratio - 4), 4) / 4) if liq else 0    # healthy turnover ~4x liq
    if ratio > 25:
        flags.append("volume/liquidity extreme (possible wash trading)")
        h -= 6
    h += 7 * pct(age_h, 2, 36)                                 # survived a while
    h5, h1, h24 = pc.get("h1"), pc.get("h6"), pc.get("h24")
    if h24 is not None:
        if h24 < -60:
            h -= 8
            flags.append(f"{h24:.0f}% in 24h")
        elif h24 > 1500:
            h -= 4
            flags.append(f"already +{h24:.0f}% (late)")
        elif 0 <= h24 <= 600:
            h += 8
    if liq < 15_000:
        flags.append(f"thin liquidity ${liq:,.0f}")
    h = max(0.0, min(45.0, h))

    return round(s + h), flags, good, age_h, liq, vol24, buys, sells, pc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--min-liq", type=float, default=15000)
    ap.add_argument("--max-age-h", type=float, default=72)
    ap.add_argument("--min-age-h", type=float, default=1)
    a = ap.parse_args()

    addrs = candidates()
    print(f"[candidates] {len(addrs)} addresses", file=sys.stderr)
    pairs = fetch_pairs(addrs)
    pool = []
    for addr, p in pairs.items():
        liq = (p.get("liquidity") or {}).get("usd") or 0
        age_h = (time.time() * 1000 - (p.get("pairCreatedAt") or 0)) / 3.6e6
        if liq >= a.min_liq and a.min_age_h <= age_h <= a.max_age_h:
            pool.append((addr, p))
    print(f"[filtered] {len(pool)} with liq>=${a.min_liq:,.0f}, age {a.min_age_h}-{a.max_age_h}h",
          file=sys.stderr)

    rows = []
    for addr, p in pool[:40]:
        rc = get(f"{RUG}/tokens/{addr}/report")
        sc, flags, good, age_h, liq, vol, b, s, pc = score(p, rc)
        rows.append(dict(score=sc, symbol=p["baseToken"]["symbol"], name=p["baseToken"]["name"],
                         addr=addr, url=p.get("url"), age_h=age_h, liq=liq, vol=vol,
                         buys=b, sells=s, mcap=p.get("marketCap") or p.get("fdv"),
                         pc=pc, flags=flags, good=good))
        time.sleep(0.5)
    rows.sort(key=lambda r: -r["score"])
    print(json.dumps(rows[: a.top], indent=2))


if __name__ == "__main__":
    main()
