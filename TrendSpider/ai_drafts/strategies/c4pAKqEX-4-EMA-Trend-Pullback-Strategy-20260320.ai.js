describe_indicator('4 EMA Trend and Pullback Strategy', 'price');

// EMA Settings
const myTab = input.tab('EMA Settings');
const myLen7 = myTab.number('EMA 7 Fast', 7, { min: 1, max: 500 });
const myLen21 = myTab.number('EMA 21 Slow', 21, { min: 1, max: 500 });
const myLen50 = myTab.number('EMA 50 Trend', 50, { min: 1, max: 500 });
const myLen200 = myTab.number('EMA 200 Macro', 200, { min: 1, max: 1000 });

const myEma7 = ema(close, myLen7);
const myEma21 = ema(close, myLen21);
const myEma50 = ema(close, myLen50);
const myEma200 = ema(close, myLen200);

// Macro trend filter
const myBullishMacro = for_every(myEma50, myEma200, (_e50, _e200) => _e50 > _e200);
const myBearishMacro = for_every(myEma50, myEma200, (_e50, _e200) => _e50 < _e200);

// Crossover / crossunder of EMA7 vs EMA21 (replicates ta.crossover / ta.crossunder)
const myCrossOver = for_every(myEma7, myEma21, (_e7, _e21, _prev, _idx) => {
	if (_idx === 0) return false;
	return myEma7[_idx - 1] <= myEma21[_idx - 1] && _e7 > _e21;
});
const myCrossUnder = for_every(myEma7, myEma21, (_e7, _e21, _prev, _idx) => {
	if (_idx === 0) return false;
	return myEma7[_idx - 1] >= myEma21[_idx - 1] && _e7 < _e21;
});

// Entry triggers
const myLongTrigger = myCrossOver;
const myShortTrigger = myCrossUnder;

// Exit conditions (per Pine logic, independent of position)
const myLongExitCondition = for_every(myCrossUnder, close, myEma50, (_cu, _c, _e50) => _cu || _c < _e50);
const myShortExitCondition = for_every(myCrossOver, close, myEma50, (_co, _c, _e50) => _co || _c > _e50);

// Simulated position tracking to replicate strategy.position_size behavior
// (Custom JS API has no strategy/backtest engine, so position state is approximated
// via a running flag: 1 = long, -1 = short, 0 = flat)
const myPositionState = for_every(
	myBullishMacro, myLongTrigger, myBearishMacro, myShortTrigger,
	myLongExitCondition, myShortExitCondition,
	(_bullMacro, _longTrig, _bearMacro, _shortTrig, _longExit, _shortExit, _prev, _idx) => {
		let myState = _idx === 0 ? 0 : _prev;
		if (myState > 0 && _longExit) {
			myState = 0;
		}
		else if (myState < 0 && _shortExit) {
			myState = 0;
		}
		if (myState === 0 && _bullMacro && _longTrig) {
			myState = 1;
		}
		else if (myState === 0 && _bearMacro && _shortTrig) {
			myState = -1;
		}
		return myState;
	});

// Final entry/exit signals, gated by simulated position state
const myLongEntrySignal = for_every(myPositionState, (_pos, _prev, _idx) => {
	const myPrevPos = _idx === 0 ? 0 : myPositionState[_idx - 1];
	return myPrevPos <= 0 && _pos === 1;
});
const myShortEntrySignal = for_every(myPositionState, (_pos, _prev, _idx) => {
	const myPrevPos = _idx === 0 ? 0 : myPositionState[_idx - 1];
	return myPrevPos >= 0 && _pos === -1;
});
const myLongExitSignal = for_every(myPositionState, (_pos, _prev, _idx) => {
	const myPrevPos = _idx === 0 ? 0 : myPositionState[_idx - 1];
	return myPrevPos === 1 && _pos !== 1;
});
const myShortExitSignal = for_every(myPositionState, (_pos, _prev, _idx) => {
	const myPrevPos = _idx === 0 ? 0 : myPositionState[_idx - 1];
	return myPrevPos === -1 && _pos !== -1;
});

// Perfect bull/bear alignment for background highlight
const myPerfectBull = for_every(myEma7, myEma21, myEma50, myEma200, (_e7, _e21, _e50, _e200) => _e7 > _e21 && _e21 > _e50 && _e50 > _e200);
const myPerfectBear = for_every(myEma7, myEma21, myEma50, myEma200, (_e7, _e21, _e50, _e200) => _e7 < _e21 && _e21 < _e50 && _e50 < _e200);

const myCandleColors = for_every(myPerfectBull, myPerfectBear, (_bull, _bear) => {
	if (_bull) return 'rgba(0,200,0,0.15)';
	if (_bear) return 'rgba(200,0,0,0.15)';
	return null;
});
color_candles(myCandleColors);

// Plot EMAs
paint(myEma7, { name: 'EMA7', color: '#2962FF', thickness: 1 });
paint(myEma21, { name: 'EMA21', color: '#FF9800', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: '#2E7D32', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#D32F2F', thickness: 3 });

// Register signals for scanner, alerts and strategy tester
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myShortExitSignal, 'Short Exit');
register_signal(myPerfectBull, 'Perfect Bull Alignment');
register_signal(myPerfectBear, 'Perfect Bear Alignment');