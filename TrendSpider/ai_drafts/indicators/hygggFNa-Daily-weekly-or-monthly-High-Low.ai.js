// This indicator approximates a repainting "HTF High/Low" overlay.
// NOTE: The original Pine script uses request.security(...,
// barmerge.lookahead_on), which deliberately leaks future bars'
// data into the past (classic repainting lookahead). The platform
// explicitly forbids using future data when computing past values,
// so a byte-for-byte reproduction of that non-causal behavior is
// not possible here. Instead, this script computes a "live running"
// High/Low of the current (still forming) Daily/Weekly/Monthly
// period using the chart's own price data, which updates in real
// time as the period progresses, without looking into the future.
// This is the closest causal equivalent of what the Pine script
// shows live on an active, unclosed higher-timeframe period.
describe_indicator('HTF High Low (Live, Causal)', 'price');

const myShowChart = input.boolean('Show On Chart', true);
const myTimeframeOption = input.select('Timeframe', 'Daily', ['Daily', 'Weekly', 'Monthly']);

// Builds a grouping key per candle, identifying which HTF period
// (day / ISO week / month) a given candle belongs to.
const myGroupKeys = time.map(myTimestamp => {
	const myParts = time_of(myTimestamp);
	if (myTimeframeOption === 'Daily') {
		return `${myParts.year}-${myParts.dayOfYear}`;
	}
	else if (myTimeframeOption === 'Weekly') {
		return `${myParts.year}-W${myParts.weekOfYear}`;
	}
	else {
		return `${myParts.year}-M${myParts.month}`;
	}
});

const myHtfHigh = series_of(null);
const myHtfLow = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewPeriod = myIndex === 0 || myGroupKeys[myIndex] !== myGroupKeys[myIndex - 1];

	if (myNewPeriod) {
		myHtfHigh[myIndex] = high[myIndex];
		myHtfLow[myIndex] = low[myIndex];
	}
	else {
		myHtfHigh[myIndex] = Math.max(myHtfHigh[myIndex - 1], high[myIndex]);
		myHtfLow[myIndex] = Math.min(myHtfLow[myIndex - 1], low[myIndex]);
	}
}

paint(myShowChart ? myHtfHigh : constants.empty_series, { name: 'HTF Current High', color: '#8C9C8D', style: 'line' });
paint(myShowChart ? myHtfLow : constants.empty_series, { name: 'HTF Current Low', color: '#CEB7B7', style: 'line' });

// Scanner/Strategy friendly signals: price breaking the running
// HTF high or low of the currently forming period.
const myBreakAboveHtfHigh = for_every(close, myHtfHigh, (_myClose, _myHigh) => _myClose > _myHigh);
const myBreakBelowHtfLow = for_every(close, myHtfLow, (_myClose, _myLow) => _myClose < _myLow);

register_signal(myBreakAboveHtfHigh, 'Close Above HTF High');
register_signal(myBreakBelowHtfLow, 'Close Below HTF Low');