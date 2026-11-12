/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : EURUSD Bullish / Bearish Indicator
 * Author       : pete170863
 * Source URL   : https://www.tradingview.com/script/2SeY4cVu-Beglan-EURUSD-Bullish-Bearish-Indicator
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : EURUSD Bullish Bearish Indicator_TV
 *
 * Deviations from the original: Reviewed AI draft; bgcolor replaced by a bias-coloured cloud between EMA 50 and 200;
 *   Pine-exact RSI; dashboard via paint_overlay.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('EURUSD Bullish Bearish Indicator_TV', 'price');
const myEmaFastLength = input.number('EMA 50', 50, { min: 1, max: 500 });
const myEmaSlowLength = input.number('EMA 200', 200, { min: 1, max: 500 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myMacdFast = input.number('MACD Fast', 12, { min: 1, max: 200 });
const myMacdSlow = input.number('MACD Slow', 26, { min: 1, max: 200 });
const myMacdSignal = input.number('MACD Signal', 9, { min: 1, max: 200 });
const myEma50 = ema(close, myEmaFastLength);
const myEma200 = ema(close, myEmaSlowLength);
// pine-parity: ta.rsi uses SMA-seeded RMA of gains/losses
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myAvgGain = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(_c - close[_i - 1], 0)), myRsiLength);
const myAvgLoss = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(close[_i - 1] - _c, 0)), myRsiLength);
const myRsi = myAvgGain.map((_g, _i) => (_g === null || myAvgLoss[_i] === null) ? null : (myAvgLoss[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myAvgLoss[_i])));
const myMacdLine = sub(ema(close, myMacdFast), ema(close, myMacdSlow));
const mySignalLine = ema(myMacdLine, myMacdSignal);
const myBullScore = close.map((_c, _i) => {
	const myVals = [myEma50[_i], myEma200[_i], myRsi[_i], myMacdLine[_i], mySignalLine[_i]];
	if (myVals.some(_v => _v === null || _v === undefined)) return null;
	const myHist = myMacdLine[_i] - mySignalLine[_i];
	return (myEma50[_i] > myEma200[_i] ? 1 : 0) + (_c > myEma50[_i] ? 1 : 0) + (myRsi[_i] > 50 ? 1 : 0) + (myMacdLine[_i] > mySignalLine[_i] ? 1 : 0) + (myHist > 0 ? 1 : 0);
});
const myBullish = myBullScore.map(_s => _s !== null && _s >= 4);
const myBearish = myBullScore.map(_s => _s !== null && (5 - _s) >= 4);
paint(myEma50, { name: 'EMA 50', color: 'orange', thickness: 2 });
paint(myEma200, { name: 'EMA 200', color: 'blue', thickness: 2 });
// bgcolor is not available: the band between the two EMAs is shaded by bias instead
const myGateTo = (_s, _f) => _s.map((_v, _i) => _f(_i) ? _v : null);
const myBullF = (_i) => myBullish[_i];
const myBearF = (_i) => myBearish[_i];
const myNeutralF = (_i) => !myBullish[_i] && !myBearish[_i];
color_cloud(myGateTo(myEma50, myBullF), myGateTo(myEma200, myBullF), 'rgba(0,200,0,0.2)', 'rgba(0,200,0,0.2)', 'Bull Up', 'Bull Dn');
color_cloud(myGateTo(myEma50, myBearF), myGateTo(myEma200, myBearF), 'rgba(200,0,0,0.2)', 'rgba(200,0,0,0.2)', 'Bear Up', 'Bear Dn');
color_cloud(myGateTo(myEma50, myNeutralF), myGateTo(myEma200, myNeutralF), 'rgba(128,128,128,0.15)', 'rgba(128,128,128,0.15)', 'Neutral Up', 'Neutral Dn');
const myLast = close.length - 1;
const myBull = myBullScore[myLast];
const myDirection = myBullish[myLast] ? 'BULLISH' : (myBearish[myLast] ? 'BEARISH' : 'NEUTRAL');
const myDirectionColor = myBullish[myLast] ? '#2ecc71' : (myBearish[myLast] ? '#e74c3c' : '#95a5a6');
const myRow = (_a, _b, _bg, _fg) => ({ cells: [{ text: _a, background_color: '#282828', color: '#ffffff' }, { text: _b, background_color: _bg, color: _fg }] });
paint_overlay('EURUSD Dashboard', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'EURUSD', background_color: '#000000', color: '#ffffff' }, { text: 'MARKET BIAS', background_color: '#000000', color: '#ffffff' }] },
		myRow('Direction', myDirection, myDirectionColor, '#ffffff'),
		myRow('Bull Score', myBull === null ? 'N/A' : myBull + ' / 5', '#000000', '#2ecc71'),
		myRow('Bear Score', myBull === null ? 'N/A' : (5 - myBull) + ' / 5', '#000000', '#e74c3c'),
		myRow('RSI', myRsi[myLast] === null ? 'N/A' : myRsi[myLast].toFixed(1), '#000000', myRsi[myLast] > 50 ? '#2ecc71' : '#e74c3c')
	]
});
register_signal(myBullish, 'Market Bullish');
register_signal(myBearish, 'Market Bearish');
register_signal(myBullish.map((_b, _i) => _b && _i > 0 && !myBullish[_i - 1]), 'Turned Bullish');
register_signal(myBearish.map((_b, _i) => _b && _i > 0 && !myBearish[_i - 1]), 'Turned Bearish');
