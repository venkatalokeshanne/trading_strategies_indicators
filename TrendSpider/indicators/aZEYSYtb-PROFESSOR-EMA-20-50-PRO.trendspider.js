/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : PROFESSOR EMA 20/50 PRO
 * Author       : SZDEHGHSEDH
 * Source URL   : https://www.tradingview.com/script/aZEYSYtb-PROFESSOR-EMA-20-50-PRO
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : PROFESSOR EMA 20/50 PRO_TV
 *
 * The Pine original, in words: EMA 20 and EMA 50 of a chosen source, filled green while fast > slow, red otherwise.
 *
 * Deviations from the original: colour and width inputs not exposed (fixed colours). Cross/trend signals added for
 *   scanning.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('PROFESSOR EMA 20/50 PRO_TV', 'price');

const myCross = (_a, _b, _up) => {
    const _pa = shift(_a, 1), _pb = shift(_b, 1);
    return for_every(_a, _b, _pa, _pb, (a, b, pa, pb) => a !== null && b !== null && pa !== null && pb !== null &&
        (_up ? (a > b && pa <= pb) : (a < b && pa >= pb)));
};
const myAbove = (_a, _b) => for_every(_a, _b, (a, b) => a !== null && b !== null && a > b);

const myEmaTab = input.tab('EMA SETTINGS');
const myFastLen = myEmaTab.number('FAST EMA LENGTH', 20, { min: 1, max: 500 });
const mySlowLen = myEmaTab.number('SLOW EMA LENGTH', 50, { min: 1, max: 500 });
const mySourceName = myEmaTab.select('SOURCE', 'close', constants.price_source_options);
const myShowFill = input.tab('TREND FILL').boolean('SHOW TREND FILL', true);

const mySource = market[mySourceName];
const myEmaFast = ema(mySource, myFastLen);
const myEmaSlow = ema(mySource, mySlowLen);
paint(myEmaFast, { name: 'EMA FAST', color: '#00E676', thickness: 2 });
paint(myEmaSlow, { name: 'EMA SLOW', color: '#FF3D3D', thickness: 2 });
color_cloud(myEmaFast, myEmaSlow, myShowFill ? '#00E676' : 'rgba(0,0,0,0)', myShowFill ? '#FF3D3D' : 'rgba(0,0,0,0)', 'Bullish', 'Bearish');

register_signal(myCross(myEmaFast, myEmaSlow, true), 'Bullish Cross');
register_signal(myCross(myEmaFast, myEmaSlow, false), 'Bearish Cross');
register_signal(myAbove(myEmaFast, myEmaSlow), 'Bullish Trend');
