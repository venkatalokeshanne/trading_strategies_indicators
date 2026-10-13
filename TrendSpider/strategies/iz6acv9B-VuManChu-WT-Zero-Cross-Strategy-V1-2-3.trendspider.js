/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VuManChu WT Zero Cross Strategy V1.2.3
 * Author       : as published on TradingView (see Source URL)
 * Source URL   : https://www.tradingview.com/script/iz6acv9B-VuManChu-WT-Zero-Cross-Strategy-V1-2-3
 * Pine version : v6
 * Licence      : not stated
 * Type         : strategy (exact simulation on the chart + signals for the Strategy Tester)
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-13 by Claude (pine-to-trendspider skill, full procedure)
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
 *   - Initial capital and the tick are inputs (1,000,000 and 1 cent by default: TradingView's default capital and a
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

describe_indicator('VuManChu WT Zero Cross Strategy V1.2.3_TV', 'overlay', { shortName: 'VMC WT' });

// ── Inputs (Pine defaults) ───────────────────────────────────────────────
// Whole-number minimums and defaults: the mobile app validates number inputs in whole steps from the minimum,
// so a decimal default or minimum (0.01, min 0.1 with 2) is flagged invalid there (LESSONS L26).
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
const atrMultIn = input.number('ATR Multiplier', 2, { min: 0 });
const fixedPctIn = input.number('Fixed Stop %', 1, { min: 0 });
const capitalIn = input.number('Initial Capital', 1000000, { min: 1 });
const qtyPctIn = input.number('Position % Equity', 2, { min: 0, max: 100 });
const tickCents = input.number('Tick (cents)', 1, { min: 0 });       // 1 = $0.01, a US stock's tick
const tickIn = tickCents / 100;
const showEma = input.boolean('Show EMA', true);
const showArrows = input.boolean('Show Entry Arrows', true);
const showDots = input.boolean('Show TP Dots', true);
const showStop = input.boolean('Show Stop Loss Line', true);
const showPanel = input.boolean('Show Results', true);

// ── The Pine strategy, simulated exactly (tools/parity/iz6acv9B/sim.js, unchanged) ──
function vmcSimulate(O0, H0, L0, C0, P) {
    const n = C0.length;
    // prices on the tick grid, as the broker emulator sees them; the indicators use the raw prices (roundAll: false)
    const tg = P.tick > 0 ? P.tick : 0;
    const onTick = (a) => (tg ? a.map((v) => Math.round(v / tg) * tg) : a);
    const O = onTick(O0), H = onTick(H0), L = onTick(L0), C = onTick(C0);
    const Hi = P.roundAll ? H : H0, Lo = P.roundAll ? L : L0, Cl = P.roundAll ? C : C0;
    const isNa = (v) => v === null || v === undefined || Number.isNaN(v);
    // ---- indicators, Pine semantics ----------------------------------------------------------------------------
    const emaPine = (src, len) => {            // ta.ema: SMA of the first `len` valid values, then alpha smoothing
        const a = 2 / (len + 1), out = [];
        let acc = null, seen = 0, seed = 0;
        for (let i = 0; i < src.length; i++) {
            const v = src[i];
            if (isNa(v)) { out.push(acc); continue; }
            if (acc === null) {
                seed += v; seen++;
                if (seen === len) acc = seed / len;
                out.push(acc);
                continue;
            }
            acc = a * v + (1 - a) * acc;
            out.push(acc);
        }
        return out;
    };
    const smaPine = (src, len) => {            // ta.sma: na until `len` valid values in the window
        const out = [];
        for (let i = 0; i < src.length; i++) {
            if (i < len - 1) { out.push(null); continue; }
            let s = 0, ok = true;
            for (let k = i - len + 1; k <= i; k++) { if (isNa(src[k])) { ok = false; break; } s += src[k]; }
            out.push(ok ? s / len : null);
        }
        return out;
    };
    const rmaPine = (src, len) => {            // ta.rma: SMA-seeded Wilder smoothing
        const out = [];
        let acc = null, seen = 0, seed = 0;
        for (let i = 0; i < src.length; i++) {
            const v = src[i];
            if (isNa(v)) { out.push(acc); continue; }
            if (acc === null) {
                seed += v; seen++;
                if (seen === len) acc = seed / len;
                out.push(acc);
                continue;
            }
            acc = (acc * (len - 1) + v) / len;
            out.push(acc);
        }
        return out;
    };
    const src = [], tr = [];
    for (let i = 0; i < n; i++) {
        src.push(P.src ? P.src[i] : (Hi[i] + Lo[i] + Cl[i]) / 3);             // WT source, hlc3 by default
        tr.push(i === 0 ? Hi[i] - Lo[i] : Math.max(Hi[i] - Lo[i], Math.abs(Hi[i] - Cl[i - 1]), Math.abs(Lo[i] - Cl[i - 1])));
    }
    const esa = emaPine(src, P.chLen);
    const dev = emaPine(src.map((v, i) => (isNa(esa[i]) ? null : Math.abs(v - esa[i]))), P.chLen);
    const ci = src.map((v, i) => (isNa(esa[i]) || isNa(dev[i]) || dev[i] === 0 ? null : (v - esa[i]) / (0.015 * dev[i])));
    const wt1 = emaPine(ci, P.avgLen);
    const wt2 = smaPine(wt1, P.maLen);
    const emaF = emaPine(Cl, P.emaLen);
    const atrV = rmaPine(tr, P.atrLen);

    // ---- swing tracking (var floats starting at 0) -------------------------------------------------------------
    const lowSince = [], highSince = [];
    let lo = 0, hi = 0;
    for (let i = 0; i < n; i++) {
        const w = wt1[i];
        lo = !isNa(w) && w < 0 ? Math.min(lo, w) : 0;
        hi = !isNa(w) && w > 0 ? Math.max(hi, w) : 0;
        lowSince.push(lo); highSince.push(hi);
    }
    const lt = (a, b) => !isNa(a) && !isNa(b) && a < b, gt = (a, b) => !isNa(a) && !isNa(b) && a > b;
    const le = (a, b) => !isNa(a) && !isNa(b) && a <= b, ge = (a, b) => !isNa(a) && !isNa(b) && a >= b;

    // ---- broker + script state ---------------------------------------------------------------------------------
    // fills happen at prices rounded to the symbol's tick (Pine's broker emulator does this)
    const tk = P.tick > 0 ? P.tick : 0;
    const px = (v) => (tk ? Math.round(v / tk) * tk : v);
    const trades = [];                 // closed trades (each partial close is its own trade, as in Pine)
    let posDir = 0, posQty = 0, posEntryPx = 0, posEntryBar = -1, posEntryId = "";
    let realized = 0;
    let inLong = false, inShort = false, tpCount = 0, entryPrice = null, stopLevel = null;
    let restingStop = null;            // the strategy.exit stop order working on this bar (placed on an earlier bar)
    let enteredAt = -1;                // bar of the last strategy.entry fill: that order is still pending while the
                                       // script runs, so a strategy.close on the same bar finds no position to close
    const out = { longEntry: [], shortEntry: [], longTP: [], shortTP: [], exitLong: [], exitShort: [], stop: [], ema: emaF, trades: trades,
                  longSig: [], shortSig: [], longDot: [], shortDot: [], pos: [], realized: [] };

    const closeQty = (qty, px, i, exitId, comment) => {
        if (posDir === 0 || qty <= 0) return;
        const q = Math.min(qty, posQty);
        trades.push({ dir: posDir, entryBar: posEntryBar, exitBar: i, entryPx: posEntryPx, exitPx: px, qty: q,
                      pl: posDir * (px - posEntryPx) * q, entryId: posEntryId, exitId: exitId, comment: comment || "" });
        realized += posDir * (px - posEntryPx) * q;
        posQty -= q;
        if (posQty <= 0) {                     // the position is fully closed: that is a Tester exit
            if (posDir === 1) out.exitLong[i] = true; else out.exitShort[i] = true;
            posDir = 0; posQty = 0; restingStop = null;
        }
    };
    const closeAll = (px, i, exitId, comment) => closeQty(posQty, px, i, exitId, comment);
    const enter = (dir, i) => {        // strategy.entry: reverses an opposite position; ignored when already in `dir`
        if (posDir === dir) return;
        if (posDir === -dir) closeAll(px(C[i]), i, "", "");
        const equity = P.capital + realized;
        const fillPx = px(C[i]);
        if (!(fillPx > 0)) return;                                       // a price that rounds to 0 cannot be sized
        const qty = Math.floor(equity * P.pct / 100 / fillPx + 1e-9);   // tolerance: 201.9999999 is 202
        if (qty <= 0) return;
        posDir = dir; posQty = qty; posEntryPx = fillPx; posEntryBar = i; posEntryId = dir === 1 ? "Long" : "Short";
        if (dir === 1) out.longEntry[i] = true; else out.shortEntry[i] = true;
        enteredAt = i;
    };
    const calcStop = (isLong, ep, i) => {
        const a = atrV[i];
        const atrStop = isNa(a) ? null : (isLong ? ep - a * P.atrMult : ep + a * P.atrMult);
        const fixedStop = isLong ? ep * (1 - P.fixedPct / 100) : ep * (1 + P.fixedPct / 100);
        if (P.slType === "ATR") return atrStop;
        if (P.slType === "Fixed %") return fixedStop;
        if (isNa(atrStop)) return null;
        return isLong ? Math.max(atrStop, fixedStop) : Math.min(atrStop, fixedStop);
    };

    for (let i = 0; i < n; i++) {
        out.longEntry.push(false); out.shortEntry.push(false); out.longTP.push(false); out.shortTP.push(false);
        out.exitLong.push(false); out.exitShort.push(false);
        out.longSig.push(false); out.shortSig.push(false); out.longDot.push(false); out.shortDot.push(false);
        // 1. the resting stop order from earlier bars, intrabar, before the script runs
        if (posDir !== 0 && restingStop !== null) {
            // triggered by the exact stop level; filled at that level rounded to the tick away from the market
            // (a sell stop down, a buy stop up), or at the open when the bar gaps through it
            if (posDir === 1) {
                const sp = tk ? Math.floor(restingStop / tk + 1e-9) * tk : restingStop;
                if (L[i] <= restingStop) closeAll(O[i] <= restingStop ? px(O[i]) : sp, i, "Long SL", "");
            } else if (posDir === -1) {
                const sp = tk ? Math.ceil(restingStop / tk - 1e-9) * tk : restingStop;
                if (H[i] >= restingStop) closeAll(O[i] >= restingStop ? px(O[i]) : sp, i, "Short SL", "");
            }
        }
        // 2. the script, at the bar's close
        if (posDir === 0) { inLong = false; inShort = false; tpCount = 0; stopLevel = null; entryPrice = null; }
        const rawLong = i > 0 && lt(wt1[i - 1], 0) && ge(wt1[i], 0);
        const rawShort = i > 0 && gt(wt1[i - 1], 0) && le(wt1[i], 0);
        const longSignal = rawLong && lowSince[i - 1] <= -P.minSwing;
        const shortSignal = rawShort && highSince[i - 1] >= P.minSwing;
        const d1 = i > 0 && !isNa(wt1[i - 1]) && !isNa(wt2[i - 1]) ? wt1[i - 1] - wt2[i - 1] : null;
        const d0 = !isNa(wt1[i]) && !isNa(wt2[i]) ? wt1[i] - wt2[i] : null;
        const crossUp = lt(d1, 0) && ge(d0, 0), crossDown = gt(d1, 0) && le(d0, 0);
        const buyCircle = crossUp && lt(wt1[i], -60) && lt(wt2[i], -60);
        const sellCircle = crossDown && gt(wt1[i], 60) && gt(wt2[i], 60);
        const longAllowed = !P.trendFilter || gt(C[i], emaF[i]);
        const shortAllowed = !P.trendFilter || lt(C[i], emaF[i]);
        // qty_percent rounds down to whole shares, but never below one share
        // what the Pine script plots: entry arrows on the raw signals (TP dots are set at the end of the bar)
        out.longSig[i] = longSignal; out.shortSig[i] = shortSignal;
        const tpQty = (p) => Math.max(1, Math.floor(posQty * p / 100 + 1e-9));
        const tpPct = () => (tpCount === 0 ? P.tp1 : tpCount === 1 ? P.tp2 : tpCount === 2 ? P.tp3 : tpCount === 3 ? P.tp4 : tpCount === 4 ? P.tp5 : null);

        if (longSignal && longAllowed) {
            if (posDir === -1) closeAll(px(C[i]), i, "", "");
            enter(1, i);
            inLong = true; inShort = false; tpCount = 0; entryPrice = C[i];
            stopLevel = P.enableSL ? calcStop(true, Cl[i], i) : null;
        } else if (shortSignal && shortAllowed) {
            if (posDir === 1) closeAll(px(C[i]), i, "", "");
            enter(-1, i);
            inShort = true; inLong = false; tpCount = 0; entryPrice = C[i];
            stopLevel = P.enableSL ? calcStop(false, Cl[i], i) : null;
        } else if (longSignal && !longAllowed && inShort) {
            if (posDir === -1) closeAll(px(C[i]), i, "", "");
            inShort = false; tpCount = 0; stopLevel = null;
        } else if (shortSignal && !shortAllowed && inLong) {
            if (posDir === 1) closeAll(px(C[i]), i, "", "");
            inLong = false; tpCount = 0; stopLevel = null;
        } else if (inLong && sellCircle) {
            const p = tpPct();
            if (p !== null) { if (posDir === 1) { out.longTP[i] = true; closeQty(tpQty(p), px(C[i]), i, "", ""); } tpCount++; }
        } else if (inShort && buyCircle) {
            const p = tpPct();
            if (p !== null) { if (posDir === -1) { out.shortTP[i] = true; closeQty(tpQty(p), px(C[i]), i, "", ""); } tpCount++; }
        }
        // the script's own "SL Hit" check on the bar's (unrounded) high/low, closing at the close; it catches bars
        // where the working stop order (compared on tick-rounded prices) just missed
        if (P.enableSL && stopLevel !== null) {
            if (inLong && Lo[i] <= stopLevel) { if (posDir === 1 && enteredAt !== i) closeAll(px(C[i]), i, "", "SL Hit"); inLong = false; tpCount = 0; stopLevel = null; }
            if (inShort && stopLevel !== null && Hi[i] >= stopLevel) { if (posDir === -1 && enteredAt !== i) closeAll(px(C[i]), i, "", "SL Hit"); inShort = false; tpCount = 0; stopLevel = null; }
        }
        // strategy.exit: the stop order that works from the next bar
        if (P.enableSL && stopLevel !== null && ((inLong && posDir === 1) || (inShort && posDir === -1))) restingStop = stopLevel;
        out.stop.push(P.enableSL && stopLevel !== null ? stopLevel : null);
        out.longDot[i] = inLong && sellCircle; out.shortDot[i] = inShort && buyCircle;   // state at the bar's end, as plotted
        out.pos.push(posDir * posQty); out.realized.push(realized);
    }
    return out;
}

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
