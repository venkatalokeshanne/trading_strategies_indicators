"""Builds the TrendSpider script from the validated simulation (sim.js), so the code that matched Foresight trade for
trade is exactly the code that runs in TrendSpider. Output: TrendSpider/strategies/iz6acv9B-...trendspider.js"""
import re
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parents[2]
OUT = REPO / "TrendSpider" / "strategies" / "iz6acv9B-VuManChu-WT-Zero-Cross-Strategy-V1-2-3.trendspider.js"

sim = (HERE / "sim.js").read_text(encoding="utf-8")
body = sim[sim.index("function vmcSimulate"):sim.index('if (typeof module !== "undefined")')].rstrip()

HEADER = f"""/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VuManChu WT Zero Cross Strategy V1.2.3
 * Author       : as published on TradingView (see Source URL)
 * Source URL   : https://www.tradingview.com/script/iz6acv9B-VuManChu-WT-Zero-Cross-Strategy-V1-2-3
 * Pine version : v6
 * Licence      : not stated
 * Type         : strategy (exact simulation on the chart + signals for the Strategy Tester)
 * Placement    : overlay
 * Status       : FULL
 * Converted    : {date.today().isoformat()} by Claude (pine-to-trendspider skill, full procedure)
 * TrendSpider name : VuManChu WT Zero Cross Strategy V1.2.3_TV
 * Live tested  : 2026-10-13 on INFQ 15m — saved in TrendSpider: yes; Strategy Tester (Long only, 10,000 candles): 112 positions
 *
 * How it works:
 *   The script re-runs the Pine strategy's own order logic bar by bar (process_orders_on_close fills at the close,
 *   the 50 % take-profit ladder, the ATR stop order that fills inside the bar, long/short reversals, 2 % of equity
 *   sizing, fills rounded to the tick) and shows its trades and results on the chart. Checked trade for trade
 *   against Foresight (which runs the Pine script unchanged): 352 stock x timeframe sets, 209,186 trades, all
 *   identical (tools/parity/iz6acv9B: sim.js, compare.py, sweep.py).
 *
 * Deviations from the original:
 *   - Results panel and markers: exact. They use TrendSpider's own price data, so on a symbol whose data differs
 *     from TradingView's (adjustments, extended hours) the trades differ by that data, not by the logic.
 *   - Initial capital and tick size are inputs (1,000,000 and 0.01 by default: TradingView's default capital and a
 *     US stock's tick); TrendSpider exposes neither.
 *   - Max drawdown in the panel is on closed trades (TradingView's also includes open-trade swings).
 *   - The Pine "SL Hit" alerts test the stop after the script has already cleared it, so on TradingView they never
 *     fire; here "VMC Long Stop" / "VMC Short Stop" fire when a stop actually closes the position.
 *
 * Not carried over:
 *   - none of the logic. The Strategy Tester itself cannot run this exactly (below).
 *
 * Strategy Tester settings (set these by hand in TrendSpider) — close to, not identical with, the original:
 *   Strategy 1 — Direction: Long only
 *     Entry : "VMC Long Entry"  -> Signal emerged
 *     Exit  : Script -> "VMC Long Exit" -> Signal emerged
 *   Strategy 2 — Direction: Short only
 *     Entry : "VMC Short Entry" -> Signal emerged
 *     Exit  : Script -> "VMC Short Exit" -> Signal emerged
 *   Sizing : 2 % of equity.  Commission / slippage: none (the Pine script sets none).
 *   Backtest length: raise from the 300-candle default to the maximum.
 *   Why only close: the Tester fills at the NEXT bar's open (Pine: this bar's close), holds whole positions (Pine:
 *   50 % take-profits, up to five), and stop exits come as signals filled at the next open (Pine: inside the bar).
 *   The exact figures are in the script's results panel on the chart.
 * ───────────────────────────────────────────────────────────────────────
 */
"""

MAIN = r"""
describe_indicator('VuManChu WT Zero Cross Strategy V1.2.3_TV', 'overlay', { shortName: 'VMC WT' });

// ── Inputs (Pine defaults) ───────────────────────────────────────────────
const wtChLen = input.number('WT Channel Length', 9, { min: 1 });
const wtAvgLen = input.number('WT Average Length', 27, { min: 1 });
const wtMaLen = input.number('WT MA Length', 3, { min: 1 });
const wtSrcName = input.select('WT Source', 'hlc3', ['open', 'high', 'low', 'close', 'hl2', 'hlc3', 'ohlc4']);
const minSwingIn = input.number('Min Swing', 10, { min: 1 });
const trendOn = input.boolean('Trend Filter', false);
const emaLenIn = input.number('EMA Length', 200, { min: 1 });
const tp1In = input.number('TP1 %', 50, { min: 1, max: 100 });
const tp2In = input.number('TP2 %', 50, { min: 1, max: 100 });
const tp3In = input.number('TP3 %', 50, { min: 1, max: 100 });
const tp4In = input.number('TP4 %', 50, { min: 1, max: 100 });
const tp5In = input.number('TP5 %', 50, { min: 1, max: 100 });
const slOn = input.boolean('Stop Loss', true);
const slTypeIn = input.select('Stop Loss Type', 'ATR', ['ATR', 'Fixed %', 'Both']);
const atrLenIn = input.number('ATR Length', 14, { min: 1 });
const atrMultIn = input.number('ATR Multiplier', 2, { min: 0.1 });
const fixedPctIn = input.number('Fixed Stop %', 1, { min: 0.01 });
const capitalIn = input.number('Initial Capital', 1000000, { min: 1 });
const qtyPctIn = input.number('Position % Equity', 2, { min: 0.01, max: 100 });
const tickIn = input.number('Tick Size', 0.01, { min: 0 });
const showEma = input.boolean('Show EMA', true);
const showArrows = input.boolean('Show Entry Arrows', true);
const showDots = input.boolean('Show TP Dots', true);
const showStop = input.boolean('Show Stop Loss Line', true);
const showPanel = input.boolean('Show Results', true);

// ── The Pine strategy, simulated exactly (tools/parity/iz6acv9B/sim.js, unchanged) ──
__SIM__

const wtSrc = wtSrcName === 'hlc3' ? null : market[wtSrcName];
const res = vmcSimulate(open, high, low, close, {
    chLen: wtChLen, avgLen: wtAvgLen, maLen: wtMaLen, minSwing: minSwingIn, trendFilter: trendOn, emaLen: emaLenIn,
    tp1: tp1In, tp2: tp2In, tp3: tp3In, tp4: tp4In, tp5: tp5In, enableSL: slOn, slType: slTypeIn,
    atrLen: atrLenIn, atrMult: atrMultIn, fixedPct: fixedPctIn, capital: capitalIn, pct: qtyPctIn, tick: tickIn,
    roundAll: false, src: wtSrc
});

// ── Paints — unconditional, literal names (none equal to a signal name) ──
paint(res.ema.map((v) => (showEma ? v : null)), { name: 'EMA Filter', color: '#FFEB3B', thickness: 2 });
paint(res.stop.map((v) => (showStop ? v : null)), { name: 'Stop Loss', color: '#F23645', thickness: 1 });
paint(res.longSig.map((s, i) => (showArrows && s ? low[i] : null)), { name: 'Long Entry', color: '#089981', style: 'dotted', marker: 'triangle' });
paint(res.shortSig.map((s, i) => (showArrows && s ? high[i] : null)), { name: 'Short Entry', color: '#F23645', style: 'dotted', marker: 'triangle-down' });
paint(res.longDot.map((s, i) => (showDots && s ? high[i] : null)), { name: 'Long TP', color: '#F23645', style: 'dotted', marker: 'circle' });
paint(res.shortDot.map((s, i) => (showDots && s ? low[i] : null)), { name: 'Short TP', color: '#089981', style: 'dotted', marker: 'circle' });

// ── Results of the exact simulation ──────────────────────────────────────
const closed = res.trades;
let grossWin = 0, grossLoss = 0, wins = 0, eqv = capitalIn, peak = capitalIn, maxDd = 0;
for (let k = 0; k < closed.length; k++) {
    const p = closed[k].pl;
    if (p > 0) { grossWin += p; wins++; } else grossLoss -= p;
    eqv += p; peak = Math.max(peak, eqv); maxDd = Math.max(maxDd, peak - eqv);
}
const lastI = close.length - 1;
const netPl = closed.length ? res.realized[lastI] : 0;
const posNow = res.pos[lastI] || 0;
const money = (v) => (v < 0 ? '-' : '') + Math.abs(v).toFixed(2);
// overlay table in the format TrendSpider's own store scripts use: cell text / color / padding / fontWeight, table
// background / fontSize / width, order 'above_all' (drawn over the chart rather than beneath it)
const rowOf = (a, b) => ({ cells: [{ text: a, color: '#B2B5BE', padding: '2px 8px' }, { text: b, color: '#FFFFFF', padding: '2px 8px', textAlign: 'right' }] });
paint_overlay('VMC WT Results', { position: 'top_left', offset_x: 10, offset_y: 40, order: 'above_all' }, {
    fontSize: 12, width: '320px', background: 'rgba(19, 23, 34, 0.85)', border: '1px solid #2A2E39',
    rows: showPanel ? [
        { cells: [{ text: 'VuManChu WT Zero Cross V1.2.3', color: '#FFFFFF', fontWeight: 'bold', padding: '4px 8px' }, { text: 'Pine-exact', color: '#B2B5BE', padding: '4px 8px', textAlign: 'right' }] },
        rowOf('Net profit', money(netPl) + ' (' + (100 * netPl / capitalIn).toFixed(2) + '%)'),
        rowOf('Closed trades', String(closed.length)),
        rowOf('Win rate', closed.length ? (100 * wins / closed.length).toFixed(2) + '%' : '-'),
        rowOf('Profit factor', grossLoss > 0 ? (grossWin / grossLoss).toFixed(3) : '-'),
        rowOf('Max drawdown (closed)', money(maxDd) + ' (' + (100 * maxDd / capitalIn).toFixed(2) + '%)'),
        rowOf('Open position', posNow > 0 ? 'Long ' + posNow : posNow < 0 ? 'Short ' + (-posNow) : 'Flat')
    ] : []
});

// ── Signals — single-bar pulses; Tester uses "Signal emerged" ────────────
const stopOut = (dir) => close.map(() => false).map((_x, i) => closed.some((t) => t.exitBar === i && t.dir === dir && (t.exitId !== '' || t.comment === 'SL Hit')));
register_signal(res.longEntry, 'VMC Long Entry');
register_signal(res.exitLong, 'VMC Long Exit');
register_signal(res.shortEntry, 'VMC Short Entry');
register_signal(res.exitShort, 'VMC Short Exit');
register_signal(res.longSig, 'VMC Long Signal');
register_signal(res.shortSig, 'VMC Short Signal');
register_signal(res.longTP, 'VMC Long Take Profit');
register_signal(res.shortTP, 'VMC Short Take Profit');
register_signal(stopOut(1), 'VMC Long Stop');
register_signal(stopOut(-1), 'VMC Short Stop');
"""

text = HEADER + MAIN.replace("__SIM__", body)
OUT.write_text(text, encoding="utf-8")
print("wrote", OUT, len(text.splitlines()), "lines")
