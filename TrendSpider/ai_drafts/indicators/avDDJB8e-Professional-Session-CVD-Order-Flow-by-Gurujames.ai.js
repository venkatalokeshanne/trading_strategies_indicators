describe_indicator('Session CVD (Order Flow)', 'lower', { decimals: 0 });

// =========================================================================
// INPUTS
// =========================================================================
const dataTab = input.tab('Data Configuration');
// Shortened title: original was too long and triggered an
// "input(): name is too lengthy" platform error.
const myLtfInput = dataTab.select('Intrabar Timeframe', '1', constants.time_frames);
const myResetMode = dataTab.select('Session Reset Mode', 'Daily', ['Daily', 'Weekly', 'Continuous']);

const visualsTab = input.tab('Visuals and Labels');
const myShowLabels = visualsTab.boolean('Show Extreme Labels', true);

// =========================================================================
// FETCH LOWER TIMEFRAME DATA
// (TrendSpider has no request.security_lower_tf; we approximate it by
// fetching the raw lower timeframe history via request.history() and then
// bucketing those candles into the current chart's bars)
// =========================================================================
const myLtfData = await request.history(current.ticker, myLtfInput, { ext_session: true });
assert(!myLtfData.error, `Error fetching intrabar data: "${myLtfData.error}"`);

// Compute per-ltf-candle delta, reproducing Pine's get_intrabar_delta() logic
const myLtfDeltas = [];
for (let myI = 0; myI < myLtfData.close.length; myI += 1) {
	const myClose = myLtfData.close[myI];
	const myOpen = myLtfData.open[myI];
	const myVolume = myLtfData.volume[myI];
	const myPrevClose = myI > 0 ? myLtfData.close[myI - 1] : myClose;

	let myBuyVol = 0;
	let mySellVol = 0;

	if (myClose > myOpen) {
		myBuyVol = myVolume;
	}
	else if (myClose === myOpen && myClose >= myPrevClose) {
		myBuyVol = myVolume;
	}

	if (myClose < myOpen) {
		mySellVol = myVolume;
	}
	else if (myClose === myOpen && myClose < myPrevClose) {
		mySellVol = myVolume;
	}

	myLtfDeltas.push(myBuyVol - mySellVol);
}

// =========================================================================
// SESSION ACCUMULATION, RESET LOGIC AND CANDLE RECONSTRUCTION
// =========================================================================
const myCvdOpen = series_of(null);
const myCvdHigh = series_of(null);
const myCvdLow = series_of(null);
const myCvdClose = series_of(null);

let myCurrentCvd = 0.0;
let myLtfPointer = 0;
let myPrevDayKey = null;
let myPrevWeekKey = null;

for (let myBarIndex = 0; myBarIndex < close.length; myBarIndex += 1) {
	const myBarStart = time[myBarIndex];
	const myBarEnd = myBarIndex + 1 < time.length ? time[myBarIndex + 1] : Infinity;

	// Determine session reset condition, mirroring ta.change(time("D")) / time("W")
	const myTimeInfo = time_of(myBarStart);
	const myDayKey = `${myTimeInfo.year}-${myTimeInfo.dayOfYear}`;
	const myWeekKey = `${myTimeInfo.year}-${myTimeInfo.weekOfYear}`;

	let myIsNewSession = false;
	if (myResetMode === 'Daily') {
		myIsNewSession = myPrevDayKey !== null && myDayKey !== myPrevDayKey;
	}
	else if (myResetMode === 'Weekly') {
		myIsNewSession = myPrevWeekKey !== null && myWeekKey !== myPrevWeekKey;
	}

	myPrevDayKey = myDayKey;
	myPrevWeekKey = myWeekKey;

	if (myIsNewSession) {
		myCurrentCvd = 0.0;
	}

	const myCvdOpenValue = myCurrentCvd;
	let myTempCvd = myCurrentCvd;
	let myCvdHighValue = myCurrentCvd;
	let myCvdLowValue = myCurrentCvd;

	// Walk the ltf deltas belonging to this higher timeframe candle
	while (myLtfPointer < myLtfData.time.length && myLtfData.time[myLtfPointer] < myBarStart) {
		myLtfPointer += 1;
	}

	let myScanPointer = myLtfPointer;
	while (myScanPointer < myLtfData.time.length && myLtfData.time[myScanPointer] < myBarEnd) {
		myTempCvd += myLtfDeltas[myScanPointer];
		myCvdHighValue = Math.max(myCvdHighValue, myTempCvd);
		myCvdLowValue = Math.min(myCvdLowValue, myTempCvd);
		myScanPointer += 1;
	}

	myLtfPointer = myScanPointer;
	myCurrentCvd = myTempCvd;

	myCvdOpen[myBarIndex] = myCvdOpenValue;
	myCvdHigh[myBarIndex] = myCvdHighValue;
	myCvdLow[myBarIndex] = myCvdLowValue;
	myCvdClose[myBarIndex] = myCurrentCvd;
}

// =========================================================================
// COLOR, SWINGS AND SIGNALS
// =========================================================================
const myBullBearColor = for_every(myCvdClose, myCvdOpen, (_myClose, _myOpen) => _myClose >= _myOpen ? '#009688' : '#f44336');

const myHighest10 = highest(myCvdClose, 10);
const myLowest10 = lowest(myCvdClose, 10);
const myIsSwingHigh = for_every(myCvdClose, myHighest10, (_myClose, _myHigh) => _myClose === _myHigh);
const myIsSwingLow = for_every(myCvdClose, myLowest10, (_myClose, _myLow) => _myClose === _myLow);

register_signal(for_every(myCvdClose, myCvdOpen, (_myClose, _myOpen) => _myClose >= _myOpen), 'Bullish Delta Bar');
register_signal(for_every(myCvdClose, myCvdOpen, (_myClose, _myOpen) => _myClose < _myOpen), 'Bearish Delta Bar');
register_signal(myIsSwingHigh, 'Delta Swing High');
register_signal(myIsSwingLow, 'Delta Swing Low');

// =========================================================================
// PLOTTING
// (TrendSpider's Custom JS API has no OHLC "candlestick" plot primitive for
// lower indicators, so we approximate the CVD candle with a close line
// colored bull/bear, plus thin high/low reference lines)
// =========================================================================
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'dotted', thickness: 1 });

const myHighLinePainted = paint(myCvdHigh, { name: 'Cvd High', color: 'silver', style: 'dotted', thickness: 1 });
const myLowLinePainted = paint(myCvdLow, { name: 'Cvd Low', color: 'silver', style: 'dotted', thickness: 1 });
const myCloseLinePainted = paint(myCvdClose, { name: 'Cvd Close', color: myBullBearColor, style: 'line', thickness: 2 });

// Place labels on swing highs/lows, matching the Pine label.new() calls
if (myShowLabels) {
	for (let myLabelIndex = 0; myLabelIndex < close.length; myLabelIndex += 1) {
		if (myIsSwingHigh[myLabelIndex]) {
			paint_label_at_line(myHighLinePainted, myLabelIndex, String(Math.round(myCvdHigh[myLabelIndex])), {
				color: '#ffffff',
				background_color: '#009688',
				vertical_align: 'bottom'
			});
		}
		if (myIsSwingLow[myLabelIndex]) {
			paint_label_at_line(myLowLinePainted, myLabelIndex, String(Math.round(myCvdLow[myLabelIndex])), {
				color: '#ffffff',
				background_color: '#f44336',
				vertical_align: 'top'
			});
		}
	}
}