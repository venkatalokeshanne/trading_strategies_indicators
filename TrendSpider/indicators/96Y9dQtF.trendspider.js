/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Kalman Trend Filter
 * Author       : alirk8907
 * Source URL   : https://www.tradingview.com/script/96Y9dQtF
 * Pine version : v6
 * Licence      : CC BY-NC-SA 4.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Kalman Trend Filter_TV
 *
 * Deviations from the original: Reviewed TrendSpider-AI draft, live-tested. Colour/width/extend-right options not
 *   available; higher-timeframe values lag one completed HTF bar (non-repainting).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Kalman Trend Filter_TV', 'price');
const myShortLen = input.number('Short Period', 50, { min: 1, max: 1000 });
const myLongLen = input.number('Long Period', 150, { min: 1, max: 1000 });
const myProcessNoise = input.number('Process Noise Q', 0.01, { min: 0.0001, max: 10, step: 0.001 });
const myKalman = (_len) => {
	let myP = 1.0;
	const myR = _len * 0.1;
	return for_every(close, (_close, _prevX, _index) => {
		const myPrevX = _index === 0 || _prevX === null ? _close : _prevX;
		const myPPred = myP + myProcessNoise;
		const myK = myPPred / (myPPred + myR);
		myP = (1.0 - myK) * myPPred;
		return myPrevX + myK * (_close - myPrevX);
	});
};
const myShortX = myKalman(myShortLen);
const myLongX = myKalman(myLongLen);
const myTrendUp = for_every(myShortX, myLongX, (_s, _l) => _s > _l);
const myShortRising = for_every(myShortX, shift(myShortX, 2), (_s, _s2) => _s2 !== null && _s > _s2);
const myUpperColor = '#13bd6e';
const myLowerColor = '#af0d4b';
paint(myShortX, { name: 'Short Kalman', color: for_every(myShortRising, _r => _r ? myUpperColor : myLowerColor), thickness: 1 });
paint(myLongX, { name: 'Long Kalman', color: for_every(myTrendUp, _u => _u ? myUpperColor : myLowerColor), thickness: 2 });
color_cloud(myShortX, myLongX, myUpperColor, myLowerColor, 'Bull Fill', 'Bear Fill');
const myPrevUp = shift(myTrendUp, 1);
register_signal(for_every(myTrendUp, myPrevUp, (_n, _p) => _n === true && _p === false), 'Bullish Cross');
register_signal(for_every(myTrendUp, myPrevUp, (_n, _p) => _n === false && _p === true), 'Bearish Cross');
register_signal(myTrendUp, 'Trend Up');
