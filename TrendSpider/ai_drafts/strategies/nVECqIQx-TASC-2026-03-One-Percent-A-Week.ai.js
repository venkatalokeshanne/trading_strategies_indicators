describe_indicator('TASC 2026.03 One Percent A Week', 'price');

// This indicator is an approximation of a TradingView Pine Script
// STRATEGY (which places limit orders, tracks fills, averages
// price, and manages exits). The Custom JS API has no native
// concept of pending limit orders, intrabar fills, or a
// strategy.position_size state machine, so this script
// re-implements that logic manually, bar by bar, using the
// following simplifying assumptions:
//   1. It assumes the chart is running on the Daily resolution
//      (each candle = one session), since the Pine logic relies
//      on "session.isfirstbar_regular" which, on a Daily chart,
//      is always true, meaning the profit-target order is set on
//      the very same bar as the fill (not literally "next day").
//   2. A pending Buy limit order (at 1% below Monday's open) is
//      considered "filled" on any bar where candle Low touches
//      or crosses below that limit price.
//   3. The profit-target / break-even Sell limit order is
//      considered "filled" on any bar where candle High touches
//      or crosses above that limit price.
//   4. "strategy.close_all" on Friday is modeled as an unconditional
//      flat-out at Friday's close.
// These are reasonable proxies for intrabar order fills, since the
// Custom JS API only has access to O/H/L/C per bar, not tick data.

const myWOpenArr = series_of(null);
const myDown1Arr = series_of(null);
const myBetArr = series_of(null);
const myPtArr = series_of(null);

const myBuySignalArr = series_of(false);
const myProfitSignalArr = series_of(false);
const myBreakevenSetSignalArr = series_of(false);
const myFridayCloseSignalArr = series_of(false);

let myWOpen = null;
let myDown1 = null;
let myPositionSize = 0;
let myAvgPrice = null;
let myPt = null;
let myBeSent = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myDow = time_of(time[myIndex]).dayOfWeek; // 1 = Monday, 5 = Friday
	const myIsMonday = myDow === 1;
	const myIsFriday = myDow === 5;

	let myBuyFilledThisBar = false;
	let myProfitFilledThisBar = false;
	let myBreakevenSetThisBar = false;
	let myFridayClosedThisBar = false;

	// Step 1 & 2: observe Monday open, set 1% dip limit price
	if (myIsMonday) {
		myWOpen = open[myIndex];
		myDown1 = myWOpen * 0.99;
		if (myPositionSize === 0) {
			myPt = null;
		}
	}

	// Step 3 (fill check for the pending Buy limit order)
	if (myPositionSize === 0 && myDown1 !== null && low[myIndex] <= myDown1) {
		myPositionSize = 1;
		myAvgPrice = myDown1;
		myBeSent = false;
		myPt = myAvgPrice * 1.01;
		myBuyFilledThisBar = true;
	}

	// Step 4: break-even risk management after a -0.5% move
	if (myPositionSize > 0 && !myBeSent && myAvgPrice !== null && low[myIndex] < myAvgPrice * 0.995) {
		myPt = myAvgPrice;
		myBeSent = true;
		myBreakevenSetThisBar = true;
	}

	// Check fill of the Sell limit order (profit target or break-even)
	if (myPositionSize > 0 && myPt !== null && high[myIndex] >= myPt) {
		myProfitFilledThisBar = true;
		myPositionSize = 0;
		myAvgPrice = null;
		myPt = null;
		myBeSent = false;
	}

	// Step 5: hard exit at Friday close
	if (myIsFriday && myPositionSize > 0) {
		myPositionSize = 0;
		myAvgPrice = null;
		myPt = null;
		myBeSent = false;
		myFridayClosedThisBar = true;
	}

	const myBet = myAvgPrice !== null ? myAvgPrice * 0.995 : null;

	myWOpenArr[myIndex] = (myIsMonday || myPt !== null) ? null : myWOpen;
	myDown1Arr[myIndex] = (myIsMonday || myPt !== null) ? null : myDown1;
	myBetArr[myIndex] = myPositionSize > 0 ? myBet : null;
	myPtArr[myIndex] = myPositionSize > 0 ? myPt : null;

	myBuySignalArr[myIndex] = myBuyFilledThisBar;
	myProfitSignalArr[myIndex] = myProfitFilledThisBar;
	myBreakevenSetSignalArr[myIndex] = myBreakevenSetThisBar;
	myFridayCloseSignalArr[myIndex] = myFridayClosedThisBar;
}

paint(myWOpenArr, { name: 'Weekly Open', color: '#f5c518', style: 'line' });
paint(myDown1Arr, { name: 'Weekly OnePercentDip', color: '#2962ff', style: 'dotted' });
paint(myBetArr, { name: 'HalfPercentDrawdown', color: '#ff0000', style: 'dotted' });
paint(myPtArr, { name: 'ProfitTarget', color: '#00c853', style: 'line' });

register_signal(myBuySignalArr, 'Buy Entry Filled');
register_signal(myProfitSignalArr, 'Profit or Breakeven Exit Filled');
register_signal(myBreakevenSetSignalArr, 'Breakeven Stop Armed');
register_signal(myFridayCloseSignalArr, 'Friday Hard Exit');