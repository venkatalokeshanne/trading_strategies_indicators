describe_indicator('LVN Rejection Acceptance Strategy', 'price');

// NOTE: TradingView strategy.entry/exit logic (position sizing, stop/limit
// fills) is simulated here with a bar-by-bar loop that tracks a simple
// long/flat/short state machine. Intrabar stop/limit fills are approximated
// using the candle's high/low (TradingView fills intrabar too, so this is
// a close match but not guaranteed identical on every edge case, since
// TrendSpider does not expose intrabar order simulation).

const myZoneLen = input.number('LVN Detection Length', 40, { min: 1, max: 500 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 200 });
const myZoneWidth = input.number('LVN Width ATR', 0.8, { min: 0.01, max: 10 });
const myStopMult = input.number('Stop ATR Multiplier', 1.5, { min: 0.01, max: 20 });
const myRr = input.number('Risk Reward', 2.0, { min: 0.01, max: 20 });

const myBasis = sma(close, myZoneLen);
const myAtrVal = atr(high, low, close, myAtrLen);

const myLvnUpper = add(myBasis, mult(myAtrVal, myZoneWidth));
const myLvnLower = sub(myBasis, mult(myAtrVal, myZoneWidth));

const myAvgVol = sma(volume, myZoneLen);
const myLowVol = for_every(volume, myAvgVol, (_v, _avg) => _v < _avg * 0.8);

const myBullReject = for_every(low, myLvnLower, close, myLowVol, (_l, _lower, _c, _lv) => _l < _lower && _c > _lower && _lv);
const myBearReject = for_every(high, myLvnUpper, close, myLowVol, (_h, _upper, _c, _lv) => _h > _upper && _c < _upper && _lv);

const myCloseShift1 = shift(close, 1);
const myBullAccept = for_every(close, myLvnUpper, myCloseShift1, (_c, _upper, _cp) => _c > _upper && _cp > _upper);
const myBearAccept = for_every(close, myLvnLower, myCloseShift1, (_c, _lower, _cp) => _c < _lower && _cp < _lower);

const myLongCondition = for_every(myBullReject, myBullAccept, (_a, _b) => _a || _b);
const myShortCondition = for_every(myBearReject, myBearAccept, (_a, _b) => _a || _b);

// ───── Bar-by-bar state machine to simulate strategy entries/exits ─────
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

let myPositionState = 0; // 0 flat, 1 long, -1 short
let myEntryPrice = null;
let myStopPrice = null;
let myTargetPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myHighNow = high[myIndex];
	const myLowNow = low[myIndex];
	const myAtrNow = myAtrVal[myIndex];

	if (myPositionState === 1) {
		if (myLowNow <= myStopPrice || myHighNow >= myTargetPrice) {
			myLongExitSignal[myIndex] = true;
			myPositionState = 0;
			myEntryPrice = null;
			myStopPrice = null;
			myTargetPrice = null;
		}
	}
	else if (myPositionState === -1) {
		if (myHighNow >= myStopPrice || myLowNow <= myTargetPrice) {
			myShortExitSignal[myIndex] = true;
			myPositionState = 0;
			myEntryPrice = null;
			myStopPrice = null;
			myTargetPrice = null;
		}
	}

	if (myPositionState === 0) {
		if (myLongCondition[myIndex] && myAtrNow != null) {
			myPositionState = 1;
			myEntryPrice = close[myIndex];
			myStopPrice = myEntryPrice - myAtrNow * myStopMult;
			myTargetPrice = myEntryPrice + myAtrNow * myStopMult * myRr;
			myLongEntrySignal[myIndex] = true;
		}
		else if (myShortCondition[myIndex] && myAtrNow != null) {
			myPositionState = -1;
			myEntryPrice = close[myIndex];
			myStopPrice = myEntryPrice + myAtrNow * myStopMult;
			myTargetPrice = myEntryPrice - myAtrNow * myStopMult * myRr;
			myShortEntrySignal[myIndex] = true;
		}
	}
}

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');

paint(myBasis, { name: 'LVN Mid', color: 'orange', thickness: 1 });
paint(myLvnUpper, { name: 'LVN Upper', color: 'red', thickness: 1 });
paint(myLvnLower, { name: 'LVN Lower', color: 'green', thickness: 1 });