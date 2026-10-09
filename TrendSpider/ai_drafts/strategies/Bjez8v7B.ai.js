describe_indicator('Atlantium Gold - Safe Trader (converted)', 'price');

// =====================================================================
// This indicator reproduces the Pine Script "Atlantium Gold - Safe
// Trader" strategy logic. Strategy-level mechanics which do not exist
// in the Custom JS API (position sizing, equity, commissions, order
// fills, bgcolor backgrounds) are approximated. See notes below code.
// =====================================================================

const myTpMult = input.number('TP ATR Multiplier', 5.5, { min: 0.1, max: 20 });
const mySlMult = input.number('SL ATR Multiplier', 2.5, { min: 0.1, max: 20 });
const myAllowedHourStart = input.number('Allowed Hour Start', 8, { min: 0, max: 23 });
const myAllowedHourEnd = input.number('Allowed Hour End', 19, { min: 0, max: 23 });
const myWeekendHour = input.number('Friday Close Hour', 20, { min: 0, max: 23 });
const myNewsSpikeMult = input.number('News Spike ATR Multiplier', 2.5, { min: 0.1, max: 10 });

// --- Core indicators (computed once, outside any loop) ---
const myEmaFast = ema(close, 10);
const myEmaSlow = ema(close, 40);
const myRsi = rsi(close, 14);
const myAtrFast = atr(high, low, close, 5);
const myAtrSlow = atr(high, low, close, 20);
const myAtr = atr(high, low, close, 14);

// --- Per-bar time attributes ---
const myHourOf = time.map(_t => time_of(_t).hours);
// time_of().dayOfWeek is ISO: 1=Mon ... 5=Fri ... 7=Sun
const myDayOfWeekOf = time.map(_t => time_of(_t).dayOfWeek);

// --- Output series ---
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myCloseSignal = series_of(false);
const myWeekendNear = series_of(false);
const myNewsSpike = series_of(false);
const mySlLine = series_of(null);
const myTpLine = series_of(null);

// --- State machine replicating strategy.position_size / sl / tp ---
// myPositionSize: 0 = flat, 1 = long, -1 = short
let myPositionSize = 0;
let mySl = null;
let myTp = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myIsAllowedHour = myHourOf[myIndex] >= myAllowedHourStart && myHourOf[myIndex] <= myAllowedHourEnd;
	const myIsFriday = myDayOfWeekOf[myIndex] === 5;
	const myIsWeekendNear = myIsFriday && myHourOf[myIndex] >= myWeekendHour;
	const myIsNewsSpike = myAtrFast[myIndex] > (myAtrSlow[myIndex] * myNewsSpikeMult);

	myWeekendNear[myIndex] = myIsWeekendNear;
	myNewsSpike[myIndex] = myIsNewsSpike;

	// position size as of the start of this bar (used for "can_trade",
	// matching Pine's evaluation order before exits are processed)
	const myPositionAtBarStart = myPositionSize;

	// --- forced close on Friday evening ---
	if (myIsWeekendNear && myPositionSize !== 0) {
		myPositionSize = 0;
		mySl = null;
		myTp = null;
		myCloseSignal[myIndex] = true;
	}
	// --- normal TP/SL exit check (intrabar touch) ---
	else if (myPositionSize === 1) {
		if (low[myIndex] <= mySl || high[myIndex] >= myTp) {
			myPositionSize = 0;
			mySl = null;
			myTp = null;
			myCloseSignal[myIndex] = true;
		}
	}
	else if (myPositionSize === -1) {
		if (high[myIndex] >= mySl || low[myIndex] <= myTp) {
			myPositionSize = 0;
			mySl = null;
			myTp = null;
			myCloseSignal[myIndex] = true;
		}
	}

	// --- entries ---
	const myCanTrade = myPositionAtBarStart === 0 && myIsAllowedHour && !myIsWeekendNear && !myIsNewsSpike;

	const myCrossover = myEmaFast[myIndex] > myEmaSlow[myIndex] && myEmaFast[myIndex - 1] <= myEmaSlow[myIndex - 1];
	const myCrossunder = myEmaFast[myIndex] < myEmaSlow[myIndex] && myEmaFast[myIndex - 1] >= myEmaSlow[myIndex - 1];

	const myLongCond = myCanTrade && myCrossover && myRsi[myIndex] > 50;
	const myShortCond = myCanTrade && myCrossunder && myRsi[myIndex] < 50;

	if (myLongCond) {
		mySl = close[myIndex] - (myAtr[myIndex] * mySlMult);
		myTp = close[myIndex] + (myAtr[myIndex] * myTpMult);
		myPositionSize = 1;
		myBuySignal[myIndex] = true;
	}
	else if (myShortCond) {
		mySl = close[myIndex] + (myAtr[myIndex] * mySlMult);
		myTp = close[myIndex] - (myAtr[myIndex] * myTpMult);
		myPositionSize = -1;
		mySellSignal[myIndex] = true;
	}

	mySlLine[myIndex] = mySl;
	myTpLine[myIndex] = myTp;
}

// --- Visuals ---
paint(myEmaFast, { name: 'Ema Fast', color: '#00E5FF', thickness: 1 });
paint(myEmaSlow, { name: 'Ema Slow', color: '#FFFFFF', thickness: 2 });
paint(mySlLine, { name: 'Stop Loss', color: '#EF5350', style: 'dotted', thickness: 1 });
paint(myTpLine, { name: 'Take Profit', color: '#26A69A', style: 'dotted', thickness: 1 });

// --- Scanner/Alert/Strategy signals ---
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myCloseSignal, 'Close Signal');
register_signal(myWeekendNear, 'Weekend Close Filter');
register_signal(myNewsSpike, 'News Spike Filter');