describe_indicator('TASC 2026.08 An Ag Selling Model', 'price');

// NOTE: Pine Script strategy() entries/exits (strategy.entry,
// strategy.close_all, pyramiding) have no direct equivalent in
// TrendSpider Custom JS. This script reproduces the underlying
// signal logic (sell signals, cover signals, active period,
// crop-year resets) as series you can scan, alert on, or
// backtest via register_signal(). Pyramiding limit of 3 open
// trades (as in the original strategy() declaration) is
// hardcoded, matching the Pine code, since it is not exposed
// as an input in the original script either.

const myTab1 = input.tab('Average & Sell Level Settings');
const mySrc = myTab1.select('Source', 'close', constants.price_source_options);
const myLen = myTab1.number('MA Length', 40, { min: 1, max: 500 });
const myAtrLen = myTab1.number('ATR Length', 20, { min: 1, max: 500 });
const myAtrMulti = myTab1.number('ATR Factor', 2.5, { min: 0.1, max: 20 });

const myTab2 = input.tab('Strategy Settings');
const myHarvestMonth = myTab2.number('Month Of Harvest', 11, { min: 1, max: 12 });
const myDelayMonths = myTab2.number('Delay In Months After Harvest', 2, { min: 0, max: 11 });
const myDaysBetween = myTab2.number('Days Between Trades', 30, { min: 1, max: 1000 });

const myPrice = market[mySrc];
const myTrend = sma(myPrice, myLen);
const myAtr = atr(high, low, close, myAtrLen);
const mySellLevel = add(myTrend, mult(myAtr, myAtrMulti));

const myPyramidLimit = 3;

// Figure out the "begin sale month", matching Pine's modulo logic
let myBeginSaleMonth = (myHarvestMonth + myDelayMonths + 1) % 12;
if (myBeginSaleMonth === 0) {
	myBeginSaleMonth = 12;
}

// Month (1-based) for every candle, using exchange time zone
const myMonthSeries = time.map(_t => time_of(_t).month + 1);

const myN = close.length;
const mySellSignal = series_of(false);
const myCoverSignal = series_of(false);
const myActiveSeries = series_of(false);
const myNewCropYearSeries = series_of(false);
const myIsHarvestMonthSeries = series_of(false);

let myActive = false;
let myDaysSince = 0;
let myOpenCount = 0;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myIsHarvestMonth = myMonthSeries[myIndex] === myHarvestMonth;
	const myPrevIsHarvestMonth = myIndex > 0 ? myMonthSeries[myIndex - 1] === myHarvestMonth : false;
	const myNewCropYr = myIsHarvestMonth && !myPrevIsHarvestMonth;
	const myPrevMonth = myIndex > 0 ? myMonthSeries[myIndex - 1] : null;

	if (myNewCropYr) {
		myActive = false;
		myDaysSince = 0;
		myOpenCount = 0;
	}

	if (myMonthSeries[myIndex] === myBeginSaleMonth && myPrevMonth !== myBeginSaleMonth) {
		myActive = true;
	}

	if (myOpenCount > 0) {
		myDaysSince += 1;
	}

	let mySell = false;
	let myCover = false;

	if (myActive && high[myIndex] >= mySellLevel[myIndex]) {
		if (myOpenCount === 0) {
			mySell = true;
			myDaysSince = 0;
			myOpenCount += 1;
		}
		else if (myDaysSince >= myDaysBetween && myOpenCount < myPyramidLimit) {
			mySell = true;
			myDaysSince = 0;
			myOpenCount += 1;
		}
	}

	if (!myActive) {
		if (myOpenCount > 0) {
			myCover = true;
		}
		myOpenCount = 0;
	}

	mySellSignal[myIndex] = mySell;
	myCoverSignal[myIndex] = myCover;
	myActiveSeries[myIndex] = myActive;
	myNewCropYearSeries[myIndex] = myNewCropYr;
	myIsHarvestMonthSeries[myIndex] = myIsHarvestMonth;
}

// Average and sell level lines, matching the Pine plots
paint(myTrend, { name: 'Average', color: 'orange', thickness: 2 });
paint(mySellLevel, { name: 'SellLevel', color: 'blue', thickness: 2 });

// Candle coloring as an approximation of the Pine bgcolor() logic:
// yellow-ish for harvest month, reddish when trades are not allowed
const myCandleColors = for_every(
	myIsHarvestMonthSeries,
	myActiveSeries,
	(_isHarvest, _active) => {
		if (_isHarvest) return '#ffeb3b';
		if (!_active) return '#ff5252';
		return null;
	}
);
color_candles(myCandleColors);

// Signals exposed for scanners, alerts and backtests
register_signal(mySellSignal, 'Sell Signal');
register_signal(myCoverSignal, 'Cover Signal');
register_signal(myActiveSeries, 'Active Period');
register_signal(myNewCropYearSeries, 'New Crop Year');