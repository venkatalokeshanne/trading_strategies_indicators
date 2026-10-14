// Pine-exact calculation of "Neural Confluence Engine [Quantum Algo]", written in the subset of JavaScript that
// TrendSpider's sandbox accepts (no `new`, no classes), so build_ts.py pastes this body unchanged into the TrendSpider
// script. check.js runs it in Node against Foresight, which runs the Pine source itself.
//
// Pine semantics reproduced:
//   - ta.ema / ta.sma: na until `len` valid values, the EMA seeded with their SMA
//   - ta.rma (ta.atr, ta.rsi, ta.dmi): SMA-seeded Wilder smoothing; ta.atr = rma(ta.tr(true))
//   - ta.stdev: population (biased) deviation; ta.linreg(x, n, 0): least-squares value at the newest bar
//   - ta.vwap(hlc3): resets at every new session (D.newSession)
//   - comparisons with na are false, math.max / math.min with na give na (v6)
//   - request.security(..., lookahead_off): landHtf() below
function nceCompute(D, P) {
    const n = D.c.length;
    const O = D.o, H = D.h, L = D.l, C = D.c, V = D.v;
    const isNa = (v) => v === null || v === undefined || Number.isNaN(v);
    const gt = (a, b) => !isNa(a) && !isNa(b) && a > b;
    const lt = (a, b) => !isNa(a) && !isNa(b) && a < b;
    const ge = (a, b) => !isNa(a) && !isNa(b) && a >= b;
    const le = (a, b) => !isNa(a) && !isNa(b) && a <= b;
    const pmax = (a, b) => (isNa(a) || isNa(b) ? null : Math.max(a, b));
    const pmin = (a, b) => (isNa(a) || isNa(b) ? null : Math.min(a, b));
    const prev = (x, i) => (i > 0 ? x[i - 1] : null);

    const seeded = (src, len, step) => {      // shared by EMA (step = alpha form) and RMA
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
            acc = step(acc, v);
            out.push(acc);
        }
        return out;
    };
    const emaP = (src, len) => { const a = 2 / (len + 1); return seeded(src, len, (acc, v) => a * v + (1 - a) * acc); };
    const rmaP = (src, len) => seeded(src, len, (acc, v) => (acc * (len - 1) + v) / len);
    const window = (src, len, f) => {         // f(values) over the last `len` bars, na if any is na
        const out = [];
        for (let i = 0; i < src.length; i++) {
            if (i < len - 1) { out.push(null); continue; }
            const w = [];
            let ok = true;
            for (let k = i - len + 1; k <= i; k++) { if (isNa(src[k])) { ok = false; break; } w.push(src[k]); }
            out.push(ok ? f(w) : null);
        }
        return out;
    };
    const smaP = (src, len) => window(src, len, (w) => w.reduce((s, v) => s + v, 0) / len);
    const stdevP = (src, len) => window(src, len, (w) => {
        const m = w.reduce((s, v) => s + v, 0) / len;
        return Math.sqrt(w.reduce((s, v) => s + (v - m) * (v - m), 0) / len);
    });
    const highestP = (src, len) => window(src, len, (w) => Math.max.apply(null, w));
    const lowestP = (src, len) => window(src, len, (w) => Math.min.apply(null, w));
    const linregP = (src, len) => window(src, len, (w) => {   // x = 0 (oldest) … len-1 (newest); value at x = len-1
        let sx = 0, sy = 0, sxx = 0, sxy = 0;
        for (let k = 0; k < len; k++) { sx += k; sy += w[k]; sxx += k * k; sxy += k * w[k]; }
        const slope = (len * sxy - sx * sy) / (len * sxx - sx * sx);
        const intercept = (sy - slope * sx) / len;
        return intercept + slope * (len - 1);
    });
    const trTrue = [], trFalse = [];
    for (let i = 0; i < n; i++) {
        const r = i === 0 ? null : Math.max(H[i] - L[i], Math.abs(H[i] - C[i - 1]), Math.abs(L[i] - C[i - 1]));
        trFalse.push(r);
        trTrue.push(i === 0 ? H[i] - L[i] : r);
    }
    const atrP = (len) => rmaP(trTrue, len);
    const subS = (a, b) => a.map((v, i) => (isNa(v) || isNa(b[i]) ? null : v - b[i]));

    // ── core calculations ──
    const emaFast = emaP(C, P.emaFast), emaSlow = emaP(C, P.emaSlow), emaBase = emaP(C, P.emaBase);
    const ema5 = emaP(C, 5), ema13 = emaP(C, 13), ema34 = emaP(C, 34);
    const src3 = C.map((c, i) => (H[i] + L[i] + c) / 3);
    const vwapVal = [];
    let pv = 0, vv = 0;
    for (let i = 0; i < n; i++) {
        if (i === 0 || D.newSession[i]) { pv = 0; vv = 0; }
        if (!isNa(V[i])) { pv += src3[i] * V[i]; vv += V[i]; }
        vwapVal.push(vv > 0 ? pv / vv : 0);   // no volume yet this session: 0, as Foresight (TradingView) gives
    }
    const atrVal = atrP(P.atrLen);
    // ta.rsi(close, 14): rma of gains and losses; 100 when there are no losses, 0 when there are no gains
    const chg = C.map((c, i) => (i === 0 ? null : c - C[i - 1]));
    const up = rmaP(chg.map((d) => (isNa(d) ? null : Math.max(d, 0))), 14);
    const dn = rmaP(chg.map((d) => (isNa(d) ? null : -Math.min(d, 0))), 14);
    const rsiVal = up.map((u, i) => (isNa(u) || isNa(dn[i]) ? null : dn[i] === 0 ? 100 : u === 0 ? 0 : 100 - 100 / (1 + u / dn[i])));
    const macdLine = subS(emaP(C, 12), emaP(C, 26));
    const signalLine = emaP(macdLine, 9);
    const histLine = subS(macdLine, signalLine);
    // ta.dmi(14, 14), Pine's reference implementation
    const plusDM = [], minusDM = [];
    for (let i = 0; i < n; i++) {
        if (i === 0) { plusDM.push(null); minusDM.push(null); continue; }
        // Pine compares floats with a small tolerance: an up-move and a down-move that are equal in price but differ
        // in the last bits (117.75 - 117.655 vs 117.29 - 117.195) count as equal, so neither is directional
        const u = H[i] - H[i - 1], d = L[i - 1] - L[i], eps = 1e-10 * Math.max(Math.abs(u), Math.abs(d), 1);
        plusDM.push(u - d > eps && u > 0 ? u : 0);
        minusDM.push(d - u > eps && d > 0 ? d : 0);
    }
    const trur = rmaP(trFalse, 14);
    const fixnan = (x) => { let last = null; return x.map((v) => { if (!isNa(v)) last = v; return last; }); };
    const diPlus = fixnan(rmaP(plusDM, 14).map((v, i) => (isNa(v) || isNa(trur[i]) ? null : 100 * v / trur[i])));
    const diMinus = fixnan(rmaP(minusDM, 14).map((v, i) => (isNa(v) || isNa(trur[i]) ? null : 100 * v / trur[i])));
    const adxVal = rmaP(diPlus.map((p, i) => {
        if (isNa(p) || isNa(diMinus[i])) return null;
        const s = p + diMinus[i];
        return Math.abs(p - diMinus[i]) / (s === 0 ? 1 : s);
    }), 14).map((v) => (isNa(v) ? null : 100 * v));
    const volAvg = smaP(V, 20);
    const volRatio = V.map((v, i) => (isNa(volAvg[i]) ? null : v / Math.max(volAvg[i], 1)));

    // WaveTrend
    const wtEsa = emaP(src3, P.wtChannel);
    const wtD = emaP(src3.map((v, i) => (isNa(wtEsa[i]) ? null : Math.abs(v - wtEsa[i]))), P.wtChannel);
    const wtCi = src3.map((v, i) => (isNa(wtEsa[i]) || isNa(wtD[i]) ? null : (v - wtEsa[i]) / (0.015 * wtD[i])));
    const wtTci = emaP(wtCi, P.wtAvg);
    const wtSig = smaP(wtTci, 4);

    // squeeze
    const bbBasis = smaP(C, 20), bbDev = stdevP(C, 20).map((v) => (isNa(v) ? null : 2 * v));
    const atr10 = atrP(10);
    const sqzOn = [], sqzOff = [], sqzFiring = [];
    for (let i = 0; i < n; i++) {
        const bbU = isNa(bbBasis[i]) || isNa(bbDev[i]) ? null : bbBasis[i] + bbDev[i];
        const bbL = isNa(bbBasis[i]) || isNa(bbDev[i]) ? null : bbBasis[i] - bbDev[i];
        const kr = isNa(atr10[i]) ? null : 1.5 * atr10[i];
        const kcU = isNa(bbBasis[i]) || isNa(kr) ? null : bbBasis[i] + kr;
        const kcL = isNa(bbBasis[i]) || isNa(kr) ? null : bbBasis[i] - kr;
        sqzOn.push(gt(bbL, kcL) && lt(bbU, kcU));
        sqzOff.push(lt(bbL, kcL) || gt(bbU, kcU));
        sqzFiring.push(i > 0 && sqzOn[i - 1] && sqzOff[i]);
    }
    // ta.linreg(close - ta.sma((ta.highest(high, 20) + ta.lowest(low, 20)) / 2 + ta.sma(close, 20), 2) / 2, 20, 0)
    const hh = highestP(H, 20), ll = lowestP(L, 20), sma20 = smaP(C, 20);
    const inner = smaP(hh.map((v, i) => (isNa(v) || isNa(ll[i]) || isNa(sma20[i]) ? null : (v + ll[i]) / 2 + sma20[i])), 2);
    const sqzMom = linregP(C.map((c, i) => (isNa(inner[i]) ? null : c - inner[i] / 2)), 20);

    // higher timeframe trend
    const htfBullish = [], htfBearish = [];
    for (let i = 0; i < n; i++) {
        const f = D.htfFast ? D.htfFast[i] : null, s = D.htfSlow ? D.htfSlow[i] : null;
        htfBullish.push(gt(f, s));
        htfBearish.push(lt(f, s));
    }

    // ── directional strength score ──
    const bullRaw = [], bearRaw = [];
    const w1 = 1.5, w2 = 1.3, w3 = 1.0, w4 = 0.8, w5 = 0.8, w6 = 0.7, w7 = 1.0, w8 = 1.2;
    const wTotal = w1 + w2 + w3 + w4 + w5 + w6 + w7 + w8;
    for (let i = 0; i < n; i++) {
        const t = wtTci[i], sg = wtSig[i];
        const fWtBull = gt(t, sg) ? (lt(t, -40) ? 1.0 : gt(t, 0) ? 0.8 : 0.5) : 0.0;
        const fWtBear = lt(t, sg) ? (gt(t, 40) ? 1.0 : lt(t, 0) ? 0.8 : 0.5) : 0.0;
        const fEmaBull = gt(emaFast[i], emaSlow[i]) && gt(emaSlow[i], emaBase[i]) ? 1.0 : gt(emaFast[i], emaSlow[i]) ? 0.6 : 0.0;
        const fEmaBear = lt(emaFast[i], emaSlow[i]) && lt(emaSlow[i], emaBase[i]) ? 1.0 : lt(emaFast[i], emaSlow[i]) ? 0.6 : 0.0;
        const vwPlus = isNa(vwapVal[i]) || isNa(atrVal[i]) ? null : vwapVal[i] + atrVal[i];
        const vwMinus = isNa(vwapVal[i]) || isNa(atrVal[i]) ? null : vwapVal[i] - atrVal[i];
        const fVwapBull = gt(C[i], vwapVal[i]) ? (gt(C[i], vwPlus) ? 1.0 : 0.7) : 0.0;
        const fVwapBear = lt(C[i], vwapVal[i]) ? (lt(C[i], vwMinus) ? 1.0 : 0.7) : 0.0;
        const fRsiBull = gt(rsiVal[i], 50) ? (gt(rsiVal[i], 60) ? 1.0 : 0.6) : 0.0;
        const fRsiBear = lt(rsiVal[i], 50) ? (lt(rsiVal[i], 40) ? 1.0 : 0.6) : 0.0;
        const fMacdBull = gt(histLine[i], 0) ? (gt(histLine[i], prev(histLine, i)) ? 1.0 : 0.6) : 0.0;
        const fMacdBear = lt(histLine[i], 0) ? (lt(histLine[i], prev(histLine, i)) ? 1.0 : 0.6) : 0.0;
        const fAdx = gt(adxVal[i], 25) ? (gt(adxVal[i], 40) ? 1.0 : 0.7) : 0.3;
        const va8 = isNa(volAvg[i]) ? null : volAvg[i] * 0.8;
        const fVolBull = gt(V[i], volAvg[i]) && C[i] > O[i] ? 1.0 : gt(V[i], va8) ? 0.4 : 0.0;
        const fVolBear = gt(V[i], volAvg[i]) && C[i] < O[i] ? 1.0 : gt(V[i], va8) ? 0.4 : 0.0;
        const fSqzBull = sqzFiring[i] && gt(sqzMom[i], 0) ? 1.0 : sqzOn[i] ? 0.3 : 0.0;
        const fSqzBear = sqzFiring[i] && lt(sqzMom[i], 0) ? 1.0 : sqzOn[i] ? 0.3 : 0.0;
        bullRaw.push((fWtBull * w1 + fEmaBull * w2 + fVwapBull * w3 + fRsiBull * w4 + fMacdBull * w5 + fAdx * w6 + fVolBull * w7 + fSqzBull * w8) / wTotal * 100);
        bearRaw.push((fWtBear * w1 + fEmaBear * w2 + fVwapBear * w3 + fRsiBear * w4 + fMacdBear * w5 + fAdx * w6 + fVolBear * w7 + fSqzBear * w8) / wTotal * 100);
    }
    const bullScore = emaP(bullRaw, 3), bearScore = emaP(bearRaw, 3);
    const nce = subS(bullScore, bearScore);

    // ── signals ──
    const ribbonBull = [], ribbonBear = [], flipBull = [], flipBear = [], buyPlus = [], sellPlus = [];
    for (let i = 0; i < n; i++) {
        ribbonBull.push(gt(emaFast[i], emaSlow[i]));
        ribbonBear.push(lt(emaFast[i], emaSlow[i]));
        flipBull.push(ribbonBull[i] && i > 0 && ribbonBear[i - 1]);
        flipBear.push(ribbonBear[i] && i > 0 && ribbonBull[i - 1]);
        // ta.crossover / ta.crossunder
        const crossUp = i > 0 && gt(emaFast[i], emaSlow[i]) && le(emaFast[i - 1], emaSlow[i - 1]);
        const crossDn = i > 0 && lt(emaFast[i], emaSlow[i]) && ge(emaFast[i - 1], emaSlow[i - 1]);
        buyPlus.push(crossUp && ge(bullScore[i], P.threshold) && (P.htfFilter ? htfBullish[i] : true));
        sellPlus.push(crossDn && ge(bearScore[i], P.threshold) && (P.htfFilter ? htfBearish[i] : true));
    }

    // ── trade management (the script's own tracker; it places no orders) ──
    let tradeDir = 0, entryPrice = 0, slPrice = 0, tp1 = 0, tp2 = 0, tp3 = 0;
    let tp1Hit = false, tp2Hit = false, tp3Hit = false, slHit = false, trailSL = 0, entryBar = 0;
    const T = { dir: [], entry: [], sl: [], tp1: [], tp2: [], tp3: [], trail: [], tp1Hit: [], tp2Hit: [], tp3Hit: [], slHit: [], entryBar: [] };
    for (let i = 0; i < n; i++) {
        const startTrade = (dir) => {
            tradeDir = dir;
            entryPrice = C[i];
            const risk = isNa(atrVal[i]) ? null : atrVal[i] * P.slMult;
            const at = (k) => (isNa(risk) ? null : entryPrice + dir * risk * k);
            slPrice = isNa(risk) ? null : entryPrice - dir * risk;
            tp1 = at(P.tp1Mult); tp2 = at(P.tp2Mult); tp3 = at(P.tp3Mult);
            tp1Hit = false; tp2Hit = false; tp3Hit = false; slHit = false;
            trailSL = slPrice;
            entryBar = i;
        };
        if (flipBull[i] || buyPlus[i]) startTrade(1);
        if (flipBear[i] || sellPlus[i]) startTrade(-1);
        if (tradeDir === 1 && !slHit) {
            if (ge(H[i], tp1)) { tp1Hit = true; if (P.trail) trailSL = pmax(trailSL, entryPrice); }
            if (ge(H[i], tp2)) { tp2Hit = true; if (P.trail) trailSL = pmax(trailSL, tp1); }
            if (ge(H[i], tp3)) { tp3Hit = true; if (P.trail) trailSL = pmax(trailSL, tp2); }
            if (tp1Hit && P.trail) trailSL = pmax(trailSL, isNa(atrVal[i]) ? null : L[i] - atrVal[i] * 0.5);
            if (le(L[i], trailSL)) slHit = true;
        }
        if (tradeDir === -1 && !slHit) {
            if (le(L[i], tp1)) { tp1Hit = true; if (P.trail) trailSL = pmin(trailSL, entryPrice); }
            if (le(L[i], tp2)) { tp2Hit = true; if (P.trail) trailSL = pmin(trailSL, tp1); }
            if (le(L[i], tp3)) { tp3Hit = true; if (P.trail) trailSL = pmin(trailSL, tp2); }
            if (tp1Hit && P.trail) trailSL = pmin(trailSL, isNa(atrVal[i]) ? null : H[i] + atrVal[i] * 0.5);
            if (ge(H[i], trailSL)) slHit = true;
        }
        T.dir.push(tradeDir); T.entry.push(entryPrice); T.sl.push(slPrice); T.tp1.push(tp1); T.tp2.push(tp2); T.tp3.push(tp3);
        T.trail.push(trailSL); T.tp1Hit.push(tp1Hit); T.tp2Hit.push(tp2Hit); T.tp3Hit.push(tp3Hit); T.slHit.push(slHit);
        T.entryBar.push(entryBar);
    }

    return {
        emaFast, emaSlow, emaBase, ema5, ema13, ema34, vwapVal, atrVal, rsiVal, histLine, adxVal, volRatio, wtTci, wtSig,
        sqzOn, sqzFiring, sqzMom, htfBullish, bullScore, bearScore, nce, ribbonBull, flipBull, flipBear, buyPlus, sellPlus,
        trade: T,
    };
}

// ta.ema on an array of numbers (used for the higher-timeframe EMAs): SMA-seeded, as nceCompute's emaP
function nceEma(src, len) {
    const a = 2 / (len + 1), out = [];
    let acc = null, seen = 0, seed = 0;
    for (let i = 0; i < src.length; i++) {
        const v = src[i];
        if (v === null || v === undefined || Number.isNaN(v)) { out.push(acc); continue; }
        if (acc === null) { seed += v; seen++; if (seen === len) acc = seed / len; out.push(acc); continue; }
        acc = a * v + (1 - a) * acc;
        out.push(acc);
    }
    return out;
}

// request.security(sym, tf, expr, lookahead = barmerge.lookahead_off) on historical bars: a chart bar sees the value
// of the higher-timeframe bar it belongs to only on that bar's LAST chart bar (when the HTF bar closes); before that,
// the previous HTF bar's value. The chart's newest bar sees the forming HTF bar, as Pine's realtime bar does.
// chartTime and htfTime are bar-open times in the same unit; htfVals is computed on the HTF bars.
function landHtf(chartTime, htfTime, htfVals) {
    const out = [], idx = [];
    let k = -1;
    for (let i = 0; i < chartTime.length; i++) {
        while (k + 1 < htfTime.length && htfTime[k + 1] <= chartTime[i]) k++;
        idx.push(k);
    }
    for (let i = 0; i < chartTime.length; i++) {
        const k0 = idx[i];
        if (k0 < 0) { out.push(null); continue; }
        const last = i === chartTime.length - 1 || idx[i + 1] !== k0;
        const v = last ? htfVals[k0] : (k0 > 0 ? htfVals[k0 - 1] : null);
        out.push(v === undefined ? null : v);
    }
    return out;
}

if (typeof module !== "undefined") module.exports = { nceCompute, landHtf, nceEma };
