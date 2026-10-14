"""Builds the TrendSpider script from the checked calculation (core.js), so the code that matched Foresight value for
value is exactly the code that runs in TrendSpider.
Output: TrendSpider/indicators/NCEqAlgo-Neural-Confluence-Engine-Quantum-Algo.trendspider.js"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
REPO = HERE.parents[2]
OUT = REPO / "TrendSpider" / "indicators" / "NCEqAlgo-Neural-Confluence-Engine-Quantum-Algo.trendspider.js"

core = (HERE / "core.js").read_text(encoding="utf-8")
body = core[core.index("function nceCompute"):core.index('if (typeof module !== "undefined")')].rstrip()

HEADER = """/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Neural Confluence Engine [Quantum Algo]
 * Author       : Quantum Algo (as named in the script title)
 * Source URL   : not given — source pasted by the user on 2026-10-14 (TradingView/indicators/NCEqAlgo-…pine)
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-14 by Claude (pine-to-trendspider skill, full procedure)
 * TrendSpider name : Neural Confluence Engine [Quantum Algo]_TV
 * Live tested  : __LIVE__
 *
 * What it does:
 *   Eight factors — WaveTrend, EMA stack (9/21/50), session VWAP, RSI 14, MACD histogram, ADX 14, volume vs its
 *   20-bar average, and the Bollinger-inside-Keltner squeeze — are scored, weighted (1.5, 1.3, 1.0, 0.8, 0.8, 0.7,
 *   1.0, 1.2) and smoothed into a Bull and a Bear score from 0 to 100.
 *   BUY / SELL: the 9 EMA crosses the 21 EMA (the ribbon changes colour), whatever the score.
 *   BUY+ / SELL+: the same cross when the Bull (Bear) score is at least 60 and, with the filter on, the 9 EMA is
 *   above (below) the 21 EMA on the higher timeframe (auto: 15m -> 1h, 1h -> 4h, D -> W, …).
 *   Each signal starts a tracked trade: stop 1.5 x ATR, targets at 1, 2 and 3 R; after TP1 the stop trails
 *   (break-even, then TP1, TP2, and half an ATR behind each bar). It is a display tracker — it places no orders.
 *
 * Checked: the calculation (tools/parity/nce/core.js, pasted below unchanged) against Foresight running the Pine
 *   source: NVDA 15m (26,140 bars, 1h filter) and AAPL 1h (13,245 bars, 4h filter). Bull/Bear scores, VWAP, RSI,
 *   MACD, WaveTrend, ATR, squeeze, the higher-timeframe EMAs, every BUY/SELL/BUY+/SELL+ and squeeze event, and the
 *   trade tracker (direction, TP1, SL hit, trailing stop) are identical on every bar after 150 bars of warm-up.
 *   ADX differs by at most 0.004 for about 60 bars after that warm-up (its seed), which changes no score.
 *
 * Deviations from the original:
 *   - Number inputs are whole numbers (the TrendSpider phone app rejects decimals): "SL ATR Mult (tenths)" 15 = 1.5,
 *     "TP1/2/3 R:R (tenths)" 10/20/30 = 1/2/3. Input titles shortened to TrendSpider's limit.
 *   - The higher-timeframe bars are TrendSpider's own (e.g. its 4-hour bars), landed as Pine's lookahead_off does: a
 *     chart bar sees an HTF bar's EMA from that HTF bar's last chart bar. Where TrendSpider's HTF bars start at other
 *     times than TradingView's (4-hour bars on stocks), the filter can switch on different bars.
 *   - Squeeze background (gold) and the optional momentum background are drawn as faint columns around each candle
 *     (TrendSpider has no full-height background); the squeeze column is slightly stronger so it shows.
 *   - Ribbon fills change colour at the bar where the 9/21 EMAs cross, as in Pine; TrendSpider fills take one colour,
 *     so each fill is painted twice (up / down) between hidden copies of the EMAs.
 *   - BUY / SELL / BUY+ / SELL+ are TrendSpider text labels; their text colour is TrendSpider's. The NCE score label
 *     hangs off a hidden line at low − 0.8 ATR (high + 0.8 ATR), as in Pine. Score labels: the latest 500 (Pine's
 *     max_labels_count). The squeeze "⚡" diamonds are gold diamonds below/above the bar.
 *   - TP/SL level lines (off by default) end at the last bar with their price labels there (Pine: 10 bars to the
 *     right), all solid (TrendSpider has no dashed line; Pine dashes the targets not yet hit and the trailing stop —
 *     here those are thinner). Prices are shown to 2 decimals (4 below $1) instead of the symbol's tick.
 *   - "EMA Base" (Pine: crosses) is drawn as small diamonds.
 *   - Added: an "NCE SL Hit Signal" for alerts / scanners (the Pine script draws SL HIT but has no alert for it).
 *
 * Not carried over:
 *   - Pine's {{plot_0}} placeholder in the BUY+/SELL+ alert text — TrendSpider alerts carry their own text.
 * ───────────────────────────────────────────────────────────────────────
 */
"""

MAIN = r"""
describe_indicator('Neural Confluence Engine [Quantum Algo]_TV', 'overlay', { shortName: 'NCE' });

// ── Inputs (Pine defaults; whole numbers — LESSONS L26) ──────────────────
const scoreMin = input.number('Min Confluence Score', 60, { min: 20, max: 95 });
const htfFilterOn = input.boolean('HTF Trend Filter', true);
const htfChoice = input.select('HTF Timeframe', 'auto', ['auto', '1', '5', '15', '30', '60', '240', 'D', 'W', 'M']);
const wtChannelLen = input.number('WT Channel Length', 9, { min: 2 });
const wtAvgLen = input.number('WT Average Length', 12, { min: 2 });
const emaFastLen = input.number('Fast EMA', 9, { min: 2 });
const emaSlowLen = input.number('Slow EMA', 21, { min: 2 });
const emaBaseLen = input.number('Baseline EMA', 50, { min: 10 });
const atrLength = input.number('ATR Length', 14, { min: 5 });
const slTenths = input.number('SL ATR Mult (tenths)', 15, { min: 5 });
const tp1Tenths = input.number('TP1 R:R (tenths)', 10, { min: 5 });
const tp2Tenths = input.number('TP2 R:R (tenths)', 20, { min: 10 });
const tp3Tenths = input.number('TP3 R:R (tenths)', 30, { min: 15 });
const trailAfterTp1 = input.boolean('Trail SL after TP1', true);
const showRibbon = input.boolean('Show Wave Ribbon', true);
const showDash = input.boolean('Show Dashboard', true);
const showLevels = input.boolean('Show TP/SL Levels', false);
const showWave = input.boolean('Show Background Wave', false);
const dashSize = input.select('Dashboard Size', 'small', ['tiny', 'small', 'normal']);
const ribbonOpac = input.number('Ribbon Opacity', 82, { min: 0, max: 100 });

// ── The Pine calculation, checked against Foresight (tools/parity/nce/core.js, unchanged) ──
__CORE__

// ── Data ─────────────────────────────────────────────────────────────────
const C_CYAN = '#00E5FF', C_PURPLE = '#6C5CE7', C_GREEN = '#00E676', C_RED = '#FF3D71', C_ORANGE = '#FF9F43';
const C_TEAL = '#00D4AA', C_GOLD = '#F0B429', C_BG = '#0A0E1A', C_SURFACE = '#141930', C_MUTED = '#7B82A0';
// Pine color.new(hex, transp): transp 0 = opaque … 100 = invisible. Written as #RRGGBBAA — the engine rejects
// rgba() strings in some paints (columnrange)
const colorNew = (hex, transp) => {
    const t = Math.min(100, Math.max(0, transp));
    const a = Math.round(255 * (1 - t / 100)).toString(16).padStart(2, '0');
    return hex.slice(0, 7) + a;
};
const isNaV = (v) => v === null || v === undefined || Number.isNaN(v);
const nBars = close.length, lastI = nBars - 1;
const resStr = String(current.resolution);
const intraday = /^\d+$/.test(resStr);
// Pine f_autoHTF()
const autoHtf = { '1': '5', '3': '15', '5': '30', '15': '60', '30': '240', '60': '240', '120': 'D', '240': 'D', 'D': 'W', 'W': 'M' };
const htfRes = htfChoice === 'auto' ? (autoHtf[resStr] || 'D') : htfChoice;
let htfFast = null, htfSlow = null;
try {
    const htfData = await request.history(current.ticker, htfRes);
    if (htfData && !htfData.error && htfData.time && htfData.time.length) {
        htfFast = landHtf(time, htfData.time, nceEma(htfData.close, emaFastLen));
        htfSlow = landHtf(time, htfData.time, nceEma(htfData.close, emaSlowLen));
    }
} catch (err) {
    htfFast = null;                     // no higher-timeframe data: the filter blocks BUY+/SELL+ (dashboard says n/a)
}
// ta.vwap resets each session: a new exchange-time day on intraday charts, every bar on D / W / M
const newSession = time.map((t, i) => {
    if (!intraday || i === 0) return true;
    const a = time_of(t), b = time_of(time[i - 1]);
    return a.dayOfYear !== b.dayOfYear || a.year !== b.year;
});
const R = nceCompute(
    { o: open, h: high, l: low, c: close, v: volume, newSession, htfFast, htfSlow },
    { threshold: scoreMin, htfFilter: htfFilterOn, wtChannel: wtChannelLen, wtAvg: wtAvgLen, emaFast: emaFastLen,
      emaSlow: emaSlowLen, emaBase: emaBaseLen, atrLen: atrLength, slMult: slTenths / 10, tp1Mult: tp1Tenths / 10,
      tp2Mult: tp2Tenths / 10, tp3Mult: tp3Tenths / 10, trail: trailAfterTp1 });
const T = R.trade;
const plainBuy = R.flipBull.map((f, i) => f && !R.buyPlus[i]);
const plainSell = R.flipBear.map((f, i) => f && !R.sellPlus[i]);
const anyTrigger = R.flipBull.map((f, i) => f || R.buyPlus[i] || R.flipBear[i] || R.sellPlus[i]);
const firstHit = (hit) => hit.map((h, i) => h && !(i > 0 && hit[i - 1]));       // Pine: x and not x[1]
const tp1Event = firstHit(T.tp1Hit), tp2Event = firstHit(T.tp2Hit), tp3Event = firstHit(T.tp3Hit);
const slEvent = firstHit(T.slHit);
const fmtPrice = (v) => (isNaV(v) ? 'n/a' : Math.abs(v) >= 1 ? v.toFixed(2) : v.toFixed(4));

// ── Wave ribbon ──────────────────────────────────────────────────────────
const ribbonOr = (s) => (showRibbon ? s : series_of(null));
paint(ribbonOr(R.ema5), { name: 'EMA 5', color: colorNew(C_CYAN, 40), thickness: 1 });
paint(ribbonOr(R.ema13), { name: 'EMA 13', color: colorNew(C_CYAN, 60), thickness: 1 });
paint(ribbonOr(R.emaFast), { name: 'EMA Fast', color: colorNew(C_TEAL, 30), thickness: 2 });
paint(ribbonOr(R.emaSlow), { name: 'EMA Slow', color: colorNew(C_PURPLE, 30), thickness: 2 });
paint(ribbonOr(R.ema34), { name: 'EMA 34', color: colorNew(C_PURPLE, 60), thickness: 1 });
paint(ribbonOr(R.emaBase), { name: 'EMA Base', color: colorNew(C_ORANGE, 50), style: 'dotted', marker: 'diamond', thickness: 1 });
// Pine colours the fill segment ending at bar i by emaFast > emaSlow on bar i; a hidden copy of each EMA is kept on
// the bars an "up" (or "down") segment touches, and each copy pair is filled in one colour. Drawing only.
const upSeg = R.ribbonBull.map((b, i) => b || (i < lastI && R.ribbonBull[i + 1]));
const dnSeg = R.ribbonBull.map((b, i) => !b || (i < lastI && !R.ribbonBull[i + 1]));
const hiddenCopy = (s, seg) => s.map((v, i) => (showRibbon && seg[i] ? v : null));
const ghost = { color: '#00000000', thickness: 1, editorHidden: true };
const up5 = paint(hiddenCopy(R.ema5, upSeg), { name: 'Ribbon 5 up', ...ghost });
const upF = paint(hiddenCopy(R.emaFast, upSeg), { name: 'Ribbon fast up', ...ghost });
const upS = paint(hiddenCopy(R.emaSlow, upSeg), { name: 'Ribbon slow up', ...ghost });
const up34 = paint(hiddenCopy(R.ema34, upSeg), { name: 'Ribbon 34 up', ...ghost });
const dn5 = paint(hiddenCopy(R.ema5, dnSeg), { name: 'Ribbon 5 down', ...ghost });
const dnF = paint(hiddenCopy(R.emaFast, dnSeg), { name: 'Ribbon fast down', ...ghost });
const dnS = paint(hiddenCopy(R.emaSlow, dnSeg), { name: 'Ribbon slow down', ...ghost });
const dn34 = paint(hiddenCopy(R.ema34, dnSeg), { name: 'Ribbon 34 down', ...ghost });
const alphaOf = (extra) => 1 - Math.min(100, Math.max(0, 100 - ribbonOpac + extra)) / 100;
fill(up5, upF, C_CYAN, alphaOf(15), 'Ribbon outer up');
fill(upF, upS, C_TEAL, alphaOf(0), 'Ribbon core up');
fill(upS, up34, C_PURPLE, alphaOf(20), 'Ribbon inner up');
fill(dn5, dnF, C_RED, alphaOf(15), 'Ribbon outer down');
fill(dnF, dnS, C_RED, alphaOf(0), 'Ribbon core down');
fill(dnS, dn34, C_RED, alphaOf(20), 'Ribbon inner down');

paint(R.vwapVal, { name: 'VWAP', style: 'dotted', marker: 'circle', thickness: 2,
    color: R.vwapVal.map((v, i) => (close[i] > v ? colorNew(C_GREEN, 30) : colorNew(C_RED, 30))) });

// ── Backgrounds (as faint columns around each candle) ────────────────────
const columnAt = (on) => on.map((o, i) => (o && !isNaV(R.atrVal[i]) ? { high: high[i] + R.atrVal[i], low: low[i] - R.atrVal[i] } : null));
paint(columnAt(R.nce.map((v) => showWave && !isNaV(v))), { name: 'Momentum wave zone', style: 'columnrange',
    color: R.nce.map((v) => (isNaV(v) ? null : colorNew(v > 0 ? C_CYAN : C_RED, Math.round(96 - (Math.abs(v) / 100) * 12)))) });
paint(columnAt(R.sqzOn), { name: 'Squeeze active zone', style: 'columnrange', color: colorNew(C_GOLD, 85) });

// ── Signal labels ────────────────────────────────────────────────────────
const textWhere = (cond, text) => cond.map((c) => (c ? text : null));
paint(textWhere(plainBuy, 'BUY'), { name: 'BUY labels', style: 'labels_below', color: C_TEAL, backgroundColor: C_TEAL });
paint(textWhere(plainSell, 'SELL'), { name: 'SELL labels', style: 'labels_above', color: C_ORANGE, backgroundColor: C_ORANGE });
paint(textWhere(R.buyPlus, 'BUY+'), { name: 'BUY plus labels', style: 'labels_below', color: C_CYAN, backgroundColor: C_CYAN });
paint(textWhere(R.sellPlus, 'SELL+'), { name: 'SELL plus labels', style: 'labels_above', color: C_RED, backgroundColor: C_RED });
// NCE score labels (BUY+ / SELL+ only), hanging off a hidden line at low - 0.8 ATR / high + 0.8 ATR
const scoreAt = R.buyPlus.map((b, i) => (isNaV(R.atrVal[i]) ? null
    : b ? low[i] - R.atrVal[i] * 0.8 : R.sellPlus[i] ? high[i] + R.atrVal[i] * 0.8 : null));
const scoreLine = paint(scoreAt, { name: 'NCE score level', ...ghost });
const scoreBars = scoreAt.map((v, i) => (v === null ? -1 : i)).filter((i) => i >= 0).slice(-500);
for (let k = 0; k < scoreBars.length; k++) {
    const i = scoreBars[k], isBuy = R.buyPlus[i];
    const sc = isBuy ? R.bullScore[i] : R.bearScore[i];
    paint_label_at_line(scoreLine, i, `NCE ${Math.round(sc)}%${R.sqzFiring[i] ? ' ⚡' : ''}`, {
        color: '#FFFFFF', background_color: colorNew(isBuy ? C_CYAN : C_RED, 40), vertical_align: isBuy ? 'bottom' : 'top' });
}
paint(R.sqzFiring.map((f, i) => (f && R.sqzMom[i] > 0 && !isNaV(R.atrVal[i]) ? low[i] - R.atrVal[i] * 0.3 : null)),
    { name: 'Squeeze Bull', style: 'dotted', marker: 'diamond', color: C_GOLD, thickness: 3 });
paint(R.sqzFiring.map((f, i) => (f && R.sqzMom[i] < 0 && !isNaV(R.atrVal[i]) ? high[i] + R.atrVal[i] * 0.3 : null)),
    { name: 'Squeeze Bear', style: 'dotted', marker: 'diamond', color: C_GOLD, thickness: 3 });

// ── TP / SL hit labels — the last trade's only (Pine deletes them when a new trade opens) ──
let lastTrigger = -1;
for (let i = 0; i < nBars; i++) if (anyTrigger[i]) lastTrigger = i;
const lastEvent = (ev) => { let at = -1; for (let i = Math.max(lastTrigger, 0); i < nBars; i++) if (ev[i]) at = i; return lastTrigger < 0 ? -1 : at; };
const hitLabel = (ev, priceOf, name, text, bg) => {
    const at = lastEvent(ev);
    const s = series_of(null);
    if (at >= 0) s[at] = priceOf[at];
    const ref = paint(s, { name, ...ghost });
    if (at >= 0 && !isNaV(priceOf[at])) paint_label_at_line(ref, at, text, { color: '#FFFFFF', background_color: bg, vertical_align: 'middle' });
};
hitLabel(tp1Event, T.tp1, 'TP1 hit level', 'TP1 ✓', C_TEAL);
hitLabel(tp2Event, T.tp2, 'TP2 hit level', 'TP2 ✓', C_GREEN);
hitLabel(tp3Event, T.tp3, 'TP3 hit level', 'TP3 ✓', C_GREEN);
hitLabel(slEvent, T.trail, 'SL hit level', 'SL HIT', C_RED);

// ── Trade level lines — last trade, off by default ───────────────────────
const lvOn = showLevels && T.dir[lastI] !== 0;
const left = Math.max(T.entryBar[lastI], lastI - 4999);
const trailing = T.tp1Hit[lastI] && trailAfterTp1;
const slShown = trailing ? T.trail[lastI] : T.sl[lastI];
const level = (v, name, color, thick, text) => {
    const ref = paint(lvOn && !isNaV(v) ? horizontal_line(v, left, lastI) : series_of(null),
        { name, color, thickness: thick, style: 'line' });   // no dashed style in TrendSpider
    if (lvOn && !isNaV(v)) paint_label_at_line(ref, lastI, text, { color: '#FFFFFF', background_color: color, vertical_align: 'middle' });
};
level(T.entry[lastI], 'Entry level', C_CYAN, 2, `ENTRY ${fmtPrice(T.entry[lastI])}`);
level(slShown, 'Stop level', trailing ? C_ORANGE : C_RED, 2, `${trailing ? 'TRAIL' : 'SL'} ${fmtPrice(slShown)}`);
level(T.tp1[lastI], 'TP1 level', C_TEAL, T.tp1Hit[lastI] ? 2 : 1, `${T.tp1Hit[lastI] ? 'TP1 ✓' : 'TP1'} ${fmtPrice(T.tp1[lastI])}`);
level(T.tp2[lastI], 'TP2 level', T.tp2Hit[lastI] ? C_TEAL : C_GREEN, T.tp2Hit[lastI] ? 2 : 1, `${T.tp2Hit[lastI] ? 'TP2 ✓' : 'TP2'} ${fmtPrice(T.tp2[lastI])}`);
level(T.tp3[lastI], 'TP3 level', C_GREEN, T.tp3Hit[lastI] ? 2 : 1, `${T.tp3Hit[lastI] ? 'TP3 ✓' : 'TP3'} ${fmtPrice(T.tp3[lastI])}`);

// ── Candle colouring ─────────────────────────────────────────────────────
color_candles(R.buyPlus.map((b, i) => (b ? C_CYAN : R.sellPlus[i] ? C_RED : R.flipBull[i] ? C_TEAL : R.flipBear[i] ? C_ORANGE : R.sqzFiring[i] ? C_GOLD : null)));

// ── Dashboard (last bar) ─────────────────────────────────────────────────
const bull = R.bullScore[lastI], bear = R.bearScore[lastI];
const adxNow = R.adxVal[lastI], rsiNow = R.rsiVal[lastI], volNow = R.volRatio[lastI], vw = R.vwapVal[lastI];
const wtBull = R.wtTci[lastI] > R.wtSig[lastI] && !isNaV(R.wtSig[lastI]);
const bias = bull > bear + 20 ? 'STRONG BULL' : bear > bull + 20 ? 'STRONG BEAR' : bull > bear ? 'MILD BULL' : 'MILD BEAR';
const htfKnown = htfFast !== null;
const status = T.dir[lastI] === 0 ? 'NO TRADE' : T.slHit[lastI] ? 'CLOSED' : T.tp3Hit[lastI] ? 'TP3 HIT' : T.tp2Hit[lastI] ? 'TP2 HIT' : T.tp1Hit[lastI] ? 'TP1 HIT → TRAIL' : 'ACTIVE';
const statusBg = T.dir[lastI] === 0 ? C_MUTED : T.slHit[lastI] ? colorNew(C_RED, 20) : T.tp1Hit[lastI] ? colorNew(C_TEAL, 20) : colorNew(C_CYAN, 20);
const roundTxt = (v) => (isNaV(v) ? 'n/a' : String(Math.round(v)));
const cell = (text, color, background) => ({ text, color, background, padding: '2px 8px' });
const dashRow = (a, aColor, b, bColor, bBg, aBg) => ({ cells: [cell(a, aColor, aBg || C_BG), cell(b, bColor, bBg || C_BG)] });
paint_overlay('NCE Dashboard', { position: 'top_right', offset_x: 10, offset_y: 10, order: 'above_all' }, {
    fontSize: dashSize === 'tiny' ? 10 : dashSize === 'small' ? 12 : 14,
    background: colorNew(C_SURFACE, 5), border: `2px solid ${colorNew(C_CYAN, 60)}`,
    rows: showDash ? [
        dashRow('NCE', C_CYAN, `${current.ticker}  ${resStr}`, C_CYAN),
        dashRow('BULL', '#FFFFFF', `${roundTxt(bull)}%`, '#FFFFFF', colorNew(C_GREEN, 30), colorNew(C_GREEN, 30)),
        dashRow('BEAR', '#FFFFFF', `${roundTxt(bear)}%`, '#FFFFFF', colorNew(C_RED, 30), colorNew(C_RED, 30)),
        dashRow('BIAS', '#FFFFFF', bias, '#FFFFFF', colorNew(bias.includes('BULL') ? C_GREEN : C_RED, 40)),
        dashRow('HTF', C_MUTED, !htfKnown ? 'n/a' : R.htfBullish[lastI] ? 'BULLISH' : 'BEARISH', '#FFFFFF',
            !htfKnown ? C_BG : colorNew(R.htfBullish[lastI] ? C_GREEN : C_RED, 40)),
        dashRow('WaveTrend', C_MUTED, wtBull ? 'BULL' : 'BEAR', wtBull ? C_GREEN : C_RED),
        dashRow('VWAP', C_MUTED, close[lastI] > vw ? 'ABOVE' : 'BELOW', close[lastI] > vw ? C_GREEN : C_RED),
        dashRow('Squeeze', C_MUTED, R.sqzOn[lastI] ? 'ON' : R.sqzFiring[lastI] ? 'FIRING' : 'OFF',
            R.sqzOn[lastI] ? C_GOLD : R.sqzFiring[lastI] ? C_GREEN : C_MUTED),
        dashRow('ADX', C_MUTED, `${roundTxt(adxNow)}${adxNow > 25 ? ' STRONG' : ' WEAK'}`, adxNow > 25 ? C_GREEN : C_MUTED),
        dashRow('Volume', C_MUTED, `${roundTxt(isNaV(volNow) ? null : volNow * 100)}%`, volNow > 1 ? C_GREEN : C_MUTED),
        dashRow('RSI', C_MUTED, roundTxt(rsiNow), rsiNow > 50 ? C_GREEN : C_RED),
        dashRow('TRADE', C_MUTED, status, '#FFFFFF', statusBg),
        dashRow('THRESHOLD', C_MUTED, `${scoreMin}%`, C_CYAN),
    ] : [],
});

// ── Scores (legend / data only) ──────────────────────────────────────────
paint(R.bullScore, { name: 'Bull Score', color: C_GREEN, hidden: true });
paint(R.bearScore, { name: 'Bear Score', color: C_RED, hidden: true });
paint(R.nce, { name: 'NCE Net Score', color: C_CYAN, hidden: true });

// ── Signals — for alerts, scanners and the Strategy Tester ───────────────
register_signal(R.flipBull, 'NCE Buy Signal');
register_signal(R.flipBear, 'NCE Sell Signal');
register_signal(R.buyPlus, 'NCE Buy Plus Signal');
register_signal(R.sellPlus, 'NCE Sell Plus Signal');
register_signal(R.sqzFiring, 'NCE Squeeze Breakout Signal');
register_signal(tp1Event, 'NCE TP1 Hit Signal');
register_signal(tp2Event, 'NCE TP2 Hit Signal');
register_signal(tp3Event, 'NCE TP3 Hit Signal');
register_signal(slEvent, 'NCE SL Hit Signal');
"""

live = sys.argv[1] if len(sys.argv) > 1 else "not yet"
text = HEADER.replace("__LIVE__", live) + MAIN.replace("__CORE__", body)
OUT.write_text(text, encoding="utf-8")
print("wrote", OUT, len(text.splitlines()), "lines")
