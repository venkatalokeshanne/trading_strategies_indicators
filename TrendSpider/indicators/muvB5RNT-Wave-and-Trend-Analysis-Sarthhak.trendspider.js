/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : WaveTrend with Crosses [Sarthhak]
 * Author       : alphamale1993
 * Source URL   : https://www.tradingview.com/script/muvB5RNT-Wave-and-Trend-Analysis-Sarthhak
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : WaveTrend with Crosses [Sarthhak]_TV
 *
 * The Pine original, in words: WaveTrend: WT1 = EMA(21) of the channel index of hlc3, WT2 = SMA(4) of WT1, with
 *   OB/OS levels and dots on crosses.
 *
 * Deviations from the original: cross bars recoloured; dots drawn as a dotted marker.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('WaveTrend with Crosses [Sarthhak]_TV', 'lower');

// Mirrors the Pine Script "WaveTrend with Crosses [Sarthhak]" indicator.
const myChannelLength = input.number('Channel Length', 10, { min: 1, max: 100 });
const myAverageLength = input.number('Average Length', 21, { min: 1, max: 100 });
const myOverBought1 = input.number('Over Bought Level 1', 60, { min: -100, max: 100 });
const myOverBought2 = input.number('Over Bought Level 2', 53, { min: -100, max: 100 });
const myOverSold1 = input.number('Over Sold Level 1', -60, { min: -100, max: 100 });
const myOverSold2 = input.number('Over Sold Level 2', -53, { min: -100, max: 100 });

const myAp = hlc3;
const myEsa = ema(myAp, myChannelLength);
const myAbsDiff = for_every(myAp, myEsa, (_ap, _esa) => _esa === null ? null : Math.abs(_ap - _esa));
const myD = ema(myAbsDiff, myChannelLength);
const myCi = for_every(myAp, myEsa, myD, (_ap, _esa, _d) => _esa === null || !_d ? null : (_ap - _esa) / (0.015 * _d));
const myTci = ema(myCi, myAverageLength);

const myWt1 = myTci;
const myWt2 = sma(myWt1, 4);

// Detects crosses (either direction), equivalent to ta.cross(wt1, wt2)
const myCrossSignal = for_every(myWt1, myWt2, (_w1, _w2, _prev, _index) => {
	if (_index === 0) return false;
	const myDiffNow = _w1 - _w2;
	const myDiffPrevW1 = close[_index - 1] === close[_index - 1] ? myWt1[_index - 1] : null;
	const myDiffPrevW2 = myWt2[_index - 1];
	if (myDiffPrevW1 === null || myDiffPrevW2 === null || myDiffPrevW1 === undefined || myDiffPrevW2 === undefined) return false;
	const myDiffPrev = myDiffPrevW1 - myDiffPrevW2;
	return (myDiffPrev <= 0 && myDiffNow > 0) || (myDiffPrev >= 0 && myDiffNow < 0);
});

const myCrossUp = for_every(myWt1, myWt2, myCrossSignal, (_w1, _w2, _cross) => _cross && (_w2 - _w1) <= 0);
const myCrossDown = for_every(myWt1, myWt2, myCrossSignal, (_w1, _w2, _cross) => _cross && (_w2 - _w1) > 0);

// Cross markers plotted at wt2 value, null otherwise
const myCrossMarker = for_every(myWt2, myCrossSignal, (_w2, _cross) => _cross ? _w2 : null);
const myCrossColor = for_every(myWt2, myWt1, (_w2, _w1) => (_w2 - _w1) > 0 ? 'red' : 'lime');

paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'line' });
paint(horizontal_line(myOverBought1), { name: 'Over Bought 1', color: 'red', style: 'line' });
paint(horizontal_line(myOverSold1), { name: 'Over Sold 1', color: 'green', style: 'line' });
paint(horizontal_line(myOverBought2), { name: 'Over Bought 2', color: 'red', style: 'line' });
paint(horizontal_line(myOverSold2), { name: 'Over Sold 2', color: 'green', style: 'line' });

paint(myWt1, { name: 'WT1', color: 'green', style: 'line' });
paint(myWt2, { name: 'WT2', color: 'red', style: 'line' });
paint(sub(myWt1, myWt2), { name: 'WT1 Minus WT2', color: 'rgba(0,0,255,0.2)', style: 'column' });

// Pine's style_circles is not available; approximated with a dotted marker line.
paint(myCrossMarker, { name: 'Cross Marker', color: myCrossColor, style: 'dotted', thickness: 6 });

// barcolor equivalent
const myBarColor = for_every(myWt2, myWt1, myCrossSignal, (_w2, _w1, _cross) => {
	if (!_cross) return null;
	return (_w2 - _w1) > 0 ? 'aqua' : 'yellow';
});
color_candles(myBarColor);

register_signal(myCrossUp, 'WaveTrend Bullish Cross');
register_signal(myCrossDown, 'WaveTrend Bearish Cross');
