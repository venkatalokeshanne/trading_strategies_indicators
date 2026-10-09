// ORIGINAL SCRIPT WAS A TRADINGVIEW PINE STRATEGY ("ORB PRO + FILTERS").
// TrendSpider Custom JS does not support strategies (orders, exits, trailing
// stops, position sizing) - only indicators/signals. This port reproduces
// the ORB levels, EMA filter, ATR trail value and the long/short ENTRY
// conditions as signals. Exit logic (TP/trailing stop) cannot be expressed
// here; see the flagged note below.
describe_indicator('ORB PRO Plus Filters', 'price');

const myTab = input.tab('Settings');

const myOrbRow = myTab.row();
const myStartHour = myOrbRow.number('ORB Start Hour', 7, { min: 0, max: 23 });
const myEndHour = myOrbRow.number('ORB End Hour', 8, { min: 0, max: 23 });

const myAtrRow = myTab.row();
const myAtrLen = myAtrRow.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = myAtrRow.number('ATR Mult', 1.5, { min: 0.1, max: 10, step: 0.1 });

// EMA trend filter
const myEma = ema(close, 50);

// ATR for the trail calculation
const myAtr = atr(high, low, close, myAtrLen);

// Build ORB high/low per session day using a plain loop (stateful logic,
// cannot be expressed with the built-in vectorized functions).
const myOrbHigh = series_of(null);
const myOrbLow = series_of(null);
const myInORBFlags = [];
const myInSessionFlags = [];

let myCurOrbHigh = null;
let myCurOrbLow = null;
let myPrevDayKey = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = myTimeInfo.year * 1000 + myTimeInfo.dayOfYear;

	if (myPrevDayKey !== null && myDayKey !== myPrevDayKey) {
		myCurOrbHigh = null;
		myCurOrbLow = null;
	}
	myPrevDayKey = myDayKey;

	const myIsInORB = myTimeInfo.hours >= myStartHour && myTimeInfo.hours < myEndHour;

	if (myIsInORB) {
		myCurOrbHigh = myCurOrbHigh === null ? high[myIndex] : Math.max(myCurOrbHigh, high[myIndex]);
		myCurOrbLow = myCurOrbLow === null ? low[myIndex] : Math.min(myCurOrbLow, low[myIndex]);
	}

	myOrbHigh[myIndex] = myCurOrbHigh;
	myOrbLow[myIndex] = myCurOrbLow;
	myInORBFlags.push(myIsInORB);

	// Approximated session window (14:00 - 23:00), using the exchange time
	// zone exposed by time_of(), not Europe/Amsterdam specifically.
	const myIsInSession = myTimeInfo.hours >= 14 && myTimeInfo.hours <= 23;
	myInSessionFlags.push(myIsInSession);
}

const myOrbRange = sub(myOrbHigh, myOrbLow);
const myTrail = max_of(mult(myAtr, myAtrMult), mult(myOrbRange, 0.5));

const myPrevClose = shift(close, 1);

const myLongCond = for_every(close, myPrevClose, myOrbHigh, myEma, (_c, _pc, _oh, _e, _prev, _idx) => {
	return _oh != null && _c > _oh && _pc <= _oh && myInSessionFlags[_idx] && !myInORBFlags[_idx] && _c > _e;
});

const myShortCond = for_every(close, myPrevClose, myOrbLow, myEma, (_c, _pc, _ol, _e, _prev, _idx) => {
	return _ol != null && _c < _ol && _pc >= _ol && myInSessionFlags[_idx] && !myInORBFlags[_idx] && _c < _e;
});

register_signal(myLongCond, 'Long Entry');
register_signal(myShortCond, 'Short Entry');

paint(myOrbHigh, { name: 'ORB High', color: '#26A69A', thickness: 2, style: 'ladder' });
paint(myOrbLow, { name: 'ORB Low', color: '#EF5350', thickness: 2, style: 'ladder' });
paint(myEma, { name: 'EMA 50', color: '#4DA3FF', thickness: 2 });