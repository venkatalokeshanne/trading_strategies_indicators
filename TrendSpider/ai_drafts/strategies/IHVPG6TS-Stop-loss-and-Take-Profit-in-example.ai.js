describe_indicator('Stop Loss and Take Profit in Dollars', 'price');

// NOTE: This is a conversion of a Pine Script v4 *strategy* into a
// TrendSpider indicator. TrendSpider's Custom JS API has no built-in
// strategy/broker emulator (no strategy.entry/exit, position sizing,
// syminfo.pointvalue/mintick), so position tracking, entries and
// exits are reproduced manually with an explicit state machine below.
// Several Pine mechanics are approximated - see the comments and the
// flags reported outside of the code.

const myTakeProfitDollars = input.number('Take Profit $', 200, { min: 0 });
const myStopLossDollars = input.number('Stop Loss $', 100, { min: 0 });
// In Pine, syminfo.mintick algebraically cancels out of the final
// price formula (points are converted to $ and back using mintick),
// so it is irrelevant to the final result and omitted here.
// syminfo.pointvalue and the strategy position size (default qty = 1
// contract/share, no pyramiding) are approximated via these inputs.
const myPointValue = input.number('Point Value', 1, { min: 0.0001 });
const myPositionSize = input.number('Position Size (qty)', 1, { min: 0.0001 });

const mySma14 = sma(close, 14);
const mySma28 = sma(close, 28);

const myCandleCount = close.length;

const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myExitSignal = series_of(false);

const myAvgPriceLine = series_of(null);
const myTakeProfitLine = series_of(null);
const myStopLossLine = series_of(null);

// Price distance equivalents of the $ amounts (mintick-independent,
// as derived from the original Pine formula).
const myTakeProfitDistance = myTakeProfitDollars / (myPointValue * myPositionSize);
const myStopLossDistance = myStopLossDollars / (myPointValue * myPositionSize);

// 0 = flat, 1 = long, -1 = short. Only one position at a time (no
// pyramiding), matching the default Pine strategy behavior.
let myPosition = 0;
let myAvgPrice = null;

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	const myCrossOver = mySma14[myIndex - 1] <= mySma28[myIndex - 1] && mySma14[myIndex] > mySma28[myIndex];
	const myCrossUnder = mySma14[myIndex - 1] >= mySma28[myIndex - 1] && mySma14[myIndex] < mySma28[myIndex];

	// Check for stop/target hits on the currently open position first.
	// Approximation: if both TP and SL fall within the same bar's
	// range, we cannot know which one Pine's bar-magnifier would hit
	// first, so this checks TP first, then SL (optimistic assumption).
	if (myPosition === 1 && myAvgPrice !== null) {
		const myTP = myAvgPrice + myTakeProfitDistance;
		const mySL = myAvgPrice - myStopLossDistance;
		if (high[myIndex] >= myTP || low[myIndex] <= mySL) {
			myExitSignal[myIndex] = true;
			myPosition = 0;
			myAvgPrice = null;
		}
	}
	else if (myPosition === -1 && myAvgPrice !== null) {
		const myTP = myAvgPrice - myTakeProfitDistance;
		const mySL = myAvgPrice + myStopLossDistance;
		if (low[myIndex] <= myTP || high[myIndex] >= mySL) {
			myExitSignal[myIndex] = true;
			myPosition = 0;
			myAvgPrice = null;
		}
	}

	// Entries. Approximation: Pine's strategy.entry fills on the next
	// bar's open by default; here we fill at the signal bar's close
	// for simplicity, so entry price/bar may differ slightly from the
	// original strategy's actual fills.
	if (myCrossOver && myPosition <= 0) {
		myPosition = 1;
		myAvgPrice = close[myIndex];
		myLongEntrySignal[myIndex] = true;
	}
	else if (myCrossUnder && myPosition >= 0) {
		myPosition = -1;
		myAvgPrice = close[myIndex];
		myShortEntrySignal[myIndex] = true;
	}

	if (myPosition !== 0 && myAvgPrice !== null) {
		myAvgPriceLine[myIndex] = myAvgPrice;
		myTakeProfitLine[myIndex] = myPosition === 1 ? myAvgPrice + myTakeProfitDistance : myAvgPrice - myTakeProfitDistance;
		myStopLossLine[myIndex] = myPosition === 1 ? myAvgPrice - myStopLossDistance : myAvgPrice + myStopLossDistance;
	}
}

const myAvgLinePainted = paint(myAvgPriceLine, { name: 'AvgPrice', color: 'gray', style: 'ladder' });
const myTpLinePainted = paint(myTakeProfitLine, { name: 'TakeProfit', color: 'green', style: 'ladder' });
const mySlLinePainted = paint(myStopLossLine, { name: 'StopLoss', color: 'red', style: 'ladder' });

fill(myTpLinePainted, myAvgLinePainted, 'green', 0.15, 'TPZone');
fill(myAvgLinePainted, mySlLinePainted, 'red', 0.15, 'SLZone');

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myExitSignal, 'Exit');