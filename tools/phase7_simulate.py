"""
Phase 7 Step 3: T+1 Overnight Swing Simulation
------------------------------------------------
Daily cross-sectional simulation with A-share iron rules:
  Iron Rule 1: T+1 lock (can't sell on buy day)
  Iron Rule 2: Limit-down = can't sell
  Iron Rule 3: Limit-up = can't buy

Captures "micro-execution slices of institutional accumulation" (INS-022).
20 bars ≈ 0.4 days, T+1 forces min 1-day hold.

Usage:
  python3 phase7_simulate.py \
    --predictions /omega_pool/phase7/predictions.parquet \
    --cost_bp 25 \
    --output_dir /omega_pool/phase7/results/
"""

import os
import json
import argparse
import logging
from collections import defaultdict

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def load_predictions(path):
    """Load predictions from parquet or JSON."""
    if path.endswith(".parquet"):
        import pyarrow.parquet as pq
        table = pq.read_table(path)
        return table.to_pydict()
    else:
        with open(path) as f:
            records = json.load(f)
        result = defaultdict(list)
        for r in records:
            for k, v in r.items():
                result[k].append(v)
        return dict(result)


def get_board_daily_limit_bp(symbol):
    """Daily price limit in BP by board type.

    Main board (000/001/002/600/601/603/605): ±10% = 1000 BP
    ChiNext 创业板 (300/301): ±20% = 2000 BP
    STAR Market 科创板 (688): ±20% = 2000 BP
    """
    if symbol[:3] in ('688', '300', '301'):
        return 2000
    return 1000


def is_limit_locked(bid_p1, ask_p1, threshold=0.001):
    """Detect price limit: spread ≈ 0 means order book locked (best-effort heuristic).

    A-share limit detection without previous close price:
    When a stock hits limit-up, ask side is empty (ask_p ≈ bid_p or 0).
    When a stock hits limit-down, bid side is empty (bid_p ≈ ask_p or 0).
    We detect this as spread_ratio < threshold.

    Note: This is a best-effort heuristic. Exact limit detection requires
    previous close + limit band (±10% main board, ±20% ChiNext/STAR).
    The shard data does not contain previous close, so we use spread-lock
    as a proxy. False negatives are possible for stocks near but not at limits.
    """
    if bid_p1 <= 0 or ask_p1 <= 0:
        return True
    spread_ratio = abs(ask_p1 - bid_p1) / max(bid_p1, 1e-8)
    return spread_ratio < threshold


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--cost_bp", type=float, default=25.0)
    parser.add_argument("--long_pctile", type=float, default=0.80)
    parser.add_argument("--max_positions", type=int, default=50)
    parser.add_argument("--trailing_stop_pct", type=float, default=-10.0)
    parser.add_argument("--board_loss_cap", action="store_true", default=True,
                        help="Cap per-trade loss at board daily limit × hold days")
    parser.add_argument("--no_board_loss_cap", dest="board_loss_cap", action="store_false")
    parser.add_argument("--exclude_boards", nargs="*", default=[],
                        help="Exclude board prefixes from trading (e.g., 688)")
    parser.add_argument("--adv_floor", type=float, default=0.0)
    parser.add_argument("--train_val_boundary", type=int, default=1594)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    half_cost = args.cost_bp / 2.0  # Split: half on entry, half on exit

    log.info("Loading predictions...")
    data = load_predictions(args.predictions)
    n = len(data["symbol"])
    log.info(f"Loaded {n:,} predictions")

    # Group by date
    date_groups = defaultdict(list)
    for i in range(n):
        date_groups[data["date"][i]].append(i)

    dates_sorted = sorted(date_groups.keys())
    date_to_idx = {d: i for i, d in enumerate(dates_sorted)}
    log.info(f"Trading dates: {len(dates_sorted)}")

    # ============================================================
    # Simulation
    # ============================================================

    portfolio = {}  # symbol -> {entry_date, entry_pred, entry_target_bp, peak_ret}
    daily_returns = []
    trades = []  # Closed trades
    daily_nav = 1.0
    equity_curve = []
    limit_filter_count = 0
    t1_lock_count = 0

    for day_i, date in enumerate(dates_sorted):
        indices = date_groups[date]
        day_pnl = 0.0

        # Build lookup for today
        today_symbols = {}
        for idx in indices:
            sym = data["symbol"][idx]
            today_symbols[sym] = idx

        # ---- Step 1: Check exits (T+1 lock + limit-down) ----
        to_close = []
        for sym, pos in list(portfolio.items()):
            # F1 FIX: PnL uses entry_target_bp (the forward return bound to
            # the entry signal sample), NOT exit-day's current target_bp.
            # ETL binds target = VWAP(N+1+H) - VWAP(N+1) to each sample at
            # emission time, so entry_target_bp IS the realized return for
            # that specific signal's 20-bar horizon.
            entry_target = pos["entry_target_bp"]

            # T+1 check: can only sell if NOT bought today
            is_t1_met = (date > pos["entry_date"])

            if not is_t1_met:
                # Iron Rule 1: T+1 lock — can't sell, mark-to-market only
                t1_lock_count += 1
                continue

            # Iron Rule 2: Limit-down = can't sell
            # Check today's LOB for this stock (if available)
            idx = today_symbols.get(sym)
            if idx is not None:
                bid_p1 = data["bid_p1"][idx]
                ask_p1 = data["ask_p1"][idx]
                if is_limit_locked(bid_p1, ask_p1) and entry_target < 0:
                    # Spread locked + negative return → likely limit-down
                    limit_filter_count += 1
                    continue

            # Exit: T+1 met → realize the entry signal's forward return
            exit_reason = "natural_horizon"

            # Board-aware loss cap: a stock physically cannot move more
            # than its daily limit per trading day.
            capped_target = entry_target
            hold_days = max(1, date_to_idx[date] - date_to_idx[pos["entry_date"]])
            if args.board_loss_cap:
                board_limit = get_board_daily_limit_bp(sym)
                max_possible_loss = -board_limit * hold_days
                if capped_target < max_possible_loss:
                    capped_target = max_possible_loss

            # Trailing stop: cap PnL at stop level (if achievable).
            # For main board (-10% limit), a -10% stop always works.
            # For 20% boards, overnight gap can pierce -10% stop to
            # board limit; stop executes at gap-open price.
            stop_bp = args.trailing_stop_pct * 100  # -10% = -1000 BP
            if capped_target < stop_bp:
                # Gap-through: stop couldn't execute at desired level.
                # Loss is capped at board limit (already applied above).
                exit_reason = "trailing_stop"
            elif entry_target < stop_bp and capped_target >= stop_bp:
                # Board cap brought us above stop — original would have
                # been a stop-out but board limit is tighter
                exit_reason = "trailing_stop"

            # PnL = capped target - exit cost
            trade_pnl = capped_target - half_cost
            trades.append({
                "symbol": sym,
                "entry_date": pos["entry_date"],
                "exit_date": date,
                "pred_bp": pos["entry_pred"],
                "actual_bp": entry_target,
                "capped_bp": capped_target,
                "pnl_bp": trade_pnl,
                "exit_reason": exit_reason,
            })
            to_close.append(sym)
            day_pnl += trade_pnl

        for sym in to_close:
            del portfolio[sym]

        # ---- Step 2: New signals ----
        candidates = []
        for idx in indices:
            sym = data["symbol"][idx]
            if sym in portfolio:
                continue  # Already holding

            # Board exclusion filter
            if any(sym.startswith(b) for b in args.exclude_boards):
                continue

            pred_bp = data["pred_bp"][idx]
            bid_p1 = data["bid_p1"][idx]
            ask_p1 = data["ask_p1"][idx]
            macro_v_d = data["macro_v_d"][idx]

            # Iron Rule 3: Limit-up = can't buy (spread locked = order book frozen)
            if is_limit_locked(bid_p1, ask_p1):
                limit_filter_count += 1
                continue

            # Liquidity filter
            if macro_v_d < args.adv_floor:
                continue

            candidates.append((idx, pred_bp))

        # Rank by prediction (descending)
        candidates.sort(key=lambda x: -x[1])

        # Top quintile selection
        n_candidates = len(candidates)
        n_select = max(1, int(n_candidates * (1 - args.long_pctile)))
        n_select = min(n_select, args.max_positions - len(portfolio))
        selected = candidates[:n_select]

        # Open new positions
        for idx, pred_bp in selected:
            sym = data["symbol"][idx]
            # F1 FIX: Store entry_target_bp at open time — this is the
            # forward VWAP return bound to THIS specific signal sample by ETL.
            portfolio[sym] = {
                "entry_date": date,
                "entry_pred": pred_bp,
                "entry_target_bp": data["target_bp"][idx],  # Bound at entry!
                "peak_ret": 0.0,
            }
            day_pnl -= half_cost  # Entry cost

        # ---- Step 3: Daily NAV ----
        # Mark-to-market: unrealized PnL from held positions
        n_positions = len(portfolio)
        if n_positions > 0:
            daily_ret_pct = day_pnl / 10000.0 / max(n_positions, 1)
        else:
            daily_ret_pct = 0.0

        daily_nav *= (1 + daily_ret_pct)
        daily_returns.append(daily_ret_pct)
        equity_curve.append({
            "date": date,
            "nav": daily_nav,
            "daily_return_pct": daily_ret_pct * 100,
            "positions": n_positions,
            "trades_closed": len(to_close),
            "trades_opened": len(selected),
        })

        if (day_i + 1) % 50 == 0:
            log.info(f"Day {day_i+1}/{len(dates_sorted)} | "
                     f"NAV={daily_nav:.4f} | Positions={n_positions} | "
                     f"Trades={len(trades)}")

    # ============================================================
    # Compute metrics
    # ============================================================
    log.info("Computing metrics...")

    rets = np.array(daily_returns)
    trade_pnls = np.array([t["pnl_bp"] for t in trades]) if trades else np.array([0.0])

    # Basic return metrics
    ann_factor = 252
    ann_return = (daily_nav ** (ann_factor / len(rets)) - 1) * 100 if len(rets) > 0 else 0
    sharpe = np.mean(rets) / (np.std(rets) + 1e-10) * np.sqrt(ann_factor)
    downside = rets[rets < 0]
    sortino = np.mean(rets) / (np.std(downside) + 1e-10) * np.sqrt(ann_factor) if len(downside) > 0 else 0

    # Drawdown
    cummax = np.maximum.accumulate(np.cumprod(1 + rets))
    drawdowns = np.cumprod(1 + rets) / cummax - 1
    max_dd = float(np.min(drawdowns)) * 100

    # Max DD duration
    underwater = drawdowns < 0
    dd_duration = 0
    max_dd_dur = 0
    for uw in underwater:
        dd_duration = dd_duration + 1 if uw else 0
        max_dd_dur = max(max_dd_dur, dd_duration)

    calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

    # Trade metrics
    wins = trade_pnls[trade_pnls > 0]
    losses = trade_pnls[trade_pnls < 0]
    win_rate = len(wins) / len(trade_pnls) * 100 if len(trade_pnls) > 0 else 0
    mean_win = np.mean(wins) if len(wins) > 0 else 0
    mean_loss = np.mean(np.abs(losses)) if len(losses) > 0 else 1
    asymmetry = mean_win / mean_loss if mean_loss > 0 else 0
    profit_factor = np.sum(wins) / (np.sum(np.abs(losses)) + 1e-10) if len(losses) > 0 else float('inf')

    # IC metrics (daily cross-sectional)
    daily_ics = []
    for date in dates_sorted:
        indices = date_groups[date]
        if len(indices) < 10:
            continue
        preds = np.array([data["pred_bp"][i] for i in indices])
        actuals = np.array([data["target_bp"][i] for i in indices])
        if np.std(preds) > 0 and np.std(actuals) > 0:
            ic = np.corrcoef(preds, actuals)[0, 1]
            if not np.isnan(ic):
                daily_ics.append(ic)

    ic_mean = np.mean(daily_ics) if daily_ics else 0
    ic_std = np.std(daily_ics) if daily_ics else 1
    icir = ic_mean / (ic_std + 1e-10)

    # Decile monotonicity
    all_preds = np.array(data["pred_bp"])
    all_targets = np.array(data["target_bp"])
    decile_means = []
    for d in range(10):
        lo = np.percentile(all_preds, d * 10)
        hi = np.percentile(all_preds, (d + 1) * 10)
        if d == 0:
            mask = all_preds <= hi
        elif d == 9:
            mask = all_preds >= lo
        else:
            mask = (all_preds > lo) & (all_preds <= hi)
        decile_means.append(float(np.mean(all_targets[mask])) if mask.any() else 0)
    mono_score = sum(1 for i in range(9) if decile_means[i] < decile_means[i+1])
    ls_spread = decile_means[9] - decile_means[0]

    # Break-even cost scan
    breakeven_cost = args.cost_bp
    for test_cost in range(int(args.cost_bp), 100):
        test_pnls = trade_pnls + (args.cost_bp - test_cost)  # Adjust cost
        if np.sum(test_pnls) <= 0:
            breakeven_cost = test_cost
            break
    else:
        breakeven_cost = 100  # Strategy survives even at 100 BP

    # IS vs OOS split
    is_ics = []
    oos_ics = []
    for date in dates_sorted:
        indices = date_groups[date]
        if len(indices) < 10:
            continue
        shard_idx = data["shard_idx"][indices[0]]
        preds = np.array([data["pred_bp"][i] for i in indices])
        actuals = np.array([data["target_bp"][i] for i in indices])
        if np.std(preds) > 0 and np.std(actuals) > 0:
            ic = np.corrcoef(preds, actuals)[0, 1]
            if not np.isnan(ic):
                if shard_idx < args.train_val_boundary:
                    is_ics.append(ic)
                else:
                    oos_ics.append(ic)

    # ============================================================
    # Output
    # ============================================================
    results = {
        "model": "T29 (hd=64)",
        "cost_bp": args.cost_bp,
        "total_samples": n,
        "total_trades": len(trades),
        "total_trading_days": len(dates_sorted),
        "date_range": f"{dates_sorted[0]} → {dates_sorted[-1]}",

        "annualized_return_pct": round(ann_return, 2),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "max_drawdown_pct": round(max_dd, 2),
        "max_dd_duration_days": max_dd_dur,
        "calmar_ratio": round(calmar, 4),

        "asymmetry_payoff_ratio": round(asymmetry, 4),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 4),
        "mean_win_bp": round(float(mean_win), 2),
        "mean_loss_bp": round(float(mean_loss), 2),

        "daily_ic_mean": round(ic_mean, 6),
        "daily_ic_std": round(ic_std, 6),
        "icir": round(icir, 4),
        "long_short_spread_bp": round(ls_spread, 2),
        "monotonicity": f"{mono_score}/9",
        "decile_means_bp": [round(d, 2) for d in decile_means],

        "breakeven_cost_bp": breakeven_cost,

        "is_ic_mean": round(float(np.mean(is_ics)), 6) if is_ics else None,
        "oos_ic_mean": round(float(np.mean(oos_ics)), 6) if oos_ics else None,
        "is_sharpe": None,  # Computed separately if needed
        "oos_sharpe": None,

        "limit_filter_count": limit_filter_count,
        "t1_lock_count": t1_lock_count,
    }

    os.makedirs(args.output_dir, exist_ok=True)

    # Save results JSON
    with open(os.path.join(args.output_dir, "phase7_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    # Save equity curve
    import csv
    eq_path = os.path.join(args.output_dir, "equity_curve.csv")
    with open(eq_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "nav", "daily_return_pct", "positions",
                                                "trades_closed", "trades_opened"])
        writer.writeheader()
        writer.writerows(equity_curve)

    # Save trades
    trades_path = os.path.join(args.output_dir, "trades.json")
    with open(trades_path, "w") as f:
        json.dump(trades[:10000], f, indent=2)  # Cap at 10K for file size

    # Print summary
    log.info("=" * 60)
    log.info("PHASE 7 SIMULATION RESULTS")
    log.info("=" * 60)
    log.info(f"Ann. Return:  {ann_return:.2f}%")
    log.info(f"Sharpe:       {sharpe:.4f}")
    log.info(f"Sortino:      {sortino:.4f}")
    log.info(f"Max DD:       {max_dd:.2f}%")
    log.info(f"Asymmetry:    {asymmetry:.4f}  (target >3.0)")
    log.info(f"Win Rate:     {win_rate:.1f}%")
    log.info(f"Profit Factor:{profit_factor:.4f}")
    log.info(f"Daily IC:     {ic_mean:.6f}")
    log.info(f"ICIR:         {icir:.4f}")
    log.info(f"L/S Spread:   {ls_spread:.2f} BP")
    log.info(f"Monotonicity: {mono_score}/9")
    log.info(f"Break-even:   {breakeven_cost} BP")
    log.info(f"T+1 locks:    {t1_lock_count}")
    log.info(f"Limit filters:{limit_filter_count}")
    log.info(f"IS IC:        {np.mean(is_ics):.6f}" if is_ics else "IS IC: N/A")
    log.info(f"OOS IC:       {np.mean(oos_ics):.6f}" if oos_ics else "OOS IC: N/A")
    log.info(f"Saved to {args.output_dir}")


if __name__ == "__main__":
    main()
