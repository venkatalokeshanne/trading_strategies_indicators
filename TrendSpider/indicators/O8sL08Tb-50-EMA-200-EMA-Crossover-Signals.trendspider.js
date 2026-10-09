/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 50 EMA / 200 EMA Crossover Signals
 * Author       : Joelml
 * Source URL   : https://www.tradingview.com/script/O8sL08Tb-50-EMA-200-EMA-Crossover-Signals
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 50 EMA / 200 EMA Crossover Signals_TV
 *
 * The Pine original, in words: EMA 50 and EMA 200 with BUY/SELL labels on their crosses.
 *
 * Deviations from the original: none.
 * Not carried over: background tint on cross bars.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('50 EMA / 200 EMA Crossover Signals_TV', 'price');

const myCross = (_a, _b, _up) => {
    const _pa = shift(_a, 1), _pb = shift(_b, 1);
    return for_every(_a, _b, _pa, _pb, (a, b, pa, pb) => a !== null && b !== null && pa !== null && pb !== null &&
        (_up ? (a > b && pa <= pb) : (a < b && pa >= pb)));
};

const myEma50 = ema(close, 50);
const myEma200 = ema(close, 200);
const myBuy = myCross(myEma50, myEma200, true);
const mySell = myCross(myEma50, myEma200, false);

paint(myEma50, { name: '50 EMA', color: '#2962FF', thickness: 2 });
paint(myEma200, { name: '200 EMA', color: '#4CAF50', thickness: 4 });
paint(for_every(myBuy, _b => _b ? 'BUY' : null), { name: 'BUY', style: 'labels_below', color: '#4CAF50' });
paint(for_every(mySell, _s => _s ? 'SELL' : null), { name: 'SELL', style: 'labels_above', color: '#FF5252' });
register_signal(myBuy, 'Golden Cross Buy');
register_signal(mySell, 'Death Cross Sell');
