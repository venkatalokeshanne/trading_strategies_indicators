/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Custom Moving Averages
 * Author       : version
 * Source URL   : https://www.tradingview.com/script/yJ8J6Lcn-Multi-Timeframe-Trend-Indicator
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Custom Moving Averages_TV
 *
 * The Pine original, in words: SMA 20, 72, 200 and 420 of the close.
 *
 * Deviations from the original: cross signals added for scanning.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Custom Moving Averages_TV', 'price');

const myCross = (_a, _b, _up) => {
    const _pa = shift(_a, 1), _pb = shift(_b, 1);
    return for_every(_a, _b, _pa, _pb, (a, b, pa, pb) => a !== null && b !== null && pa !== null && pb !== null &&
        (_up ? (a > b && pa <= pb) : (a < b && pa >= pb)));
};

const myMa20 = sma(close, 20);
const myMa72 = sma(close, 72);
const myMa200 = sma(close, 200);
const myMa420 = sma(close, 420);

paint(myMa20, { name: '20-day MA', color: '#2962FF', thickness: 2 });
paint(myMa72, { name: '72-day MA', color: '#4CAF50', thickness: 2 });
paint(myMa200, { name: '200-day MA', color: '#FF5252', thickness: 2 });
paint(myMa420, { name: '420-day MA', color: '#FF9800', thickness: 2 });
register_signal(myCross(myMa20, myMa72, true), 'MA20 Cross Above MA72');
register_signal(myCross(myMa20, myMa72, false), 'MA20 Cross Below MA72');
register_signal(myCross(myMa72, myMa200, true), 'MA72 Cross Above MA200');
register_signal(myCross(myMa72, myMa200, false), 'MA72 Cross Below MA200');
