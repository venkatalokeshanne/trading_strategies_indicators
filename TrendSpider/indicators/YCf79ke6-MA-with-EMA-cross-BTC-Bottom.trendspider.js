/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MA with EMA cross + BTC Bottom
 * Author       : hamitcagdas
 * Source URL   : https://www.tradingview.com/script/YCf79ke6-MA-with-EMA-cross-BTC-Bottom
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MA with EMA cross_TV
 *
 * Deviations from the original: Only the SMA/EMA cross is converted. The on-chain BTC bottom lines need
 *   GLASSNODE/COINMETRICS market cap, realized cap and BTC supply feeds, which
 *   TrendSpider does not provide, so they are not carried over; the suggested-timeframe
 *   note sits bottom-left (bottom_center is not a valid position)
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MA with EMA cross_TV', 'price');
const myMaLen = input.number('MA Length (SMA)', 22, { min: 1, max: 500 });
const myEmaLen = input.number('EMA Length', 11, { min: 1, max: 500 });
const mySma = close.map((_c, _i) => { if (_i < myMaLen - 1) return null; let myS = 0; for (let myK = _i - myMaLen + 1; myK <= _i; myK += 1) myS += close[myK]; return myS / myMaLen; });
let myAcc = null, myCnt = 0, mySum = 0;
const myK2 = 2 / (myEmaLen + 1);
const myEma = close.map(_c => { if (myAcc === null) { mySum += _c; myCnt += 1; if (myCnt === myEmaLen) myAcc = mySum / myEmaLen; return myAcc; } myAcc = myK2 * _c + (1 - myK2) * myAcc; return myAcc; });
const myUp = close.map((_c, _i) => _i > 0 && myEma[_i] !== null && mySma[_i] !== null && myEma[_i - 1] !== null && mySma[_i - 1] !== null && myEma[_i] > mySma[_i] && myEma[_i - 1] <= mySma[_i - 1]);
const myDn = close.map((_c, _i) => _i > 0 && myEma[_i] !== null && mySma[_i] !== null && myEma[_i - 1] !== null && mySma[_i - 1] !== null && myEma[_i] < mySma[_i] && myEma[_i - 1] >= mySma[_i - 1]);
paint(mySma, { name: 'MA', color: 'blue', thickness: 2 });
paint(myEma, { name: 'EMA', color: 'orange', thickness: 2 });
paint(myUp.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: 'green' });
paint(myDn.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Sell Mark', style: 'labels_above', color: 'red' });
paint_overlay('Suggested Timeframe', { position: 'bottom_left' }, { rows: [{ cells: [{ text: 'Suggested Timeframe: 1W', color: 'gray', background_color: 'rgba(0,0,0,0)' }] }] });
register_signal(myUp, 'Buy Signal');
register_signal(myDn, 'Sell Signal');
