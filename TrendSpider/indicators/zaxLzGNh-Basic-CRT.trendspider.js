/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Basic CRT
 * Author       : Wunsch-Indikator
 * Source URL   : https://www.tradingview.com/script/zaxLzGNh-Basic-CRT
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Basic CRT_TV
 *
 * Deviations from the original: Reviewed AI draft; sweep/draw lines are gray/white level lines on the two bars;
 *   Confirmed option and line styles dropped.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Basic CRT_TV', 'price');
const myCrtTab = input.tab('CRT');
const myBullColor = myCrtTab.color('CRT Bullish', 'green');
const myBearColor = myCrtTab.color('CRT Bearish', 'red');
const myShowSweep = myCrtTab.boolean('Show Sweep Lines', true);
const myShowDraw = myCrtTab.boolean('Show Draw Lines', true);
const myTfTab = input.tab('Timeframes');
const myTfFilterActive = myTfTab.boolean('Timeframe Filter', true);
const myTfMin = myTfTab.number('Min Timeframe min', 1, { min: 1, max: 100000 });
const myTfMax = myTfTab.number('Max Timeframe min', 15, { min: 1, max: 100000 });
const myResMinutes = (_res) => {
	if (!isNaN(Number(_res))) return Number(_res);
	if (_res === 'D') return 1440;
	if (_res === 'W') return 10080;
	if (_res === 'M') return 43200;
	return 1440;
};
const myCurrentMinutes = myResMinutes(current.resolution);
const myTfPass = !myTfFilterActive || (myCurrentMinutes >= myTfMin && myCurrentMinutes <= myTfMax);
const myBullCrt = series_of(false);
const myBearCrt = series_of(false);
const mySweepLevel = series_of(null);
const myDrawLevel = series_of(null);
for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myPrev = myIndex - 1;
	const myIsBull = myTfPass && close[myIndex] > close[myPrev] && low[myIndex] < low[myPrev] && high[myIndex] < high[myPrev];
	const myIsBear = myTfPass && close[myIndex] < close[myPrev] && low[myIndex] > low[myPrev] && high[myIndex] > high[myPrev];
	myBullCrt[myIndex] = myIsBull;
	myBearCrt[myIndex] = myIsBear;
	if (myIsBull) {
		if (myShowSweep) { mySweepLevel[myPrev] = low[myPrev]; mySweepLevel[myIndex] = low[myPrev]; }
		if (myShowDraw) { myDrawLevel[myPrev] = high[myPrev]; myDrawLevel[myIndex] = high[myPrev]; }
	} else if (myIsBear) {
		if (myShowDraw) { myDrawLevel[myPrev] = low[myPrev]; myDrawLevel[myIndex] = low[myPrev]; }
		if (myShowSweep) { mySweepLevel[myPrev] = high[myPrev]; mySweepLevel[myIndex] = high[myPrev]; }
	}
}
color_candles(for_every(myBullCrt, myBearCrt, (_bull, _bear) => _bull ? myBullColor : (_bear ? myBearColor : null)));
paint(mySweepLevel, { name: 'Sweep', color: 'gray', thickness: 2 });
paint(myDrawLevel, { name: 'Draw', color: 'white', thickness: 2 });
register_signal(myBullCrt, 'Bullish CRT');
register_signal(myBearCrt, 'Bearish CRT');
