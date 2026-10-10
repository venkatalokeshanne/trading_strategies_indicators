describe_indicator('NASDAQ ORB Strategy - Strict Exec', 'price');

// Inputs
const myRvolThreshold = input.number('Minimum RVOL for entry', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myRrr = input.number('Risk Reward Ratio', 2.0, { min: 0.1, max: 10, step: 0.1 });

// We need New York local hour/minute for every candle, regardless of
// the exchange timezone of the chart. The built-in time_of() uses the
// exchange timezone, so we use the whitelisted moment-timezone library
// to force America/New_York conversion, like the original Pine script.
const myMoment = library('moment-timezone');

const myNyHour = time.map(_t => Number(myMoment.unix(_t).tz('America/New_York').format('H')));
const myNyMinute = time.map(_t => Number(myMoment.unix(_t).tz('America/New_York').format('m')));

// Volume SMA(20) and RVOL, computed outside of loops as required
const myVolSma = sma(volume, 20);
const myRvol = for_every(volume, myVolSma, (_v, _vs) => (_vs != null && _vs > 0) ? (_v / _vs) : 1.0);

const myCandleCount = close.length;

// Raw (continuous) ORB levels used for crossover detection
const myOrbHighRaw = series_of(null);
const myOrbLowRaw = series_of(null);
const myOrbMidRaw = series_of(null);

// Display series (sparse, only visible once locked & inside trade window)
const myOrbHighDisplay = series_of(null);
const myOrbLowDisplay = series_of(null);
const myOrbMidDisplay = series_of(null);

const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myEodCloseSignal = series_of(false);

const mySlLine = series_of(null);
const myTpLine = series_of(null);

let myOrbHigh = null;
let myOrbLow = null;
let myOrbMid = null;
let myOrbLocked = false;
let myTradeTakenToday = false;

let myPositionDirection = 0; // 1 long, -1 short, 0 flat
let myCurrentSl = null;
let myCurrentTp = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myHour = myNyHour[myIndex];
	const myMinute = myNyMinute[myIndex];
	const myClose = close[myIndex];
	const myHigh = high[myIndex];
	const myLow = low[myIndex];

	const myIsOrbWindow = (myHour == 9 && myMinute >= 30 && myMinute < 45);
	const myIsTradeWindow = (myHour == 9 && myMinute >= 45) || (myHour > 9 && myHour < 16);

	// Reset exactly at 09:30 NY
	if (myHour == 9 && myMinute == 30) {
		myOrbHigh = myHigh;
		myOrbLow = myLow;
		myOrbMid = null;
		myOrbLocked = false;
		myTradeTakenToday = false;
	}
	else if (myIsOrbWindow && myOrbHigh != null) {
		myOrbHigh = Math.max(myHigh, myOrbHigh);
		myOrbLow = Math.min(myLow, myOrbLow);
	}

	// Lock the range at 09:45 NY
	if (myHour == 9 && myMinute == 45 && !myOrbLocked && myOrbHigh != null && myOrbLow != null) {
		myOrbMid = (myOrbHigh + myOrbLow) / 2;
		myOrbLocked = true;
	}

	myOrbHighRaw[myIndex] = myOrbHigh;
	myOrbLowRaw[myIndex] = myOrbLow;
	myOrbMidRaw[myIndex] = myOrbMid;

	myOrbHighDisplay[myIndex] = (myOrbLocked && myIsTradeWindow) ? myOrbHigh : null;
	myOrbLowDisplay[myIndex] = (myOrbLocked && myIsTradeWindow) ? myOrbLow : null;
	myOrbMidDisplay[myIndex] = (myOrbLocked && myIsTradeWindow) ? myOrbMid : null;

	// Strict close-based crossover/crossunder vs previous candle
	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;
	const myPrevOrbHigh = myIndex > 0 ? myOrbHighRaw[myIndex - 1] : null;
	const myPrevOrbLow = myIndex > 0 ? myOrbLowRaw[myIndex - 1] : null;

	const myIsBreakingHigh = (myPrevClose != null && myPrevOrbHigh != null && myOrbHigh != null) &&
		(myClose > myOrbHigh && myPrevClose <= myPrevOrbHigh);

	const myIsBreakingLow = (myPrevClose != null && myPrevOrbLow != null && myOrbLow != null) &&
		(myClose < myOrbLow && myPrevClose >= myPrevOrbLow);

	const myCanTrade = myIsTradeWindow && myOrbLocked && !myTradeTakenToday && myPositionDirection == 0;

	let myLong = false;
	let myShort = false;

	if (myCanTrade) {
		if (myIsBreakingHigh && myRvol[myIndex] >= myRvolThreshold) {
			const myLongSl = myOrbMid;
			const myLongRisk = myClose - myLongSl;
			const myLongTp = myClose + (myLongRisk * myRrr);

			myCurrentSl = myLongSl;
			myCurrentTp = myLongTp;
			myPositionDirection = 1;
			myTradeTakenToday = true;
			myLong = true;
		}
		else if (myIsBreakingLow && myRvol[myIndex] >= myRvolThreshold) {
			const myShortSl = myOrbMid;
			const myShortRisk = myShortSl - myClose;
			const myShortTp = myClose - (myShortRisk * myRrr);

			myCurrentSl = myShortSl;
			myCurrentTp = myShortTp;
			myPositionDirection = -1;
			myTradeTakenToday = true;
			myShort = true;
		}
	}

	// Simulate stop/limit exit (closes approximated on candle extremes)
	if (myPositionDirection == 1) {
		if (myHigh >= myCurrentTp || myLow <= myCurrentSl) {
			myPositionDirection = 0;
			myCurrentSl = null;
			myCurrentTp = null;
		}
	}
	else if (myPositionDirection == -1) {
		if (myLow <= myCurrentTp || myHigh >= myCurrentSl) {
			myPositionDirection = 0;
			myCurrentSl = null;
			myCurrentTp = null;
		}
	}

	// Forced EOD close at 16:00 NY
	let myEodClose = false;
	if (myHour == 16 && myMinute == 0 && myPositionDirection != 0) {
		myPositionDirection = 0;
		myCurrentSl = null;
		myCurrentTp = null;
		myEodClose = true;
	}

	myLongSignal[myIndex] = myLong;
	myShortSignal[myIndex] = myShort;
	myEodCloseSignal[myIndex] = myEodClose;

	mySlLine[myIndex] = myCurrentSl;
	myTpLine[myIndex] = myCurrentTp;
}

// Plotting ORB levels (locked range + mid line used as SL reference)
paint(myOrbHighDisplay, { name: 'ORB High', color: '#ffffff', thickness: 2, style: 'line' });
paint(myOrbLowDisplay, { name: 'ORB Low', color: '#ffffff', thickness: 2, style: 'line' });
paint(myOrbMidDisplay, { name: 'ORB Mid', color: '#f1c40f', thickness: 2, style: 'line' });

// Active trade SL/TP reference lines
paint(mySlLine, { name: 'Active Stop Loss', color: '#9b59b6', thickness: 1, style: 'dotted' });
paint(myTpLine, { name: 'Active Take Profit', color: '#2e86de', thickness: 1, style: 'dotted' });

// Signals usable in Scanners, Alerts and Strategy Tester
register_signal(myLongSignal, 'Long ORB Entry');
register_signal(myShortSignal, 'Short ORB Entry');
register_signal(myEodCloseSignal, 'EOD Forced Close');