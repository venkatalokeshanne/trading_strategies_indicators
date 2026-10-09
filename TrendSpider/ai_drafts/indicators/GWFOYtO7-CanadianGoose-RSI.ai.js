describe_indicator('RSI Signal', 'lower');

// Inputs matching the Pine Script inputs
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const mySigLength = input.number('Signal EMA Length', 14, { min: 1, max: 200 });
const myUpperLevel = input.number('Upper Alert Level', 65, { min: 0, max: 100 });
const myLowerLevel = input.number('Lower Alert Level', 35, { min: 0, max: 100 });

// Core math: RSI and its EMA smoothed "signal line"
const myRsiVal = rsi(close, myRsiLength);
const mySigLine = ema(myRsiVal, mySigLength);

// We need stateful logic (the "armed" flag), which depends on previous
// bar's state, cross of signal line through 50, and crossover/crossunder
// of the alert levels. This can't be expressed with for_every alone
// (it only tracks one previous value), so we use a plain loop over
// already-computed series (no indicator functions are called inside it).
const myUpperSignal = series_of(false);
const myLowerSignal = series_of(false);
const myArmedState = series_of(true);

let myArmed = true;

for (let myIndex = 0; myIndex < mySigLine.length; myIndex += 1) {
	const myCurr = mySigLine[myIndex];
	const myPrev = myIndex > 0 ? mySigLine[myIndex - 1] : null;

	// ta.cross(sigLine, 50): re-arm whenever signal line crosses 50 in either direction
	if (myPrev !== null && myCurr !== null) {
		const myCrossed50 = (myPrev - 50) * (myCurr - 50) < 0 || myCurr === 50;
		if (myCrossed50) {
			myArmed = true;
		}
	}

	// ta.crossover(sigLine, upperLevel): prev <= level and curr > level
	const myCrossoverUpper = myPrev !== null && myCurr !== null && myPrev <= myUpperLevel && myCurr > myUpperLevel;

	// ta.crossunder(sigLine, lowerLevel): prev >= level and curr < level
	const myCrossunderLower = myPrev !== null && myCurr !== null && myPrev >= myLowerLevel && myCurr < myLowerLevel;

	const myFinalUpperSignal = myCrossoverUpper && myArmed;
	const myFinalLowerSignal = myCrossunderLower && myArmed;

	myUpperSignal[myIndex] = myFinalUpperSignal;
	myLowerSignal[myIndex] = myFinalLowerSignal;

	if (myFinalUpperSignal || myFinalLowerSignal) {
		myArmed = false;
	}

	myArmedState[myIndex] = myArmed;
}

// Plot the signal line
paint(mySigLine, { name: 'Signal', color: 'orange', thickness: 2 });

// Reference horizontal levels (fixed, like the Pine hlines)
paint(horizontal_line(50), { name: 'Midline', color: 'gray', style: 'line' });
paint(horizontal_line(70), { name: 'Upper Level', color: 'red', style: 'line' });
paint(horizontal_line(30), { name: 'Lower Level', color: 'green', style: 'line' });

// Dynamic alert levels (based on user inputs)
paint(horizontal_line(myUpperLevel), { name: 'Upper Alarm', color: 'green', style: 'dotted' });
paint(horizontal_line(myLowerLevel), { name: 'Lower Alarm', color: 'red', style: 'dotted' });

// Mark the actual signal bars on the line itself
const myUpperMarks = for_every(mySigLine, myUpperSignal, (_sig, _flag) => _flag ? _sig : null);
const myLowerMarks = for_every(mySigLine, myLowerSignal, (_sig, _flag) => _flag ? _sig : null);

paint(myUpperMarks, { name: 'Overbought Signal', color: 'red', style: 'line', thickness: 4 });
paint(myLowerMarks, { name: 'Oversold Signal', color: 'green', style: 'line', thickness: 4 });

// Register signals so they are usable in Scanners, Alerts, Strategy Tester
register_signal(myUpperSignal, 'RSI Signal Overbought');
register_signal(myLowerSignal, 'RSI Signal Oversold');

// Overlay replicating the "GOOSE ARMED / GOOSE DISARMED" status table
const myIsArmedNow = myArmedState[myArmedState.length - 1];

paint_overlay('ArmedStatusTable', { position: 'top_right' }, {
	rows: [{
		cells: [{
			text: myIsArmedNow ? 'GOOSE ARMED' : 'GOOSE DISARMED',
			background_color: myIsArmedNow ? 'green' : 'red',
			color: 'white'
		}]
	}]
});