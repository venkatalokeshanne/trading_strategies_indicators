/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : CM_Laguerre PPO PercentileRank Mkt Tops & Bottoms
 * Author       : Trader_BPL
 * Source URL   : https://www.tradingview.com/script/yZzJpOGE-Moody-s-modified-V6-CM-Laguerre-PPO-Rank-Mkt-Tops-Bottoms
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : CM Laguerre PPO Rank Tops Bottoms_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine percentrank (previous len values <= current) and Laguerre
 *   filter hand-rolled; columns as histograms.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('CM Laguerre PPO Rank Tops Bottoms_TV', 'lower', { decimals: 1 });
const myPctile = input.number('Extreme Percentile', 90, { min: 1, max: 100 });
const myWrnPctile = input.number('Warning Percentile', 70, { min: 1, max: 100 });
const myShortG = input.number('PPO Short', 0.4, { min: 0, max: 1, step: 0.05 });
const myLongG = input.number('PPO Long', 0.8, { min: 0, max: 1, step: 0.05 });
const myLkbT = input.number('Lookback Tops', 200, { min: 1, max: 2000 });
const myLkbB = input.number('Lookback Bottoms', 200, { min: 1, max: 2000 });
const myShowLine = input.boolean('Show Threshold Line', true);
const myShowWarn = input.boolean('Show Warning Line', true);
const myN = close.length;
const myHl2 = close.map((_c, _i) => (high[_i] + low[_i]) / 2);
// Pine lag(g, p): four-pole Laguerre filter, nz() of the previous state is 0 on the first bar
const myLaguerre = (_g) => {
	let myL0 = 0, myL1 = 0, myL2 = 0, myL3 = 0;
	return myHl2.map(_p => {
		const myN0 = (1 - _g) * _p + _g * myL0;
		const myN1 = -_g * myN0 + myL0 + _g * myL1;
		const myN2 = -_g * myN1 + myL1 + _g * myL2;
		const myN3 = -_g * myN2 + myL2 + _g * myL3;
		myL0 = myN0; myL1 = myN1; myL2 = myN2; myL3 = myN3;
		return (myN0 + 2 * myN1 + 2 * myN2 + myN3) / 6;
	});
};
const myLmas = myLaguerre(myShortG);
const myLmal = myLaguerre(myLongG);
const myPpoT = myLmas.map((_s, _i) => myLmal[_i] === 0 ? null : (_s - myLmal[_i]) / myLmal[_i] * 100);
const myPpoB = myLmas.map((_s, _i) => myLmal[_i] === 0 ? null : (myLmal[_i] - _s) / myLmal[_i] * 100);
// ta.percentrank(src, len): share of the previous len values that are <= the current value
const myRank = (_s, _len) => _s.map((_v, _i) => {
	if (_i < _len || _v === null) return null;
	let myCount = 0;
	for (let myK = 1; myK <= _len; myK += 1) { const myV = _s[_i - myK]; if (myV === null) return null; if (myV <= _v) myCount += 1; }
	return myCount / _len * 100;
});
const myRankT = myRank(myPpoT, myLkbT);
const myRankB = myRank(myPpoB, myLkbB).map(_v => _v === null ? null : _v * -1);
const myPctileB = -myPctile;
const myWrnB = -myWrnPctile;
const myColT = myRankT.map(_r => _r === null ? 'gray' : (_r >= myPctile ? 'red' : (_r >= myWrnPctile ? 'orange' : 'gray')));
const myColB = myRankB.map(_r => _r === null ? 'silver' : (_r <= myPctileB ? 'lime' : (_r <= myWrnB ? 'green' : 'silver')));
const myEmpty = () => close.map(() => null);
paint(myRankT, { name: 'Percentile Rank Tops', style: 'histogram', color: myColT, thickness: 2 });
paint(myShowLine ? horizontal_line(myPctile) : myEmpty(), { name: 'Extreme Line Tops', color: 'red', thickness: 2 });
paint(myShowWarn ? horizontal_line(myWrnPctile) : myEmpty(), { name: 'Warning Line Tops', color: 'orange', thickness: 2 });
paint(myRankB, { name: 'Percentile Rank Bottoms', style: 'histogram', color: myColB, thickness: 2 });
paint(myShowLine ? horizontal_line(myPctileB) : myEmpty(), { name: 'Extreme Line Bottoms', color: 'lime', thickness: 2 });
paint(myShowWarn ? horizontal_line(myWrnB) : myEmpty(), { name: 'Warning Line Bottoms', color: 'green', thickness: 2 });
paint(horizontal_line(0), { name: 'Zero Line', color: 'gray', thickness: 1 });
register_signal(myRankT.map(_r => _r !== null && _r >= myPctile), 'Top Extreme Signal');
register_signal(myRankT.map(_r => _r !== null && _r >= myWrnPctile && _r < myPctile), 'Top Warning Signal');
register_signal(myRankB.map(_r => _r !== null && _r <= myPctileB), 'Bottom Extreme Signal');
register_signal(myRankB.map(_r => _r !== null && _r <= myWrnB && _r > myPctileB), 'Bottom Warning Signal');
