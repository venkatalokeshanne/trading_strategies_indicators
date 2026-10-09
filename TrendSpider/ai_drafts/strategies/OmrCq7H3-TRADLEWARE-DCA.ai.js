describe_indicator('Tradleware DCA', 'lower');

// NOTE: TrendSpider Custom JS API has no strategy/order/equity engine
// (no strategy.entry, strategy.close_all, strategy.equity, commission,
// slippage simulation). This indicator reproduces the DCA buy/sell
// LOGIC of the Pine script and manually simulates a simplified
// cash+position equity curve. Commission and slippage are approximated
// as a flat percentage deduction on each buy; exact TradingView fill
// mechanics (bar-open fills, slippage ticks) cannot be reproduced.

const myDateTab = input.tab('Date Range');
const myStartRow = myDateTab.row();
const myStartYear = myStartRow.number('Start Year', 2018, { min: 2000, max: 2099 });
const myStartMonth = myStartRow.number('Start Month', 1, { min: 1, max: 12 });
const myStartDay = myStartRow.number('Start Day', 1, { min: 1, max: 31 });
const myEndRow = myDateTab.row();
const myEndYear = myEndRow.number('End Year', 2099, { min: 2000, max: 2099 });
const myEndMonth = myEndRow.number('End Month', 12, { min: 1, max: 12 });
const myEndDay = myEndRow.number('End Day', 31, { min: 1, max: 31 });

const myFreqTab = input.tab('Frequency');
const myUseDayOfWeek = myFreqTab.boolean('Use Day of Week Mode', false);
const myBuyOnDayOfWeek = myFreqTab.number('Day of Week (1=Sun...7=Sat)', 2, { min: 1, max: 7 });
const myEveryXBars = myFreqTab.number('Every X Bars', 30, { min: 1, max: 1000 });

const myStrategyTab = input.tab('Strategy');
const myInitialCapital = myStrategyTab.number('Initial Capital', 10000, { min: 1 });
const myAmountPerBuy = myStrategyTab.number('Amount per buy', 100, { min: 1 });
const myCommissionPercent = myStrategyTab.number('Commission percent (approx)', 0.1, { min: 0, max: 10 });

const myMoment = library('moment-timezone');

const myStartTimestamp = myMoment.utc([myStartYear, myStartMonth - 1, myStartDay, 0, 0]).unix();
const myEndTimestamp = myMoment.utc([myEndYear, myEndMonth - 1, myEndDay, 23, 59]).unix();

assert(time.length > 0, 'No candle data available');

const myBuySignal = series_of(false);
const myCloseSignal = series_of(false);
const myEquity = series_of(null);

let myInvestedCapital = 0;
let myLastBuyBarIndex = 0;
let myCash = myInitialCapital;
let myUnits = 0;
const myLastIndex = close.length - 1;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// convert ISO day-of-week (1=Mon...7=Sun) to Pine convention (1=Sun...7=Sat)
	const myIsoDow = time_of(time[myIndex]).dayOfWeek;
	const myPineDow = myIsoDow === 7 ? 1 : myIsoDow + 1;

	const myTimeCondition = (time[myIndex] >= myStartTimestamp) &&
		(time[myIndex] <= myEndTimestamp) &&
		(myIndex !== myLastIndex);

	let myFreqCondition = false;
	if (myUseDayOfWeek) {
		myFreqCondition = myPineDow === myBuyOnDayOfWeek;
	}
	else {
		myFreqCondition = (myLastBuyBarIndex === 0) || (myIndex >= myLastBuyBarIndex + myEveryXBars);
	}

	const myLongCondition = myFreqCondition && myTimeCondition;

	if (myLongCondition) {
		myLastBuyBarIndex = myIndex;

		if (myInvestedCapital + myAmountPerBuy <= myInitialCapital) {
			const myCommissionCost = myAmountPerBuy * (myCommissionPercent / 100);
			const myUnitsBought = myAmountPerBuy / close[myIndex];

			myCash -= (myAmountPerBuy + myCommissionCost);
			myUnits += myUnitsBought;
			myInvestedCapital += myAmountPerBuy;

			myBuySignal[myIndex] = true;
		}
	}

	const myIsLastConfirmed = (myIndex === myLastIndex);
	if (myIsLastConfirmed || time[myIndex] > myEndTimestamp) {
		myCloseSignal[myIndex] = true;
	}

	myEquity[myIndex] = myCash + (myUnits * close[myIndex]);
}

paint(myEquity, { name: 'Equity', color: 'teal', thickness: 2, forceUsePriceAxis: false });

const myBuyMarks = for_every(myBuySignal, _buy => _buy ? constants.icons.arrow_up : null);
paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });

register_signal(myBuySignal, 'DCA Buy');
register_signal(myCloseSignal, 'DCA Close All');