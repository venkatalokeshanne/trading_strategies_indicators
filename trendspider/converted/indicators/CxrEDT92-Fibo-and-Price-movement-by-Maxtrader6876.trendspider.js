/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Mask Man 9 & Price Movement V2
 * Author       : alanshospitality
 * Source URL   : https://www.tradingview.com/script/CxrEDT92-Fibo-and-Price-movement-by-Maxtrader6876
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Mask Man 9 & Price Movement V2_TV
 *
 * The Pine original, in words: EMA 9 of hlc3; BUY when hlc3 crosses above it and hlc3 is higher than 5 bars ago,
 *   SELL on the opposite.
 *
 * Deviations from the original: source fixed to hlc3 (the Pine input's default).
 * Not carried over: alert() calls — use the Mask Man Buy/Sell signals for alerts.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Mask Man 9 & Price Movement V2_TV', 'price');

const myCross = (_a, _b, _up) => {
    const _pa = shift(_a, 1), _pb = shift(_b, 1);
    return for_every(_a, _b, _pa, _pb, (a, b, pa, pb) => a !== null && b !== null && pa !== null && pb !== null &&
        (_up ? (a > b && pa <= pb) : (a < b && pa >= pb)));
};
const myAbove = (_a, _b) => for_every(_a, _b, (a, b) => a !== null && b !== null && a > b);

const myLength = input.number('Mask Man Length', 9, { min: 1, max: 200 });
const myPmLength = input.number('Price Movement Lookback', 5, { min: 1, max: 200 });
const myShowSignals = input.boolean('Show Buy/Sell Signals', true);

const mySource = hlc3;
const myMaskMa = ema(mySource, myLength);
const myChange = for_every(mySource, shift(mySource, myPmLength), (s, p) => p === null ? null : s - p);
const myBuy = for_every(myCross(mySource, myMaskMa, true), myChange, (x, ch) => x && ch !== null && ch > 0);
const mySell = for_every(myCross(mySource, myMaskMa, false), myChange, (x, ch) => x && ch !== null && ch < 0);

paint(myMaskMa, { name: 'Mask Man EMA (9)', color: '#2962FF', thickness: 1 });
paint(for_every(myBuy, b => myShowSignals && b ? 'BUY' : null), { name: 'Buy Signal', style: 'labels_below', color: '#4CAF50' });
paint(for_every(mySell, s => myShowSignals && s ? 'SELL' : null), { name: 'Sell Signal', style: 'labels_above', color: '#FF5252' });
register_signal(myBuy, 'Mask Man Buy');
register_signal(mySell, 'Mask Man Sell');
