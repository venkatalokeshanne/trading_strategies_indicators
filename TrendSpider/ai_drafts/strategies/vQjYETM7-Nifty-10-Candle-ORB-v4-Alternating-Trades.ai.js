describe_indicator('Nifty ORB Alternating Signals', 'price');

// --- Inputs (grouped for readability) ---
const riskTab = input.tab('Risk');
const myTpPercent = riskTab.number('Profit Target (%)', 1.0, { min: 0.1, max: 50, step: 0.1 });
const mySlPercent = riskTab.number('Stop Loss (%)', 0.5, { min: 0.1, max: 50, step: 0.1 });

const rangeTab = input.tab('Range');
const myNumCandles = rangeTab.number('Number of Opening Candles', 10, { min: 1, max: 200 });

const timeTab = input.tab('Time');
const exitRow = timeTab.row();
const myExitHour = exitRow.number('Exit Hour (24h)', 15, { min: 0, max: 23 });
const myExitMinute = exitRow.number('Exit Minute', 0, { min: 0, max: 59 });
const myLastTradeHour = timeTab.number('Last Entry Hour (24h)', 15, { min: 0, max: 23 });

assert(!isNaN(current.resolution), 'This strategy only makes sense on an intraday time frame');

const myCount = close.length;

// Per-candle session id, used to detect "new day"
const mySessionIds = time.map(_t => bar_at(_t).session);

// Output series
const myOrbHigh = series_of(null);
const myOrbLow = series_of(null);
const myLongEntry = series_of(false);
const myShortEntry = series_of(false);
const myLongExit = series_of(false);
const myShortExit = series_of(false);
const myEodClose = series_of(false);

// State variables (sequential simulation, mirroring the Pine Script logic)
let mySessionHigh = null;
let mySessionLow = null;
let myCandleIdx = 0;
let myLastTradeType = 0; // 0 none, 1 long, -1 short
let myPositionSize = 0;  // 0, 1 (long), -1 (short)
let myPositionAvgPrice = null;

for (let myIndex = 0; myIndex < myCount; myIndex += 1) {
	const myIsNewDay = myIndex === 0 || mySessionIds[myIndex] !== mySessionIds[myIndex - 1];

	if (myIsNewDay) {
		mySessionHigh = null;
		mySessionLow = null;
		myCandleIdx = 0;
		myLastTradeType = 0;
	}

	// --- Range calculation ---
	if (myCandleIdx < myNumCandles) {
		myCandleIdx += 1;
		mySessionHigh = (mySessionHigh === null) ? high[myIndex] : Math.max(mySessionHigh, high[myIndex]);
		mySessionLow = (mySessionLow === null) ? low[myIndex] : Math.min(mySessionLow, low[myIndex]);
	}

	if (myCandleIdx >= myNumCandles) {
		myOrbHigh[myIndex] = mySessionHigh;
		myOrbLow[myIndex] = mySessionLow;
	}

	// --- Time logic ---
	const myTimeInfo = time_of(time[myIndex]);
	const myCurrentTime = myTimeInfo.hours * 100 + myTimeInfo.minutes;
	const myIsExitTime = myCurrentTime >= (myExitHour * 100 + myExitMinute);
	const myCanEnter = myCurrentTime < (myLastTradeHour * 100);

	const myCanTrade = myCandleIdx >= myNumCandles && myPositionSize === 0 && myCanEnter && !myIsExitTime;

	// --- Crossover / crossunder detection vs ORB levels ---
	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;
	const myCrossoverHigh = myCanTrade && myPrevClose !== null && myPrevClose <= mySessionHigh && close[myIndex] > mySessionHigh;
	const myCrossunderLow = myCanTrade && myPrevClose !== null && myPrevClose >= mySessionLow && close[myIndex] < mySessionLow;

	const myLongCondition = myCrossoverHigh && (myLastTradeType <= 0);
	const myShortCondition = myCrossunderLow && (myLastTradeType >= 0);

	if (myLongCondition) {
		myPositionSize = 1;
		myPositionAvgPrice = close[myIndex];
		myLastTradeType = 1;
		myLongEntry[myIndex] = true;
	}
	else if (myShortCondition) {
		myPositionSize = -1;
		myPositionAvgPrice = close[myIndex];
		myLastTradeType = -1;
		myShortEntry[myIndex] = true;
	}

	// --- Percentage based exits (checked same bar, like Pine's strategy.exit) ---
	if (myPositionSize > 0) {
		const myLongTp = myPositionAvgPrice * (1 + myTpPercent / 100);
		const myLongSl = myPositionAvgPrice * (1 - mySlPercent / 100);
		if (high[myIndex] >= myLongTp || low[myIndex] <= myLongSl) {
			myLongExit[myIndex] = true;
			myPositionSize = 0;
			myPositionAvgPrice = null;
		}
	}
	else if (myPositionSize < 0) {
		const myShortTp = myPositionAvgPrice * (1 - myTpPercent / 100);
		const myShortSl = myPositionAvgPrice * (1 + mySlPercent / 100);
		if (low[myIndex] <= myShortTp || high[myIndex] >= myShortSl) {
			myShortExit[myIndex] = true;
			myPositionSize = 0;
			myPositionAvgPrice = null;
		}
	}

	// --- Forced EOD square off ---
	if (myIsExitTime && myPositionSize !== 0) {
		myEodClose[myIndex] = true;
		myPositionSize = 0;
		myPositionAvgPrice = null;
	}
}

// --- Plotting ORB High/Low ---
paint(myOrbHigh, { name: 'ORB High', color: '#2ca599', thickness: 2, style: 'ladder' });
paint(myOrbLow, { name: 'ORB Low', color: '#ee5451', thickness: 2, style: 'ladder' });

// --- Scanner/Strategy/Alert signals ---
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myLongExit, 'Long Exit TP SL');
register_signal(myShortExit, 'Short Exit TP SL');
register_signal(myEodClose, 'EOD Square Off');