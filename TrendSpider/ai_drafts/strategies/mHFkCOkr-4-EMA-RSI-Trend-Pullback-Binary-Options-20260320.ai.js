describe_indicator('4EMA and RSI Trend Pullback', 'price');

// EMA settings
const emaTab = input.tab('EMA Settings');
const myLen7 = emaTab.number('EMA 7 Fast', 7, { min: 1, max: 500 });
const myLen21 = emaTab.number('EMA 21 Slow', 21, { min: 1, max: 500 });
const myLen50 = emaTab.number('EMA 50 Trend', 50, { min: 1, max: 500 });
const myLen200 = emaTab.number('EMA 200 Macro', 200, { min: 1, max: 500 });

// RSI settings
const rsiTab = input.tab('RSI Settings');
const myRsiLen = rsiTab.number('RSI Length', 14, { min: 1, max: 500 });
const myRsiOverbought = rsiTab.number('RSI Overbought', 70, { min: 1, max: 100 });
const myRsiOversold = rsiTab.number('RSI Oversold', 30, { min: 1, max: 100 });
const myRsiMid = rsiTab.number('RSI Mid', 50, { min: 1, max: 100 });

// Core calculations
const myEma7 = ema(close, myLen7);
const myEma21 = ema(close, myLen21);
const myEma50 = ema(close, myLen50);
const myEma200 = ema(close, myLen200);
const myRsi = rsi(close, myRsiLen);

// Macro trend filter
const myBullishMacro = for_every(myEma50, myEma200, (_e50, _e200) => _e50 > _e200);
const myBearishMacro = for_every(myEma50, myEma200, (_e50, _e200) => _e50 < _e200);

// RSI confirmation filters
const myRsiLongOk = for_every(myRsi, _r => _r > myRsiMid && _r < myRsiOverbought);
const myRsiShortOk = for_every(myRsi, _r => _r < myRsiMid && _r > myRsiOversold);

// EMA 7/21 cross detection (equivalent of ta.crossover / ta.crossunder)
const myCrossOver = for_every(myEma7, myEma21, (_e7, _e21, _prev, _idx) => {
	if (_idx === 0) return false;
	return _e7 > _e21 && myEma7[_idx - 1] <= myEma21[_idx - 1];
});
const myCrossUnder = for_every(myEma7, myEma21, (_e7, _e21, _prev, _idx) => {
	if (_idx === 0) return false;
	return _e7 < _e21 && myEma7[_idx - 1] >= myEma21[_idx - 1];
});

// Entry triggers
const myLongTrigger = for_every(myCrossOver, myRsiLongOk, (_co, _ok) => _co && _ok);
const myShortTrigger = for_every(myCrossUnder, myRsiShortOk, (_cu, _ok) => _cu && _ok);

// Exit conditions
const myLongExit = for_every(myCrossUnder, close, myEma50, (_cu, _c, _e50) => _cu || _c < _e50);
const myShortExit = for_every(myCrossOver, close, myEma50, (_co, _c, _e50) => _co || _c > _e50);

// Final entry signals (macro filter applied)
const myLongEntrySignal = for_every(myBullishMacro, myLongTrigger, (_bull, _trig) => _bull && _trig);
const myShortEntrySignal = for_every(myBearishMacro, myShortTrigger, (_bear, _trig) => _bear && _trig);

// Position state simulation (to replicate strategy.position_size logic for exits)
// Since this is an indicator (not a strategy), we track a simple simulated
// position state bar-by-bar to know when "Exit Long" / "Exit Short" should fire,
// mirroring strategy.position_size > 0 / < 0 checks in the Pine script.
const myPositionState = series_of(0);
for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	let myPrevState = myPositionState[myIndex - 1] || 0;
	if (myPrevState === 0) {
		if (myLongEntrySignal[myIndex]) myPrevState = 1;
		else if (myShortEntrySignal[myIndex]) myPrevState = -1;
	}
	else if (myPrevState === 1) {
		if (myLongExit[myIndex]) myPrevState = 0;
	}
	else if (myPrevState === -1) {
		if (myShortExit[myIndex]) myPrevState = 0;
	}
	myPositionState[myIndex] = myPrevState;
}

const myLongExitSignal = for_every(myPositionState, myLongExit, (_state, _exit, _prev, _idx) => {
	const myPrevState = _idx > 0 ? myPositionState[_idx - 1] : 0;
	return myPrevState > 0 && _exit;
});
const myShortExitSignal = for_every(myPositionState, myShortExit, (_state, _exit, _prev, _idx) => {
	const myPrevState = _idx > 0 ? myPositionState[_idx - 1] : 0;
	return myPrevState < 0 && _exit;
});

// Perfect trend alignment for background-like reference
const myPerfectBull = for_every(myEma7, myEma21, myEma50, myEma200, (_e7, _e21, _e50, _e200) => _e7 > _e21 && _e21 > _e50 && _e50 > _e200);
const myPerfectBear = for_every(myEma7, myEma21, myEma50, myEma200, (_e7, _e21, _e50, _e200) => _e7 < _e21 && _e21 < _e50 && _e50 < _e200);

// Paint EMAs
paint(myEma7, { name: 'EMA7', color: '#2962ff', thickness: 1 });
paint(myEma21, { name: 'EMA21', color: '#ff9800', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: '#26a69a', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#ef5350', thickness: 3 });

// Mark entries and exits on price
const myLongEntryMarks = for_every(myLongEntrySignal, close, (_sig, _c) => _sig ? _c : null);
const myShortEntryMarks = for_every(myShortEntrySignal, close, (_sig, _c) => _sig ? _c : null);
const myLongExitMarks = for_every(myLongExitSignal, close, (_sig, _c) => _sig ? _c : null);
const myShortExitMarks = for_every(myShortExitSignal, close, (_sig, _c) => _sig ? _c : null);

paint(myLongEntryMarks, { name: 'LongEntry', color: '#00c853', style: 'labels_below' });
paint(myShortEntryMarks, { name: 'ShortEntry', color: '#d50000', style: 'labels_above' });
paint(myLongExitMarks, { name: 'LongExit', color: '#ff6d00', style: 'labels_above' });
paint(myShortExitMarks, { name: 'ShortExit', color: '#536dfe', style: 'labels_below' });

// Color candles on perfect trend alignment, similar to bgcolor() in Pine
const myCandleColors = for_every(myPerfectBull, myPerfectBear, (_bull, _bear) => {
	if (_bull) return '#2e7d32';
	if (_bear) return '#c62828';
	return null;
});
color_candles(myCandleColors);

// Register signals for scanner, alerts and strategy tester usage
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');
register_signal(myPerfectBull, 'Perfect Bull Alignment');
register_signal(myPerfectBear, 'Perfect Bear Alignment');