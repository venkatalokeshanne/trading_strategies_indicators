describe_indicator('WaveTrend with Crosses', 'lower');

// Inputs matching the original Pine Script
const myChannelLength = input.number('Channel Length', 10, { min: 1, max: 200 });
const myAverageLength = input.number('Average Length', 21, { min: 1, max: 200 });
const myOverBought1 = input.number('Over Bought Level 1', 60, { min: -100, max: 100 });
const myOverBought2 = input.number('Over Bought Level 2', 53, { min: -100, max: 100 });
const myOverSold1 = input.number('Over Sold Level 1', -60, { min: -100, max: 100 });
const myOverSold2 = input.number('Over Sold Level 2', -53, { min: -100, max: 100 });

// WaveTrend core math, replicating Pine Script exactly
const myAp = hlc3;
const myEsa = ema(myAp, myChannelLength);
const myD = ema(for_every(myAp, myEsa, (_ap, _esa) => Math.abs(_ap - _esa)), myChannelLength);
const myCi = for_every(myAp, myEsa, myD, (_ap, _esa, _d) => (_ap - _esa) / (0.015 * _d));
const myTci = ema(myCi, myAverageLength);

const myWt1 = myTci;
const myWt2 = sma(myWt1, 4);

// Detect cross (ta.cross equivalent): sign change of (wt1 - wt2) between
// the previous bar and the current bar
const myCrossSignal = for_every(myWt1, myWt2, (_wt1, _wt2, _prev, _index) => {
	if (_index === 0) {
		return false;
	}
	const myCurrentDiff = _wt1 - _wt2;
	const myPreviousDiff = myWt1[_index - 1] - myWt2[_index - 1];
	return (myPreviousDiff <= 0 && myCurrentDiff > 0) || (myPreviousDiff >= 0 && myCurrentDiff < 0);
});

// Bearish cross: wt2 above wt1 (red); Bullish cross: wt2 below wt1 (lime)
const myBearishCross = for_every(myWt1, myWt2, myCrossSignal, (_wt1, _wt2, _cross) => _cross && (_wt2 - _wt1) > 0);
const myBullishCross = for_every(myWt1, myWt2, myCrossSignal, (_wt1, _wt2, _cross) => _cross && (_wt2 - _wt1) <= 0);

// Reference levels
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'line' });
paint(horizontal_line(myOverBought1), { name: 'Overbought One', color: 'red', style: 'line' });
paint(horizontal_line(myOverSold1), { name: 'Oversold One', color: 'green', style: 'line' });
paint(horizontal_line(myOverBought2), { name: 'Overbought Two', color: 'red', style: 'line' });
paint(horizontal_line(myOverSold2), { name: 'Oversold Two', color: 'green', style: 'line' });

// WaveTrend lines
paint(myWt1, { name: 'WT1', color: '#26A69A', thickness: 2 });
paint(myWt2, { name: 'WT2', color: '#EF5350', thickness: 2 });

// Difference area (wt1 - wt2)
paint(sub(myWt1, myWt2), { name: 'WT Diff', color: 'rgba(66,135,245,0.2)', style: 'column' });

// Cross markers: colored circle at wt2 value, red for bearish, lime for bullish
const myCrossMarker = for_every(myWt2, myCrossSignal, (_wt2, _cross) => _cross ? _wt2 : null);
const myCrossColor = for_every(myBearishCross, _bear => _bear ? 'red' : 'lime');

paint(myCrossMarker, { name: 'Cross Marker', color: myCrossColor, style: 'dotted', thickness: 4 });

// Color the price candles on cross bars (aqua for bullish, yellow for bearish)
const myCandleColors = for_every(myBullishCross, myBearishCross, (_bull, _bear) => {
	if (_bull) {
		return 'aqua';
	}
	if (_bear) {
		return 'yellow';
	}
	return null;
});
color_candles(myCandleColors);

// Signals for Scanner, Alerts and Strategy Tester
register_signal(myBullishCross, 'Bullish Cross');
register_signal(myBearishCross, 'Bearish Cross');
register_signal(for_every(myWt1, _wt1 => _wt1 > myOverBought1), 'WT1 Above Overbought One');
register_signal(for_every(myWt1, _wt1 => _wt1 < myOverSold1), 'WT1 Below Oversold One');