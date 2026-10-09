describe_indicator('Continuous Market Grid Bot', 'price');

// NOTE: TrendSpider Custom JS indicators cannot replicate a Pine
// strategy() object (equity, commissions, pyramiding, position sizing,
// order management). This script reproduces the SIGNAL LOGIC of the
// Pine script exactly (same bars fire Buy/Sell), and exposes Buy/Sell/
// Stop-Loss events via register_signal() so they can be used in
// Scanners, Alerts and the Strategy Tester. Actual trade execution,
// equity tracking and commission math are not reproduced.

const myGridTab = input.tab('Grid Settings');
const myUpperLimit = myGridTab.number('Upper Price Limit', 4600.0);
const myLowerLimit = myGridTab.number('Lower Price Limit', 4200.0);
const myGridLines = myGridTab.number('Number of Grids', 20, { min: 2, max: 200 });
const myQtyPerGrid = myGridTab.number('Order Size (Base Currency)', 0.1, { min: 0 });

const myRiskTab = input.tab('Risk Controls');
const myUseSL = myRiskTab.boolean('Enable Stop Loss', false);
const mySlPrice = myRiskTab.number('Stop Loss Price', 3800.0);

assert(myGridLines >= 2, 'Number of Grids must be at least 2');

const myGridStep = (myUpperLimit - myLowerLimit) / (myGridLines - 1);
const myCandleCount = close.length;

// Bot memory: whether each grid level currently holds a position
const myGridHolding = Array(myGridLines).fill(false);
let myBotActivated = false;

const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myStopLossSignal = series_of(false);
const myHoldingCount = series_of(0);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myClose = close[myIndex];
	const myHigh = high[myIndex];
	const myLow = low[myIndex];
	const myPrevHigh = myIndex > 0 ? high[myIndex - 1] : null;
	const myPrevLow = myIndex > 0 ? low[myIndex - 1] : null;

	// Wait for price to enter the grid zone before starting
	if (!myBotActivated && myClose >= myLowerLimit && myClose <= myUpperLimit) {
		myBotActivated = true;
	}

	let myBuyHappened = false;
	let mySellHappened = false;

	if (myBotActivated && myPrevHigh !== null && myPrevLow !== null) {
		for (let myGrid = 0; myGrid < myGridLines - 1; myGrid += 1) {
			const myGridPrice = myLowerLimit + (myGrid * myGridStep);
			const myTargetPrice = myGridPrice + myGridStep;

			const myHitBuy = myLow <= myGridPrice && myPrevHigh >= myGridPrice;

			if (myHitBuy && !myGridHolding[myGrid]) {
				myGridHolding[myGrid] = true;
				myBuyHappened = true;
			}
			else {
				const myHitSell = myHigh >= myTargetPrice && myPrevLow <= myTargetPrice;

				if (myHitSell && myGridHolding[myGrid]) {
					myGridHolding[myGrid] = false;
					mySellHappened = true;
				}
			}
		}
	}

	let myStopLossHappened = false;

	if (myUseSL && myClose <= mySlPrice) {
		myBotActivated = false;
		myStopLossHappened = true;

		for (let myGrid = 0; myGrid < myGridLines; myGrid += 1) {
			myGridHolding[myGrid] = false;
		}
	}

	myBuySignal[myIndex] = myBuyHappened;
	mySellSignal[myIndex] = mySellHappened;
	myStopLossSignal[myIndex] = myStopLossHappened;
	myHoldingCount[myIndex] = myGridHolding.filter(_myHolding => _myHolding).length;
}

// Price boundary lines (equivalent of the two plot() calls)
paint(series_of(myUpperLimit), { name: 'UpperLimit', color: 'red', thickness: 2, style: 'line' });
paint(series_of(myLowerLimit), { name: 'LowerLimit', color: 'green', thickness: 2, style: 'line' });

// Buy / Sell markers on candles
const myBuyMarks = for_every(myBuySignal, _myBuy => _myBuy ? constants.icons.triangle_up : null);
const mySellMarks = for_every(mySellSignal, _mySell => _mySell ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'GridBuy', color: 'green', style: 'labels_below' });
paint(mySellMarks, { name: 'GridSell', color: 'red', style: 'labels_above' });

// Active grid position count, forced onto price axis since this is a price indicator
paint(myHoldingCount, { name: 'ActiveGrids', color: 'gray', thickness: 1, style: 'line', forceUsePriceAxis: true });

register_signal(myBuySignal, 'Grid Buy');
register_signal(mySellSignal, 'Grid Sell');
register_signal(myStopLossSignal, 'Grid Stop Loss Hit');