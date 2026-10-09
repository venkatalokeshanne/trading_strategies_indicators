describe_indicator('SilverStream v2', 'price');

// This script reproduces the Pine Script strategy logic (EMA trend +
// breakout entries, fixed $ target/stop exits, cooldown control) as
// closely as the Custom JS API allows. Strategy order execution,
// pyramiding and backtest P&L are not modeled; instead we simulate a
// single-position state machine bar by bar to reproduce the same
// buy/sell/exit signal bars as the Pine strategy would generate.

const myFastEmaLength = input.number('Fast EMA', 30, { min: 1, max: 500 });
const mySlowEmaLength = input.number('Slow EMA', 50, { min: 1, max: 500 });
const myTargetMove = input.number('Target Move ($)', 2.0, { min: 0, max: 10000 });
const myStopMove = input.number('Stop Move ($)', 1.0, { min: 0, max: 10000 });
const myCooldownBars = input.number('Trade Cooldown', 3, { min: 0, max: 1000 });

const myEmaFast = ema(close, myFastEmaLength);
const myEmaSlow = ema(close, mySlowEmaLength);

const myLongTrend = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f > _s);
const myShortTrend = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f < _s);

const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);

const myBullBreak = for_every(close, myPrevHigh, (_c, _h) => _c > _h);
const myBearBreak = for_every(close, myPrevLow, (_c, _l) => _c < _l);

const myBuySignalArr = for_every(myLongTrend, myBullBreak, (_lt, _bb) => _lt && _bb);
const mySellSignalArr = for_every(myShortTrend, myBearBreak, (_st, _bb) => _st && _bb);

// Position state machine, simulating the Pine strategy's single-position
// behavior (pyramiding=1, fixed qty), including target/stop exits.
const myBuyMarks = series_of(null);
const mySellMarks = series_of(null);
const myExitMarks = series_of(null);
const myBuySignalOut = series_of(false);
const mySellSignalOut = series_of(false);
const myExitSignalOut = series_of(false);

let myLastTradeBar = null;
let myPositionSize = 0; // 0 = flat, 1 = long, -1 = short
let myAvgPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevPositionSize = myPositionSize;

	// Check exits first (target/stop) if currently in a position
	if (myPositionSize === 1) {
		const myLongTarget = myAvgPrice + myTargetMove;
		const myLongStop = myAvgPrice - myStopMove;
		if (high[myIndex] >= myLongTarget || low[myIndex] <= myLongStop) {
			myPositionSize = 0;
			myAvgPrice = null;
		}
	}
	else if (myPositionSize === -1) {
		const myShortTarget = myAvgPrice - myTargetMove;
		const myShortStop = myAvgPrice + myStopMove;
		if (low[myIndex] <= myShortTarget || high[myIndex] >= myShortStop) {
			myPositionSize = 0;
			myAvgPrice = null;
		}
	}

	const myCooldownOK = (myLastTradeBar === null) || ((myIndex - myLastTradeBar) > myCooldownBars);

	const myBuy = myBuySignalArr[myIndex] && myCooldownOK;
	const mySell = mySellSignalArr[myIndex] && myCooldownOK;

	if (myBuy) {
		myPositionSize = 1;
		myAvgPrice = close[myIndex];
		myLastTradeBar = myIndex;
	}
	else if (mySell) {
		myPositionSize = -1;
		myAvgPrice = close[myIndex];
		myLastTradeBar = myIndex;
	}

	const myExit = (myPositionSize === 0) && (myPrevPositionSize !== 0);

	myBuySignalOut[myIndex] = myBuy;
	mySellSignalOut[myIndex] = mySell;
	myExitSignalOut[myIndex] = myExit;

	myBuyMarks[myIndex] = myBuy ? low[myIndex] : null;
	mySellMarks[myIndex] = mySell ? high[myIndex] : null;
	myExitMarks[myIndex] = myExit ? close[myIndex] : null;
}

paint(myEmaFast, { name: 'FastEMA', color: '#2ca599', thickness: 2 });
paint(myEmaSlow, { name: 'SlowEMA', color: '#ee5451', thickness: 2 });

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });
paint(myExitMarks, { name: 'Exit', style: 'labels_above', color: 'gold' });

register_signal(myBuySignalOut, 'Buy Signal');
register_signal(mySellSignalOut, 'Sell Signal');
register_signal(myExitSignalOut, 'Exit Signal');