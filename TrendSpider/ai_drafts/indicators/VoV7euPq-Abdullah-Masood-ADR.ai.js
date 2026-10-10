describe_indicator('Universal OANDA ADR Panel', 'lower');

// Fetches daily OHLC data for the current ticker. request.history
// returns arrays aligned by index, oldest first, so .at(-1) is
// yesterday's completed daily candle relative to current data.
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, "Error fetching daily data: " + myDailyData.error);

const myDailyHigh = myDailyData.high;
const myDailyLow = myDailyData.low;
const myDailyCount = myDailyHigh.length;

// Need at least 7 completed daily candles (today + 6 previous days)
// to be able to compute yH1..yH6. If not enough data, we bail out
// with null values but keep the same output shape.
const myHasEnoughData = myDailyCount >= 7;

// Daily candle at index (length-1) is today's (forming) candle, so
// "yesterday" (offset 1) is index (length-2), offset N is index (length-1-N).
function myDailyOffset(_series, _offset) {
	const myIndex = myDailyCount - 1 - _offset;
	return myIndex >= 0 ? _series[myIndex] : null;
}

const myH1 = myDailyOffset(myDailyHigh, 1);
const myL1 = myDailyOffset(myDailyLow, 1);
const myH2 = myDailyOffset(myDailyHigh, 2);
const myL2 = myDailyOffset(myDailyLow, 2);
const myH3 = myDailyOffset(myDailyHigh, 3);
const myL3 = myDailyOffset(myDailyLow, 3);
const myH4 = myDailyOffset(myDailyHigh, 4);
const myL4 = myDailyOffset(myDailyLow, 4);
const myH5 = myDailyOffset(myDailyHigh, 5);
const myL5 = myDailyOffset(myDailyLow, 5);
const myH6 = myDailyOffset(myDailyHigh, 6);
const myL6 = myDailyOffset(myDailyLow, 6);

const myYesterdayRange = myHasEnoughData ? (myH1 - myL1) : null;
const myRange2 = myHasEnoughData ? (myH2 - myL2) : null;
const myRange3 = myHasEnoughData ? (myH3 - myL3) : null;
const myRange4 = myHasEnoughData ? (myH4 - myL4) : null;
const myRange5 = myHasEnoughData ? (myH5 - myL5) : null;
const myRange6 = myHasEnoughData ? (myH6 - myL6) : null;

const myAdr3 = myHasEnoughData ? ((myRange2 + myRange3 + myRange4) / 3.0) : null;
const myAdr5 = myHasEnoughData ? ((myRange2 + myRange3 + myRange4 + myRange5 + myRange6) / 5.0) : null;

const myBreak3 = myHasEnoughData ? (myYesterdayRange > myAdr3) : false;
const myBreak5 = myHasEnoughData ? (myYesterdayRange > myAdr5) : false;

function myFormat(_value) {
	if (_value === null || _value === undefined || isNaN(_value)) return "N/A";
	return "$" + Math.round(_value).toString();
}

function myStatusText(_isBreak) {
	return _isBreak ? "BREAK" : "NO BREAK";
}

function myStatusColor(_isBreak) {
	return _isBreak ? '#cc0000' : '#1f8f3a';
}

const myHeaderColor = '#1f4e79';
const myInputRowColor = '#373737';

// Compact panel reproducing the Pine table layout
paint_overlay('ADRPanel', { position: 'top_right' }, {
	rows: [
		{
			cells: [
				{ text: current.ticker, color: 'white', background_color: myHeaderColor },
				{ text: 'VALUE', color: 'white', background_color: myHeaderColor },
				{ text: 'STATUS', color: 'white', background_color: myHeaderColor }
			]
		},
		{
			cells: [
				{ text: 'YESTERDAY RANGE' },
				{ text: myFormat(myYesterdayRange) },
				{ text: '-' }
			]
		},
		{
			cells: [
				{ text: '3D ADR' },
				{ text: myFormat(myAdr3) },
				{ text: myStatusText(myBreak3), color: 'white', background_color: myStatusColor(myBreak3) }
			]
		},
		{
			cells: [
				{ text: '5D ADR' },
				{ text: myFormat(myAdr5) },
				{ text: myStatusText(myBreak5), color: 'white', background_color: myStatusColor(myBreak5) }
			]
		},
		{
			cells: [
				{ text: '3D INPUTS', color: 'white', background_color: myInputRowColor },
				{ text: myFormat(myRange2) + " + " + myFormat(myRange3) + " + " + myFormat(myRange4), color: 'white', background_color: myInputRowColor },
				{ text: '', background_color: myInputRowColor }
			]
		},
		{
			cells: [
				{ text: '5D INPUTS', color: 'white', background_color: myInputRowColor },
				{ text: myFormat(myRange2) + " + " + myFormat(myRange3) + " + " + myFormat(myRange4) + " + " + myFormat(myRange5) + " + " + myFormat(myRange6), color: 'white', background_color: myInputRowColor },
				{ text: '', background_color: myInputRowColor }
			]
		}
	]
});

// Data window / scanner-friendly lines (constant values each render,
// since this panel reflects "current" state, not historical per-candle)
paint(series_of(myYesterdayRange), { name: 'YesterdayRange', color: '#4DA3FF' });
paint(series_of(myAdr3), { name: 'ADR3', color: '#26A69A' });
paint(series_of(myAdr5), { name: 'ADR5', color: '#EF5350' });

// Signals usable in Scanners, Alerts, Strategy Tester
register_signal(series_of(myBreak3), "3D ADR Break");
register_signal(series_of(myBreak5), "5D ADR Break");