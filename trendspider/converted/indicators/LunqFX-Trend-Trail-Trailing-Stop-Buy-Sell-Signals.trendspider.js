/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Trend Trail, Trailing Stop & Buy Sell Signals [LunqFX]
 * Author       : LunqFX
 * Source URL   : supplied by the user (TradingView script by LunqFX)
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-10 by Claude (pine-to-trendspider skill), by hand
 * TrendSpider name : Trend Trail, Trailing Stop & Buy Sell Signals [LunqFX]_TV
 * Live tested  : 2026-10-10 on INFQ 5m — APPLY clean, saved in TrendSpider: yes.
 *
 * The Pine original, in words: an ATR trailing stop that only exists while a trend regime
 * is "armed". The regime uses the Kaufman Efficiency Ratio, ranked against its own last 200
 * values (percentile); it arms above the 65th percentile (two bars in a row), disarms 15
 * points lower, and must hold at least 15 bars. While dormant there is no trail and no
 * signal. The trail distance widens in chop (1 + (1 - ER) x 0.6). BUY/SELL print when the
 * trail takes a side; a plain fixed-distance trail runs alongside and the panel compares
 * its flip count with the signals actually given.
 *
 * Every Pine rule is reproduced bar for bar in one loop: ta.atr = Wilder RMA of the true
 * range (SMA-seeded), ta.percentrank = share of the previous N values <= the current one,
 * math.sum, the var state of the regime (armed / last switch bar) and the nz() fallbacks.
 * Non-repainting, as in the Pine: everything is built from closed-bar values.
 *
 * Deviations from the original: glow, fill and candle colours use TrendSpider's rgba colours
 * (same hues and opacities); the dashboard is a TrendSpider overlay table (no cell
 * background colours); "Middle Right" dashboard position is not offered.
 * Not carried over: alertcondition() — use the signals (Buy signal, Sell signal, Any signal,
 * Regime opened, Regime closed) in TrendSpider alerts and scanners.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Trend Trail, Trailing Stop & Buy Sell Signals [LunqFX]_TV', 'price');

// ── Palette (Pine colours; rgba for the transparent ones)
const UP = '#00F5D4', DN = '#FF2E88', SLEEP = '#6B7688', SLEEP_D = '#414C5C';
const myRgba = (_hex, _alpha) => {
    const r = parseInt(_hex.slice(1, 3), 16), g = parseInt(_hex.slice(3, 5), 16), b = parseInt(_hex.slice(5, 7), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + _alpha + ')';
};

// ── Inputs
const tT = input.tab('Trail');
const myAtrLen = tT.number('ATR length', 14, { min: 2, max: 100 });
const myBaseMlt = tT.number('Trail distance (ATR)', 2.6, { min: 0.5, max: 10, step: 0.1 });
const myAdaptOn = tT.boolean('Adapt distance to conditions', true);
const myAdaptAmt = tT.number('Adaptation strength', 0.6, { min: 0, max: 1.5, step: 0.05 });
const tR = input.tab('Regime Filter');
const myRegimeOn = tR.boolean('Only trade when a trend exists', true);
const myErLen = tR.number('Efficiency lookback', 20, { min: 5, max: 200 });
const myRankLook = tR.number('Self-calibration window', 200, { min: 50, max: 1000 });
const myRankMin = tR.number('Arms above percentile', 65, { min: 30, max: 95 });
const myHyst = tR.number('Hysteresis', 15, { min: 0, max: 40 });
const myDwell = tR.number('Minimum bars per regime', 15, { min: 1, max: 200 });
const tS = input.tab('Signals');
const mySigOn = tS.boolean('Buy and sell signals', true);
const mySigLbl = tS.boolean('Labels instead of arrows', true);
const mySigStop = tS.boolean('Show stop level on label', true);
const tV = input.tab('Visuals');
const myGlowOn = tV.boolean('Glow', true);
const myFillOn = tV.boolean('Fill to price', true);
const myCandOn = tV.boolean('Dim candles when dormant', true);
const myShowHud = tV.boolean('Dashboard', true);
const myHudPos = tV.select('Dashboard position', 'Top Right', ['Top Right', 'Top Left', 'Bottom Right', 'Bottom Left']);

const myN = close.length;
const myFmt = _v => (_v === null || !isFinite(_v)) ? '—' : (Math.abs(_v) >= 10 ? _v.toFixed(2) : _v.toFixed(4));

// ── ATR(atrLen): Wilder RMA of the true range, SMA-seeded (Pine ta.atr / ta.tr(true))
const myAtr = series_of(null);
{
    let trSum = 0, prev = null;
    for (let i = 0; i < myN; i++) {
        const tr = i === 0 ? high[i] - low[i]
            : Math.max(high[i] - low[i], Math.abs(high[i] - close[i - 1]), Math.abs(low[i] - close[i - 1]));
        if (prev === null) {
            trSum += tr;
            if (i === myAtrLen - 1) { prev = trSum / myAtrLen; myAtr[i] = prev; }
        } else {
            prev = (prev * (myAtrLen - 1) + tr) / myAtrLen;
            myAtr[i] = prev;
        }
    }
}

// ── Kaufman Efficiency Ratio: |close - close[erLen]| / sum(|close - close[1]|, erLen); 0 if path is 0/na
const myEr = series_of(0);
{
    let path = 0;
    for (let i = 1; i < myN; i++) {
        path += Math.abs(close[i] - close[i - 1]);
        if (i > myErLen) path -= Math.abs(close[i - myErLen] - close[i - myErLen - 1]);
        if (i >= myErLen) myEr[i] = path > 0 ? Math.abs(close[i] - close[i - myErLen]) / path : 0;
    }
}

// ── ta.percentrank(er, rankLook): % of the previous rankLook values <= the current one
const myRank = series_of(null);
for (let i = myRankLook; i < myN; i++) {
    let cnt = 0;
    for (let k = 1; k <= myRankLook; k++) if (myEr[i] >= myEr[i - k]) cnt++;
    myRank[i] = cnt * 100 / myRankLook;
}

// ── Regime with hysteresis + minimum dwell, then the trail (torn down while dormant)
const myTrending = series_of(false), myRegOpen = series_of(false), myRegClose = series_of(false);
const myDir = series_of(0), myUpB = series_of(null), myDnB = series_of(null), myTrail = series_of(null);
const myBuy = series_of(false), mySell = series_of(false);
let armed = false, swBar = 0, wasTrend = false;
let pUpPrev = null, pDnPrev = null, pDirPrev = null, plainFlips = 0, taken = 0;
for (let i = 0; i < myN; i++) {
    // regime
    const canSwitch = i - swBar >= myDwell;
    const r = myRank[i], rPrev = i > 0 && myRank[i - 1] !== null ? myRank[i - 1] : 0;
    if (r !== null) {
        if (!armed && canSwitch && r >= myRankMin && rPrev >= myRankMin) { armed = true; swBar = i; }
        else if (armed && canSwitch && r < myRankMin - myHyst) { armed = false; swBar = i; }
    }
    const trending = !myRegimeOn || armed;
    myTrending[i] = trending;
    myRegOpen[i] = i > 0 && trending && !wasTrend;
    myRegClose[i] = i > 0 && !trending && wasTrend;
    wasTrend = trending;

    // adaptive trail
    const a = myAtr[i], mid = (high[i] + low[i]) / 2;
    const m = myAdaptOn ? myBaseMlt * (1 + (1 - myEr[i]) * myAdaptAmt) : myBaseMlt;
    const rawUp = a === null ? null : mid - m * a, rawDn = a === null ? null : mid + m * a;
    const prevDir = i > 0 ? myDir[i - 1] : 0;
    let dir, upB, dnB;
    if (!trending) { dir = 0; upB = null; dnB = null; }
    else if (prevDir === 0) {
        dir = (i >= myErLen && close[i] >= close[i - myErLen]) ? 1 : -1;
        upB = rawUp; dnB = rawDn;
    } else {
        const pu = i > 0 && myUpB[i - 1] !== null ? myUpB[i - 1] : rawUp;   // nz(upB[1], rawUp)
        const pd = i > 0 && myDnB[i - 1] !== null ? myDnB[i - 1] : rawDn;   // nz(dnB[1], rawDn)
        upB = rawUp === null ? null : (pu !== null && close[i - 1] > pu ? Math.max(rawUp, pu) : rawUp);
        dnB = rawDn === null ? null : (pd !== null && close[i - 1] < pd ? Math.min(rawDn, pd) : rawDn);
        dir = (pd !== null && close[i] > pd) ? 1 : (pu !== null && close[i] < pu) ? -1 : prevDir;
    }
    myDir[i] = dir; myUpB[i] = upB; myDnB[i] = dnB;
    myTrail[i] = dir === 1 ? upB : dir === -1 ? dnB : null;
    myBuy[i] = mySigOn && dir === 1 && prevDir !== 1;
    mySell[i] = mySigOn && dir === -1 && prevDir !== -1;
    if (myBuy[i] || mySell[i]) taken++;

    // plain fixed-distance trail (control group, no regime filter)
    const pRawUp = a === null ? null : mid - myBaseMlt * a, pRawDn = a === null ? null : mid + myBaseMlt * a;
    const ppu = pUpPrev !== null ? pUpPrev : pRawUp, ppd = pDnPrev !== null ? pDnPrev : pRawDn;
    const pUp = pRawUp === null ? null : (i > 0 && ppu !== null && close[i - 1] > ppu ? Math.max(pRawUp, ppu) : pRawUp);
    const pDn = pRawDn === null ? null : (i > 0 && ppd !== null && close[i - 1] < ppd ? Math.min(pRawDn, ppd) : pRawDn);
    const pDir = (ppd !== null && close[i] > ppd) ? 1 : (ppu !== null && close[i] < ppu) ? -1 : (pDirPrev === null ? 1 : pDirPrev);
    if (pDirPrev !== null && pDir !== pDirPrev) plainFlips++;
    pUpPrev = pUp; pDnPrev = pDn; pDirPrev = pDir;
}

// ── Drawing: glow (three wide translucent lines), the trail, fill to price, candles
const myCol = myDir.map(d => d === 1 ? UP : d === -1 ? DN : SLEEP);
const myGlow = myGlowOn ? myTrail : series_of(null);
paint(myGlow, { name: 'Glow outer', color: myCol.map(c => myRgba(c, 0.10)), thickness: 7 });
paint(myGlow, { name: 'Glow mid', color: myCol.map(c => myRgba(c, 0.24)), thickness: 5 });
paint(myGlow, { name: 'Glow inner', color: myCol.map(c => myRgba(c, 0.48)), thickness: 3 });
paint(myTrail, { name: 'Trail', color: myCol, thickness: 2 });
const myPriceLive = for_every(close, myDir, (c, d) => myFillOn && d !== 0 ? c : null);
color_cloud(myPriceLive, myTrail, myRgba(UP, 0.12), myRgba(DN, 0.12), 'Fill long', 'Fill short');

const myCandle = for_every(open, close, myTrending, (o, c, t) => {
    if (!myCandOn) return null;
    const up = c >= o;
    return t ? myRgba(up ? UP : DN, 0.78) : myRgba(up ? SLEEP : SLEEP_D, 0.70);
});
color_candles(myCandle);

// ── Signal marks: labels with the stop level, or arrows
const myBuyLbl = for_every(myBuy, myTrail, (b, t) => !b ? null
    : (mySigLbl ? '▲ BUY' + (mySigStop ? '  ' + myFmt(t) : '') : constants.icons.triangle_up));
const mySellLbl = for_every(mySell, myTrail, (s, t) => !s ? null
    : (mySigLbl ? '▼ SELL' + (mySigStop ? '  ' + myFmt(t) : '') : constants.icons.triangle_down));
paint(myBuyLbl, { name: 'Buy', style: 'labels_below', color: UP });
paint(mySellLbl, { name: 'Sell', style: 'labels_above', color: DN });

// ── Dashboard (last bar)
const L = myN - 1;
const myPosMap = { 'Top Right': 'top_right', 'Top Left': 'top_left', 'Bottom Right': 'bottom_right', 'Bottom Left': 'bottom_left' };
const dirL = myDir[L], trendL = myTrending[L], trailL = myTrail[L];
const rk = myRank[L] === null ? 0 : myRank[L];
const meterN = Math.round(Math.min(Math.max(rk / 100, 0), 1) * 10);
const meter = '█'.repeat(meterN) + '░'.repeat(10 - meterN);
const dist = Math.abs(close[L] - (trailL === null ? close[L] : trailL));
const distA = myAtr[L] ? dist / myAtr[L] : 0;
const cut = plainFlips > 0 ? (plainFlips - taken) / plainFlips * 100 : 0;
const cutTx = (cut > 0.5 ? '−' : cut < -0.5 ? '+' : '') + Math.abs(cut).toFixed(0) + '%';
const stateCol = !trendL ? SLEEP : dirL === 1 ? UP : DN;
paint_overlay('Trend Trail panel', { position: myPosMap[myHudPos] }, {
    rows: myShowHud ? [
        { cells: [{ text: !trendL ? '◍ DORMANT · no trend to trail' : dirL === 1 ? '▲ TRAILING LONG' : '▼ TRAILING SHORT', color: stateCol },
                  { text: dirL === 0 ? '—' : myFmt(trailL), color: stateCol }] },
        { cells: [{ text: 'Trend strength', color: '#94A3B8' }, { text: String(Math.floor(rk)), color: trendL ? '#F1F5F9' : SLEEP }] },
        { cells: [{ text: meter, color: trendL ? (dirL === 1 ? UP : DN) : SLEEP }, { text: 'arms at ' + myRankMin, color: '#94A3B8' }] },
        { cells: [{ text: 'Stop distance', color: '#94A3B8' },
                  { text: dirL === 0 ? 'no stop — dormant' : myFmt(dist) + '  (' + distA.toFixed(1) + ' ATR)', color: dirL === 0 ? SLEEP : '#F1F5F9' }] },
        { cells: [{ text: 'Signals here · plain trail', color: '#94A3B8' }, { text: taken + ' · ' + plainFlips, color: '#F1F5F9' }] },
        { cells: [{ text: cut < -0.5 ? 'Noise ADDED' : 'Noise removed', color: '#94A3B8' },
                  { text: cutTx, color: cut < -0.5 ? DN : cut > 0.5 ? UP : '#94A3B8' }] }
    ] : []
});

// ── Signals for scanners, alerts and the Strategy Tester
register_signal(myBuy, 'Buy signal');
register_signal(mySell, 'Sell signal');
register_signal(for_every(myBuy, mySell, (b, s) => b || s), 'Any signal');
register_signal(myRegOpen, 'Regime opened');
register_signal(myRegClose, 'Regime closed');
register_signal(myTrending, 'Trend regime active');
