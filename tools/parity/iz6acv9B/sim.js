// Pine-exact simulation of "VuManChu WT Zero Cross Strategy V1.2.3" (TradingView id iz6acv9B), written in the subset
// of JavaScript TrendSpider's sandbox accepts (no `new`, no classes), so the same function body goes into the
// TrendSpider script. Run standalone in Node by validate.js against Foresight's recorded trades.
//
// Pine semantics reproduced:
//   - ta.ema / ta.sma / ta.atr (RMA of true range, SMA-seeded) and hlc3 source
//   - process_orders_on_close = true: market orders (entries, reversals, TP partial closes, "SL Hit" closes) fill at
//     the bar's close in the order the script issues them
//   - strategy.exit(stop=) is a resting stop order from the bar after it is placed: fills at the open if the bar gaps
//     through it, otherwise at the stop price; it is checked before the script runs on that bar
//   - every fill price rounded to the tick size (mintick)
//   - percent_of_equity 2 %: qty = floor(equity * 2 % / close), equity = capital + closed P&L (+ open P&L)
//   - strategy.close(qty_percent) closes floor(position * pct %) of the open position, at least one share
//   - pyramiding 0: an entry in the direction already held is ignored by the broker, but the script's own state
//     (TP count, entry price, stop level) is still reset, exactly as the Pine code does
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
if (typeof module !== "undefined") module.exports = { vmcSimulate };
