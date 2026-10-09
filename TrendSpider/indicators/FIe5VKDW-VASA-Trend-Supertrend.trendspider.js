/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VASA Trend (Supertrend)
 * Author       : VASATrendAI
 * Source URL   : https://www.tradingview.com/script/FIe5VKDW-VASA-Trend-Supertrend
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VASA Trend (Supertrend)_TV
 *
 * The Pine original, in words: Supertrend(10, 3) line coloured by trend, shaded to the close, with flip markers.
 *
 * Deviations from the original: the AI draft used TrendSpider's supertrend(), which ignores its inputs and flips on
 *   different bars; replaced by Pine's algorithm. Fill is one colour. Colour inputs not
 *   exposed.
 * Not carried over: alertconditions — use the flip signals.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VASA Trend (Supertrend)_TV', 'price');

const trendTab = input.tab('Trend');
const myAtrLength = trendTab.number('ATR length', 10, { min: 1, max: 200 });
const myAtrMultiplier = trendTab.number('ATR multiplier', 3.0, { min: 0.5, max: 20, step: 0.1 });
const styleTab = input.tab('Style');
const myShowFlips = styleTab.boolean('Show flip markers', true);
const myShowFill = styleTab.boolean('Shade trend channel', true);

// Pine ta.supertrend, step for step (TrendSpider's supertrend() differs — reference/02).
const myRma = (_src, _n) => {
    const out = series_of(null); let sumVal = 0, cnt = 0, prev = null;
    for (let i = 0; i < _src.length; i++) {
        const v = _src[i];
        if (v === null) continue;
        if (prev === null) { sumVal += v; cnt++; if (cnt === _n) { prev = sumVal / _n; out[i] = prev; } }
        else { prev = (prev * (_n - 1) + v) / _n; out[i] = prev; }
    }
    return out;
};
const myTr = for_every(high, low, shift(close, 1), (h, l, pc) => pc === null ? h - l : Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
const myAtr = myRma(myTr, myAtrLength);
const mySt = series_of(null), myDir = series_of(null);
let prevLower = null, prevUpper = null, prevSt = null;
for (let i = 0; i < close.length; i++) {
    if (myAtr[i] === null) continue;
    const mid = (high[i] + low[i]) / 2;
    let lower = mid - myAtrMultiplier * myAtr[i];
    let upper = mid + myAtrMultiplier * myAtr[i];
    const pc = i > 0 ? close[i - 1] : null;
    const pl = prevLower === null ? 0 : prevLower, pu = prevUpper === null ? 0 : prevUpper;
    if (!(lower > pl || (pc !== null && pc < pl))) lower = pl;
    if (!(upper < pu || (pc !== null && pc > pu))) upper = pu;
    let d;
    if (prevSt === null) d = 1;
    else if (prevSt === prevUpper) d = close[i] > upper ? -1 : 1;
    else d = close[i] < lower ? 1 : -1;
    mySt[i] = d === -1 ? lower : upper;
    myDir[i] = d;
    prevLower = lower; prevUpper = upper; prevSt = mySt[i];
}

const myUpColor = '#15803d', myDownColor = '#b91c1c';
const myIsUp = for_every(myDir, _d => _d === -1);
const myStPainted = paint(mySt, { name: 'VASA Trend', color: for_every(myIsUp, _u => _u ? myUpColor : myDownColor), thickness: 2 });
const myClosePainted = paint(close, { name: 'Close (hidden)', color: 'rgba(0,0,0,0)' });
fill(myClosePainted, myStPainted, myShowFill ? myUpColor : 'rgba(0,0,0,0)', 0.1);

const myPrevDir = shift(myDir, 1);
const myFlipUp = for_every(myDir, myPrevDir, (d, p) => d === -1 && p === 1);
const myFlipDown = for_every(myDir, myPrevDir, (d, p) => d === 1 && p === -1);
paint(for_every(myFlipUp, _f => myShowFlips && _f ? constants.icons.triangle_up : null), { name: 'Flip up', style: 'labels_below', color: myUpColor });
paint(for_every(myFlipDown, _f => myShowFlips && _f ? constants.icons.triangle_down : null), { name: 'Flip down', style: 'labels_above', color: myDownColor });
register_signal(myFlipUp, 'Trend flipped UP');
register_signal(myFlipDown, 'Trend flipped DOWN');
