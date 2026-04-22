"""
LiveSimulator.py

Polls live odds, detects arbitrage opportunities, simulates bets, and logs
everything to sim_log.csv for later manual PnL review.

Usage:
    python LiveSimulator.py                        # single scan
    python LiveSimulator.py --loop --interval 300  # scan every 5 minutes
    python LiveSimulator.py --summary              # print PnL summary of log
"""

import argparse
import csv
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from OddsApiFetch import fetch_active_sports, fetch_odds_structured

LOG_FILE = os.path.join(os.path.dirname(__file__), "sim_log.csv")

LOG_COLUMNS = [
    "logged_at",
    "event_id",
    "sport",
    "commence_time",
    "home_team",
    "away_team",
    # odds snapshot
    "home_odds",
    "home_bookie",
    "away_odds",
    "away_bookie",
    "draw_odds",
    "draw_bookie",
    # arb metrics
    "total_implied_prob",
    "arb_pct",
    "skew_factor",
    # simulated stakes
    "stake_home",
    "stake_away",
    "stake_draw",
    "total_stake",
    # per-outcome payouts (profit after all stakes deducted)
    "profit_if_home_wins",
    "profit_if_away_wins",
    "profit_if_draw",
    "min_profit",   # worst case — what you're guaranteed at minimum
    "max_profit",   # best case — what you get if the favorite wins
    # filled in manually later
    "actual_winner",
    "actual_pnl",
    "notes",
]

# --- Config ---
STAKE_PER_BET = 1000.0   # virtual dollars per arb opportunity
MIN_ARB_PCT = 0.5        # minimum arb % to act on (0.5 = 0.5%)
# Skew factor: 0.0 = equal payout on all outcomes (safe)
#              1.0 = max stake on favorite, others break even (aggressive)
#              0.5 = balanced middle ground
SKEW_FACTOR = 0.7


# ---------------------------------------------------------------------------
# Arbitrage detection
# ---------------------------------------------------------------------------

def detect_arb(event: Dict, skew_factor: float = SKEW_FACTOR) -> Optional[Dict]:
    """
    Detect arbitrage and compute skewed stakes.

    skew_factor controls how aggressively stakes are pushed toward the favorite:
      0.0 = equal profit on all outcomes (classic arb)
      1.0 = max stake on favorite, other outcomes break even (zero profit)
      0.5 = halfway between the two

    All outcomes always return >= 0 profit — still fully risk-free.
    """
    home_odds = event.get("home_odds")
    away_odds = event.get("away_odds")
    draw_odds = event.get("draw_odds")

    if not home_odds or not away_odds:
        return None
    if home_odds <= 1 or away_odds <= 1:
        return None
    if draw_odds is not None and draw_odds <= 1:
        draw_odds = None

    prob_home = 1 / home_odds
    prob_away = 1 / away_odds
    prob_draw = (1 / draw_odds) if draw_odds else 0.0
    total_prob = prob_home + prob_away + prob_draw

    if total_prob >= 1.0:
        return None
    arb_pct = (1 - total_prob) * 100
    if arb_pct < MIN_ARB_PCT:
        return None

    stake = STAKE_PER_BET
    arb_surplus = stake * (1 - total_prob)  # the guaranteed profit pool

    # --- Equal-payout stakes (baseline) ---
    eq_stake_home = stake * (prob_home / total_prob)
    eq_stake_away = stake * (prob_away / total_prob)
    eq_stake_draw = stake * (prob_draw / total_prob) if draw_odds else 0.0

    # --- Breakeven stakes (minimum per outcome to not lose money) ---
    be_stake_home = stake / home_odds   # if home wins, get back exactly `stake`
    be_stake_away = stake / away_odds
    be_stake_draw = (stake / draw_odds) if draw_odds else 0.0

    # --- Identify favorite (lowest odds = shortest price = most likely) ---
    outcomes = [("home", home_odds), ("away", away_odds)]
    if draw_odds:
        outcomes.append(("draw", draw_odds))
    favorite = min(outcomes, key=lambda x: x[1])[0]

    # --- Skewed stakes: interpolate between equal-payout and max-aggressive ---
    # At skew=1: favorite gets all the arb_surplus on top of its breakeven stake;
    #            others just get their breakeven stake.
    def skewed_stake(eq_s, be_s, is_fav):
        extra = arb_surplus if is_fav else 0.0
        return (1 - skew_factor) * eq_s + skew_factor * (be_s + extra)

    stake_home = skewed_stake(eq_stake_home, be_stake_home, favorite == "home")
    stake_away = skewed_stake(eq_stake_away, be_stake_away, favorite == "away")
    stake_draw = skewed_stake(eq_stake_draw, be_stake_draw, favorite == "draw") if draw_odds else 0.0

    # --- Per-outcome profits (gross return minus total stake) ---
    profit_home = round(stake_home * home_odds - stake, 2)
    profit_away = round(stake_away * away_odds - stake, 2)
    profit_draw = round(stake_draw * draw_odds - stake, 2) if draw_odds else None

    profits = [p for p in [profit_home, profit_away, profit_draw] if p is not None]

    return {
        "total_implied_prob": round(total_prob, 6),
        "arb_pct": round(arb_pct, 4),
        "skew_factor": skew_factor,
        "stake_home": round(stake_home, 2),
        "stake_away": round(stake_away, 2),
        "stake_draw": round(stake_draw, 2) if draw_odds else 0.0,
        "total_stake": round(stake, 2),
        "profit_if_home_wins": profit_home,
        "profit_if_away_wins": profit_away,
        "profit_if_draw": profit_draw if draw_odds else "",
        "min_profit": round(min(profits), 2),
        "max_profit": round(max(profits), 2),
        # convenience for printing
        "_favorite": favorite,
        "_implied_probs": {
            "home": round(prob_home / total_prob * 100, 1),
            "away": round(prob_away / total_prob * 100, 1),
            "draw": round(prob_draw / total_prob * 100, 1) if draw_odds else None,
        },
    }


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _ensure_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
            writer.writeheader()


def log_bet(event: Dict, arb: Dict):
    _ensure_log()
    row = {col: "" for col in LOG_COLUMNS}
    # strip internal helper keys (prefixed with _) before writing
    loggable_arb = {k: v for k, v in arb.items() if not k.startswith("_")}
    row.update({
        "logged_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "event_id": event["event_id"],
        "sport": event["sport"],
        "commence_time": event["commence_time"],
        "home_team": event["home_team"],
        "away_team": event["away_team"],
        "home_odds": event["home_odds"],
        "home_bookie": event["home_bookie"],
        "away_odds": event["away_odds"],
        "away_bookie": event["away_bookie"],
        "draw_odds": event.get("draw_odds") or "",
        "draw_bookie": event.get("draw_bookie") or "",
        **loggable_arb,
    })
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        writer.writerow(row)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def run_scan(sports: Optional[List[str]] = None) -> int:
    """
    Scan sports for arb opportunities and log any found.
    If sports is None, fetches all currently active sports from the API (free endpoint).
    Returns number of bets logged.
    """
    if sports is None:
        print("  Fetching active sports from API...")
        active = fetch_active_sports()
        sports = [s["key"] for s in active]
        print(f"  Found {len(sports)} active sports to scan.\n")

    bets_logged = 0
    for sport in sports:
        print(f"  Scanning {sport}...", end=" ")
        try:
            events = fetch_odds_structured(sport)
        except Exception as e:
            print(f"SKIP ({e})")
            continue

        now = datetime.now(timezone.utc)
        upcoming = [
            e for e in events
            if datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) > now
        ]
        skipped_live = len(events) - len(upcoming)
        if skipped_live:
            print(f"(skipped {skipped_live} live) ", end="")

        arbs_found = 0
        for event in upcoming:
            arb = detect_arb(event)
            if arb:
                log_bet(event, arb)
                arbs_found += 1
                bets_logged += 1

                probs = arb["_implied_probs"]
                fav = arb["_favorite"]
                home = event["home_team"]
                away = event["away_team"]

                print(f"\n    ARB  {home} vs {away}")
                print(f"         Arb margin: {arb['arb_pct']:.2f}%  |  Skew: {arb['skew_factor']}  |  Total stake: ${arb['total_stake']:.0f}")
                print(f"         Favorite: {fav.upper()}")
                print(f"         {'Outcome':<12} {'Odds':>6}  {'Implied%':>9}  {'Stake':>8}  {'Profit if wins':>14}")
                print(f"         {'-'*56}")

                home_fav = " <-- fav" if fav == "home" else ""
                away_fav = " <-- fav" if fav == "away" else ""
                draw_fav = " <-- fav" if fav == "draw" else ""

                print(f"         {'Home':<12} {event['home_odds']:>6.2f}  {probs['home']:>8.1f}%  "
                      f"${arb['stake_home']:>7.2f}  ${arb['profit_if_home_wins']:>12.2f}{home_fav}")
                print(f"         {'Away':<12} {event['away_odds']:>6.2f}  {probs['away']:>8.1f}%  "
                      f"${arb['stake_away']:>7.2f}  ${arb['profit_if_away_wins']:>12.2f}{away_fav}")

                if event.get("draw_odds"):
                    print(f"         {'Draw':<12} {event['draw_odds']:>6.2f}  {probs['draw']:>8.1f}%  "
                          f"${arb['stake_draw']:>7.2f}  ${arb['profit_if_draw']:>12.2f}{draw_fav}")

                print(f"         Worst case: ${arb['min_profit']:.2f}  |  Best case: ${arb['max_profit']:.2f}")

        if arbs_found == 0:
            print("no arb found")

    return bets_logged


# ---------------------------------------------------------------------------
# PnL summary (for manually-filled actual_pnl column)
# ---------------------------------------------------------------------------

def print_summary():
    if not os.path.exists(LOG_FILE):
        print("No log file found yet.")
        return

    with open(LOG_FILE, newline="") as f:
        rows = list(csv.DictReader(f))

    total_bets = len(rows)
    settled = [r for r in rows if r["actual_pnl"] != ""]
    unsettled = total_bets - len(settled)

    simulated_min_profit = sum(float(r["min_profit"]) for r in rows if r.get("min_profit") not in ("", None))
    simulated_max_profit = sum(float(r["max_profit"]) for r in rows if r.get("max_profit") not in ("", None))

    actual_pnl = sum(float(r["actual_pnl"]) for r in settled) if settled else None

    print(f"\n=== SIM LOG SUMMARY ===")
    print(f"Total bets logged : {total_bets}")
    print(f"Settled           : {len(settled)}")
    print(f"Unsettled         : {unsettled}")
    print(f"Simulated profit  : ${simulated_min_profit:.2f} — ${simulated_max_profit:.2f}  (worst → best case)")
    if actual_pnl is not None:
        print(f"Actual PnL        : ${actual_pnl:.2f}  (from {len(settled)} settled bets)")
    print(f"Log file          : {LOG_FILE}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live arb simulator")
    parser.add_argument("--loop", action="store_true", help="Keep scanning on an interval")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between scans (default 300)")
    parser.add_argument("--summary", action="store_true", help="Print PnL summary from log and exit")
    parser.add_argument("--sports", nargs="+", default=None, help="Sport keys to scan (default: all active from API)")
    args = parser.parse_args()

    if args.summary:
        print_summary()
    elif args.loop:
        print(f"Starting loop scan every {args.interval}s. Ctrl+C to stop.")
        while True:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{ts}] Running scan...")
            n = run_scan(args.sports)
            print(f"  => {n} bet(s) logged this scan.")
            time.sleep(args.interval)
    else:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] Running single scan...")
        n = run_scan(args.sports)
        print(f"\n=> {n} bet(s) logged. See {LOG_FILE}")
        print_summary()
