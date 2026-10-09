describe_indicator('EQL EQH Reversal System', 'price');

// === INPUTS ===
const myLookback = input.number('Lookback Bars', 30, { min: 2, max: 500 });
const myTolerance = input.number('Tolerance (pts)', 5.0, { min: 0, max: 1000 });
const mySessionText = input.text('Session (HHMM-HHMM)', '0945-1400');
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrStopMult = input.number('ATR Stop Multiplier', 1.5, { min: 0.01, max: 20 });
const myAtrTargetMult = input.number('ATR Target Multiplier', 2.5, { min: 0.01, max: 20 });

// parses "HHMM-HHMM" session string into { startMinutes, endMinutes }
function myParseSession(_sessionText) {
	const myParts = _sessionText.split('-');
	const myStart = myParts[0];
	const myEnd = myParts[1];
	return {
		startMinutes: parseInt(myStart.slice(0, 2), 10) * 60 + parseInt(myStart.slice(2, 4), 10),
		endMinutes: parseInt(myEnd.slice(0, 2), 10) * 60 + parseInt(myEnd.slice(2, 4), 10)
	};
}

const mySessionWindow = myParseSession(mySessionText);
const myMarketDays = current.session && current.session.marketDays ? current.session.marketDays : [1, 2, 3, 4, 5];

// checks whether a given candle index falls within the configured session window
function myIsInSession(_candleIndex) {
	const myTimeInfo = time_of(time[_candleIndex]);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myIsMarketDay = myMarketDays.includes(myTimeInfo.dayOfWeek);
	return myIsMarketDay && myMinutesOfDay >= mySessionWindow.startMinutes && myMinutesOfDay <= mySessionWindow.endMinutes;
}

// === ATR ===
const myAtr = atr(high, low, close, myAtrLength);
const myStopDist = mult(myAtr, myAtrStopMult);
const myTargetDist = mult(myAtr, myAtrTargetMult);

// === HIGHEST / LOWEST ===
const myHH = highest(high, myLookback);
const myLL = lowest(low, myLookback);
const myCandleCount = close.length;

const myEqhLine = series_of(null);
const myEqlLine = series_of(null);
const myShortSignal = series_of(false);
const myLongSignal = series_of(false);

// simplified strategy position simulation: tracks a single open
// position (flat/long/short), closing it when stop or target is
// touched by a subsequent candle's high/low, mirroring Pine's
// strategy.position_size == 0 gate for new entries.
let myPositionState = 0; // 0 flat, 1 long, -1 short
let myStopPrice = 0;
let myTargetPrice = 0;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myIndex < myLookback) {
		continue;
	}

	let myEqhCount = 0;
	let myEqlCount = 0;

	for (let myOffset = 1; myOffset <= myLookback; myOffset += 1) {
		const myPastIndex = myIndex - myOffset;
		if (myPastIndex < 0) {
			continue;
		}
		if (high[myPastIndex] >= myHH[myIndex] - myTolerance) {
			myEqhCount += 1;
		}
		if (low[myPastIndex] <= myLL[myIndex] + myTolerance) {
			myEqlCount += 1;
		}
	}

	const myShortCond = myEqhCount >= 2 && high[myIndex] >= myHH[myIndex] - myTolerance;
	const myLongCond = myEqlCount >= 2 && low[myIndex] <= myLL[myIndex] + myTolerance;
	const myInSession = myIsInSession(myIndex);

	// close an existing position if stop or target was hit on this candle
	if (myPositionState === 1) {
		if (low[myIndex] <= myStopPrice) {
			myPositionState = 0;
		}
		else if (high[myIndex] >= myTargetPrice) {
			myPositionState = 0;
		}
	}
	else if (myPositionState === -1) {
		if (high[myIndex] >= myStopPrice) {
			myPositionState = 0;
		}
		else if (low[myIndex] <= myTargetPrice) {
			myPositionState = 0;
		}
	}

	const myShortSig = myInSession && myPositionState === 0 && myShortCond;
	const myLongSig = myInSession && myPositionState === 0 && myLongCond && !myShortSig;

	if (myShortSig) {
		myPositionState = -1;
		myStopPrice = close[myIndex] + myStopDist[myIndex];
		myTargetPrice = close[myIndex] - myTargetDist[myIndex];
	}
	else if (myLongSig) {
		myPositionState = 1;
		myStopPrice = close[myIndex] - myStopDist[myIndex];
		myTargetPrice = close[myIndex] + myTargetDist[myIndex];
	}

	myEqhLine[myIndex] = myEqhCount >= 2 ? myHH[myIndex] : null;
	myEqlLine[myIndex] = myEqlCount >= 2 ? myLL[myIndex] : null;
	myShortSignal[myIndex] = myShortSig;
	myLongSignal[myIndex] = myLongSig;
}

paint(myEqhLine, { name: 'EQH', color: 'red', thickness: 2, style: 'line' });
paint(myEqlLine, { name: 'EQL', color: 'green', thickness: 2, style: 'line' });

const myShortMarks = for_every(myShortSignal, high, (_signal, _high) => _signal ? _high : null);
const myLongMarks = for_every(myLongSignal, low, (_signal, _low) => _signal ? _low : null);

// renamed the painted labels so their names don't collide with the
// register_signal() names below (every paint/register_signal name
// must be unique across the whole indicator)
paint(myShortMarks, { name: 'Short Marker', style: 'labels_above', color: 'red' });
paint(myLongMarks, { name: 'Long Marker', style: 'labels_below', color: 'green' });

register_signal(myShortSignal, 'Short Signal');
register_signal(myLongSignal, 'Long Signal');