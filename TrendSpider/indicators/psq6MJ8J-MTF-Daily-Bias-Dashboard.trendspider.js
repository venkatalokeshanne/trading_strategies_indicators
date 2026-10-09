/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MTF Daily Bias Dashboard
 * Author       : Rahulb1997
 * Source URL   : https://www.tradingview.com/script/psq6MJ8J-MTF-Daily-Bias-Dashboard
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MTF Daily Bias Dashboard_TV
 *
 * Deviations from the original: Table is a static image of the last bar; timeframe text inputs replaced by selects;
 *   previous completed HTF bar values landed at the HTF bar open
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MTF Daily Bias Dashboard_TV', 'price');
const myDailyTf = input.select('Daily timeframe', 'D', ['D', 'W']);
const myFourHourTf = input.select('4-hour timeframe', '240', ['60', '120', '240', 'D']);
const myFifteenTf = input.select('15-minute timeframe', '15', ['5', '15', '30', '60']);
const myEmaLen = input.number('EMA period', 20, { min: 1, max: 500 });
const myTablePos = input.select('Table position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);
// Pine ta.ema: seeded with the SMA of the first length values
const myEma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; const myK = 2 / (_n + 1); return _s.map(_v => { if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = myK * _v + (1 - myK) * myAcc; return myAcc; }); };
const myBiasOn = async (_res) => {
	const myD = await request.history(current.ticker, _res);
	assert(!myD.error, 'Error fetching ' + _res + ' data: ' + myD.error);
	const myE = myEma(myD.close, myEmaLen);
	// close[1], close[2], ema[1] of the HTF bar: the last completed HTF bar, shown on every chart bar of the current HTF bar
	const myB = myD.close.map((_c, _k) => {
		if (_k < 2 || myE[_k - 1] === null) return 0;
		const myC1 = myD.close[_k - 1], myC2 = myD.close[_k - 2];
		if (myC1 > myE[_k - 1] && myC1 > myC2) return 1;
		if (myC1 < myE[_k - 1] && myC1 < myC2) return -1;
		return 0;
	});
	return interpolate_sparse_series(land_points_onto_series(myD.time, myB, time, 'ge'), 'constant');
};
const myDaily = await myBiasOn(myDailyTf);
const myFour = await myBiasOn(myFourHourTf);
const myFifteen = await myBiasOn(myFifteenTf);
const myText = (_b) => _b === 1 ? 'Bullish' : (_b === -1 ? 'Bearish' : 'Neutral');
const myCol = (_b) => _b === 1 ? '#089981' : (_b === -1 ? '#f23645' : '#808080');
const myLab = (_t) => _t === 'D' ? '1D' : (_t === '240' ? '4H' : (_t === '15' ? '15m' : _t));
const myLast = close.length - 1;
const myRow = (_t, _s) => ({ cells: [{ text: myLab(_t), color: 'white', background_color: '#222222' }, { text: myText(_s[myLast]), color: 'white', background_color: myCol(_s[myLast]) }] });
paint_overlay('MTF Bias Table', { position: myTablePos }, {
	rows: [
		{ cells: [{ text: 'Timeframe', color: 'white', background_color: 'black' }, { text: 'Bias', color: 'white', background_color: 'black' }] },
		myRow(myDailyTf, myDaily), myRow(myFourHourTf, myFour), myRow(myFifteenTf, myFifteen)
	]
});
register_signal(myDaily.map(_b => _b === 1), 'Daily Bullish Bias');
register_signal(myDaily.map(_b => _b === -1), 'Daily Bearish Bias');
register_signal(myDaily.map(_b => _b === 0), 'Daily Neutral Bias');
register_signal(myFour.map(_b => _b === 1), 'FourHour Bullish Bias');
register_signal(myFour.map(_b => _b === -1), 'FourHour Bearish Bias');
register_signal(myFour.map(_b => _b === 0), 'FourHour Neutral Bias');
register_signal(myFifteen.map(_b => _b === 1), 'FifteenMin Bullish Bias');
register_signal(myFifteen.map(_b => _b === -1), 'FifteenMin Bearish Bias');
register_signal(myFifteen.map(_b => _b === 0), 'FifteenMin Neutral Bias');
