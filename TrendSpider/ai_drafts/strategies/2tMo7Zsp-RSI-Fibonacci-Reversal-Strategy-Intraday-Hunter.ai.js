describe_indicator('Top and Bottom Hunter Pro', 'price');

// NOTE: this is a best-effort conversion of a Pine Script strategy into
// a TrendSpider indicator. Strategy order execution (strategy.entry,
// strategy.close_all) is not available in Custom JS indicators, so
// buy/sell conditions are exposed as signals (via register_signal) and
// as labels/arrows on the chart, instead of actually placing trades.

const fibTab = input.tab('Fibonacci Settings');
const myFib0 = fibTab.number('Fib Level 0.382', 0.382, { min: 0, max: 1, step: 0.001 });
const myFib1 = fibTab.number('Fib Level 0.618', 0.618, { min: 0, max: 1, step: 0.001 });

const rsiTab = input.tab('RSI Settings');
const myRsiLength = rsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiOverbought = rsiTab.number('RSI Overbought', 70, { min: 1, max: 99 });
const myRsiOversold = rsiTab.number('RSI Oversold', 30, { min: 1, max: 99 });

const sessionTab = input.tab('Trading Sessions');
const mySession1 = sessionTab.text('Session 1 (HHMM-HHMM)', '1000-1130');
const mySession2 = sessionTab.text('Session 2 (HHMM-HHMM)', '1330-1510');
const myShowSessionBg = sessionTab.boolean('Highlight Sessions', true);

const visualTab = input.tab('Visual Settings');
const myShowSignals = visualTab.boolean('Show Buy/Sell Labels', true);
const myShowBarColors = visualTab.boolean('Color Bars', true);

// Fibonacci range based on 2-bar high/low
const myHH = highest(high, 2);
const myLL = lowest(low, 2);
const myFibRange = sub(myHH, myLL);

const myFibLevel0 = sub(myHH, mult(myFibRange, myFib0));
const myFibLevel1 = sub(myHH, mult(myFibRange, myFib1));

const myRsi = rsi(close, myRsiLength);

// Parses a "HHMM-HHMM" session string into { startMinutes, endMinutes }
function myParseSession(_sessionText) {
	const myParts = _sessionText.split('-');
	assert(myParts.length === 2, `Invalid session format: "${_sessionText}"`);
	const myStart = parseInt(myParts[0], 10);
	const myEnd = parseInt(myParts[1], 10);
	const myStartMinutes = Math.floor(myStart / 100) * 60 + (myStart % 100);
	const myEndMinutes = Math.floor(myEnd / 100) * 60 + (myEnd % 100);
	return { startMinutes: myStartMinutes, endMinutes: myEndMinutes };
}

const mySession1Parsed = myParseSession(mySession1);
const mySession2Parsed = myParseSession(mySession2);

function myIsInSession(_minutesOfDay, _sessionParsed) {
	return _minutesOfDay >= _sessionParsed.startMinutes && _minutesOfDay <= _sessionParsed.endMinutes;
}

// Determine, for every candle, whether it falls into either trading session
const myInTradingTime = time.map(_myTimestamp => {
	const myParsedTime = time_of(_myTimestamp);
	const myMinutesOfDay = myParsedTime.hours * 60 + myParsedTime.minutes;
	return myIsInSession(myMinutesOfDay, mySession1Parsed) || myIsInSession(myMinutesOfDay, mySession2Parsed);
});

// Crossover / crossunder of RSI vs oversold / overbought levels
const myBuyCondition = for_every(myRsi, close, myFibLevel1, (_rsiVal, _closeVal, _fibVal, _prev, _index) => {
	if (_index === 0 || myRsi[_index - 1] === null || _rsiVal === null) return false;
	const myCrossedOver = myRsi[_index - 1] <= myRsiOversold && _rsiVal > myRsiOversold;
	return myCrossedOver && _closeVal > _fibVal && myInTradingTime[_index];
});

const mySellCondition = for_every(myRsi, close, myFibLevel0, (_rsiVal, _closeVal, _fibVal, _prev, _index) => {
	if (_index === 0 || myRsi[_index - 1] === null || _rsiVal === null) return false;
	const myCrossedUnder = myRsi[_index - 1] >= myRsiOverbought && _rsiVal < myRsiOverbought;
	return myCrossedUnder && _closeVal < _fibVal && myInTradingTime[_index];
});

// Bar coloring: bullish above fib 0.618, bearish below fib 0.382, otherwise neutral
const myBarColors = for_every(close, myFibLevel0, myFibLevel1, (_closeVal, _fib0, _fib1) => {
	if (_closeVal > _fib1) return '#00c88c';
	if (_closeVal < _fib0) return '#ff5252';
	return '#82828f';
});

color_candles(myShowBarColors ? myBarColors : constants.empty_series);

paint(myFibLevel0, { name: 'Fib0382', color: '#e74c3c', thickness: 2 });
paint(myFibLevel1, { name: 'Fib0618', color: '#2ecc71', thickness: 2 });

// Session background highlight, painted as a sparse marker line (visual approximation,
// since there is no native session-background paint type in Custom JS)
const mySessionBgSeries = myInTradingTime.map((_myFlag, _myIndex) => (myShowSessionBg && _myFlag) ? close[_myIndex] : null);
paint(mySessionBgSeries, { name: 'SessionActive', style: 'labels_below', color: '#7ee8fa' });

const myBuyLabels = myBuyCondition.map((_myFlag, _myIndex) => (myShowSignals && _myFlag) ? low[_myIndex] : null);
const mySellLabels = mySellCondition.map((_myFlag, _myIndex) => (myShowSignals && _myFlag) ? high[_myIndex] : null);

paint(myBuyLabels, { name: 'BuySignal', style: 'labels_below', color: '#00c88c' });
paint(mySellLabels, { name: 'SellSignal', style: 'labels_above', color: '#ff5252' });

register_signal(myBuyCondition, 'Buy Condition');
register_signal(mySellCondition, 'Sell Condition (Close All)');