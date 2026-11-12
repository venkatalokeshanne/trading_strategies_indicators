/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Centered RSI +/-50 Cross Strategy (TP Slider + ATR SL + Trailing Stop + JSON Alerts)
 * Author       : FUD2009
 * Source URL   : https://www.tradingview.com/script/ImaFsUd1-Centered-RSI-50-Cross-Strategy
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Centered RSI 50 Cross_TV
 *
 * The Pine original, in words: centered RSI = (RSI14 - 50) x 2; long when it crosses up through -50 (RSI 25), short
 *   when it crosses down through +50 (RSI 75); 5 contracts; exits by take-profit in
 *   points, ATR x multiplier stop, optional trailing stop
 *
 * Deviations from the original: Source input fixed to close. Take profit, ATR stop and trailing stop are not signals
 *   and are not reproduced.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry / Short Entry signal
 *   emerged; take profit 31 points; stop 1.5 ATR; optional trailing stop; 5 contracts;
 *   initial capital 50000. JSON alert texts dropped.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Centered RSI 50 Cross_TV', 'lower');
const myRsiLen = input.number('RSI Length', 14, { min: 1, max: 200 });
const myN = close.length;
// Pine ta.rsi: SMA-seeded RMA of gains and losses
let myUp = null, myDn = null, myCnt = 0, mySu = 0, mySd = 0;
const myRsi = close.map((_c, _i) => {
	if (_i === 0) return null;
	const myCh = _c - close[_i - 1], myG = Math.max(myCh, 0), myL = Math.max(-myCh, 0);
	if (myUp === null) { mySu += myG; mySd += myL; myCnt += 1; if (myCnt === myRsiLen) { myUp = mySu / myRsiLen; myDn = mySd / myRsiLen; } else return null; }
	else { myUp = (myUp * (myRsiLen - 1) + myG) / myRsiLen; myDn = (myDn * (myRsiLen - 1) + myL) / myRsiLen; }
	return myDn === 0 ? 100 : 100 - 100 / (1 + myUp / myDn);
});
const myCrsi = myRsi.map(_r => _r === null ? null : (_r - 50) * 2);
const myLong = close.map((_c, _i) => _i > 0 && myCrsi[_i] !== null && myCrsi[_i - 1] !== null && myCrsi[_i - 1] <= -50 && myCrsi[_i] > -50);
const myShort = close.map((_c, _i) => _i > 0 && myCrsi[_i] !== null && myCrsi[_i - 1] !== null && myCrsi[_i - 1] >= 50 && myCrsi[_i] < 50);
paint(myCrsi, { name: 'Centered RSI', color: 'blue', thickness: 2 });
paint(horizontal_line(50), { name: 'Upper Level', color: 'red', style: 'dotted' });
paint(horizontal_line(-50), { name: 'Lower Level', color: 'green', style: 'dotted' });
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'dotted' });
register_signal(myLong, 'Long Entry');
register_signal(myShort, 'Short Entry');
