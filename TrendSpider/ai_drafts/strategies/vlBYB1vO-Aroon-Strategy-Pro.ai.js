// Reproduction of a TradingView Pine Script v6 strategy ("Aroon Strategy Pro - Whale Edition").
// This is a best-effort port: TrendSpider has no native line.new()/table.new() or
// syminfo.mintick, so trade levels are painted as price-axis series instead of
// dynamic line objects, and mintick is approximated from current.decimals.
describe_indicator('Aroon Strategy Pro - Whale Edition', 'price');

const myTradeTab = input.tab('Trade Management');
const myAroonLength = myTradeTab.number('Aroon Length', 14, { min: 1, max: 200 });
const myRiskReward = myTradeTab.number('Risk Reward Ratio', 1.5, { min: 0.1, max: 50 });
const mySlPips = myTradeTab.number('Fixed SL Pips Points', 20.0, { min: 1.0, max: 100000 });
const myTpTicks = myTradeTab.number('Ticks Beyond TP', 2, { min: 0, max: 1000 });

const myBeTab = input.tab('Break Even');
const myUseBe = myBeTab.boolean('Enable Break Even', true);
const myBeAtRr = myBeTab.number('Move To BE At RR', 1.0, { min: 0.1, max: 50 });

const myTrendTab = input.tab('Trend Filter');
const myUseFilter = myTrendTab.boolean('Use Trend Filter', true);
const mySmaLen = myTrendTab.number('SMA Length', 290, { min: 1, max: 1000 });
const myEmaLen = myTrendTab.number('EMA Length', 200, { min: 1, max: 1000 });

const myCandleCount = close.length;
const mySmaVal = sma(close, mySmaLen);
const myEmaVal = ema(close, myEmaLen);

// Approximate syminfo.mintick, which has no direct equivalent in this API.
const myMinTick = Math.pow(10, -(current.decimals || 2));
const myTickVal = myMinTick * 10;

// --- Aroon via manual highestbars/lowestbars offset computation ---
// NOTE: "new Array(...)" is prohibited by the engine (no "new" keyword allowed).
// Replaced with Array(n).fill(...), which is equivalent but does not use "new".
const myAroonUp = Array(myCandleCount).fill(null);
const myAroonDown = Array(myCandleCount).fill(null);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myIndex < myAroonLength) continue;

	let myMaxIndex = myIndex;
	let myMaxValue = high[myIndex];
	let myMinIndex = myIndex;
	let myMinValue = low[myIndex];

	for (let myOffset = 1; myOffset <= myAroonLength; myOffset += 1) {
		const myCandidate = myIndex - myOffset;

		if (high[myCandidate] > myMaxValue) {
			myMaxValue = high[myCandidate];
			myMaxIndex = myCandidate;
		}
		if (low[myCandidate] < myMinValue) {
			myMinValue = low[myCandidate];
			myMinIndex = myCandidate;
		}
	}

	const myHighestBarsOffset = myMaxIndex - myIndex;
	const myLowestBarsOffset = myMinIndex - myIndex;

	myAroonUp[myIndex] = 100 * (myHighestBarsOffset + myAroonLength) / myAroonLength;
	myAroonDown[myIndex] = 100 * (myLowestBarsOffset + myAroonLength) / myAroonLength;
}

// --- Trend filter ---
const myTrendLong = Array(myCandleCount).fill(true);
const myTrendShort = Array(myCandleCount).fill(true);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (!myUseFilter) {
		myTrendLong[myIndex] = true;
		myTrendShort[myIndex] = true;
	}
	else {
		myTrendLong[myIndex] = close[myIndex] > mySmaVal[myIndex] && close[myIndex] > myEmaVal[myIndex];
		myTrendShort[myIndex] = close[myIndex] < mySmaVal[myIndex] && close[myIndex] < myEmaVal[myIndex];
	}
}

// --- Output series ---
const myLongSignalSeries = Array(myCandleCount).fill(false);
const myShortSignalSeries = Array(myCandleCount).fill(false);
const myWinSignalSeries = Array(myCandleCount).fill(false);
const myLossSignalSeries = Array(myCandleCount).fill(false);
const myBeSignalSeries = Array(myCandleCount).fill(false);

const myEntryLevel = Array(myCandleCount).fill(null);
const mySlLevel = Array(myCandleCount).fill(null);
const myTpLevel = Array(myCandleCount).fill(null);

const myWinMarker = Array(myCandleCount).fill(null);
const myLossMarker = Array(myCandleCount).fill(null);
const myBeMarker = Array(myCandleCount).fill(null);

// --- Trade state machine ---
let myInTrade = false;
let myTradeDir = 0;
let myEntryPrice = 0;
let mySlPrice = 0;
let myTpPrice = 0;
let myBeTriggerPrice = 0;
let myLastExitBar = -2;
let myWins = 0;
let myLosses = 0;
let myBes = 0;

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	if (myInTrade) {
		myEntryLevel[myIndex] = myEntryPrice;
		mySlLevel[myIndex] = mySlPrice;
		myTpLevel[myIndex] = myTpPrice;

		if (myUseBe) {
			const myBeHit = (myTradeDir === 1 && high[myIndex] >= myBeTriggerPrice) ||
				(myTradeDir === -1 && low[myIndex] <= myBeTriggerPrice);

			if (myBeHit) {
				mySlPrice = myEntryPrice;
			}
		}

		const myTpTrigger = myTpPrice + (myTradeDir * myTpTicks * myMinTick);
		const myHitTp = (myTradeDir === 1 && high[myIndex] >= myTpTrigger) ||
			(myTradeDir === -1 && low[myIndex] <= myTpTrigger);
		const myHitSl = (myTradeDir === 1 && low[myIndex] <= mySlPrice) ||
			(myTradeDir === -1 && high[myIndex] >= mySlPrice);

		if (myHitTp) {
			myWins += 1;
			myWinMarker[myIndex] = high[myIndex];
			myWinSignalSeries[myIndex] = true;
			myInTrade = false;
			myLastExitBar = myIndex;
		}
		else if (myHitSl) {
			if (mySlPrice === myEntryPrice) {
				myBes += 1;
				myBeMarker[myIndex] = high[myIndex];
				myBeSignalSeries[myIndex] = true;
			}
			else {
				myLosses += 1;
				myLossMarker[myIndex] = low[myIndex];
				myLossSignalSeries[myIndex] = true;
			}
			myInTrade = false;
			myLastExitBar = myIndex;
		}
	}

	const myCanEnter = myIndex > myLastExitBar + 1;

	const myLongSignal = (myAroonDown[myIndex] !== null && myAroonUp[myIndex] !== null &&
		myAroonDown[myIndex - 1] !== null && myAroonUp[myIndex - 1] !== null) &&
		(myAroonDown[myIndex - 1] >= myAroonUp[myIndex - 1] && myAroonDown[myIndex] < myAroonUp[myIndex]) &&
		!myInTrade && myTrendLong[myIndex] && myCanEnter;

	const myShortSignal = (myAroonDown[myIndex] !== null && myAroonUp[myIndex] !== null &&
		myAroonDown[myIndex - 1] !== null && myAroonUp[myIndex - 1] !== null) &&
		(myAroonDown[myIndex - 1] <= myAroonUp[myIndex - 1] && myAroonDown[myIndex] > myAroonUp[myIndex]) &&
		!myInTrade && myTrendShort[myIndex] && myCanEnter;

	if (myLongSignal || myShortSignal) {
		myLongSignalSeries[myIndex] = myLongSignal;
		myShortSignalSeries[myIndex] = myShortSignal;
		myInTrade = true;
		myEntryPrice = close[myIndex];
		myTradeDir = myLongSignal ? 1 : -1;
		mySlPrice = myEntryPrice - (myTradeDir * mySlPips * myTickVal);
		myTpPrice = myEntryPrice + (myTradeDir * mySlPips * myTickVal * myRiskReward);
		myBeTriggerPrice = myEntryPrice + (myTradeDir * mySlPips * myTickVal * myBeAtRr);
		myEntryLevel[myIndex] = myEntryPrice;
		mySlLevel[myIndex] = mySlPrice;
		myTpLevel[myIndex] = myTpPrice;
	}
}

paint(myUseFilter ? mySmaVal : constants.empty_series, { name: 'SMA Filter', color: '#4DA3FF', thickness: 1 });
paint(myUseFilter ? myEmaVal : constants.empty_series, { name: 'EMA Filter', color: '#FFD54F', thickness: 1 });

paint(myEntryLevel, { name: 'Entry Level', style: 'ladder', color: 'gray', thickness: 2 });
paint(mySlLevel, { name: 'SL Level', style: 'ladder', color: 'red', thickness: 2 });
paint(myTpLevel, { name: 'TP Level', style: 'ladder', color: 'green', thickness: 2 });

paint(myWinMarker, { name: 'Win Exit', style: 'labels_above', color: 'green' });
paint(myLossMarker, { name: 'Loss Exit', style: 'labels_below', color: 'red' });
paint(myBeMarker, { name: 'BE Exit', style: 'labels_above', color: 'orange' });

register_signal(myLongSignalSeries, 'Long Entry Signal');
register_signal(myShortSignalSeries, 'Short Entry Signal');
register_signal(myWinSignalSeries, 'Win Exit Signal');
register_signal(myLossSignalSeries, 'Loss Exit Signal');
register_signal(myBeSignalSeries, 'Break Even Exit Signal');

paint_overlay('TradeStats', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Trade Stats', color: 'white' }] },
		{ cells: [{ text: 'Wins ' + myWins, color: '#2ca599' }] },
		{ cells: [{ text: 'Losses ' + myLosses, color: '#ee5451' }] },
		{ cells: [{ text: 'BE ' + myBes, color: 'orange' }] }
	]
});