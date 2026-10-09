describe_indicator('SPY 200SMA Entry Exit Strategy', 'price');

// === Inputs ===
const myTab = input.tab('Settings');
const mySmaGroup = myTab.group('Moving Average');
const mySmaLength = mySmaGroup.number('SMA Period', 200, { min: 1, max: 1000 });

const myThresholdGroup = myTab.group('Thresholds');
const myThresholdRow = myThresholdGroup.row();
const myEntryThreshold = myThresholdRow.number('Entry Threshold (%)', 0.04, { min: -1, max: 1, step: 0.01 });
const myExitThreshold = myThresholdRow.number('Exit Threshold (%)', 0.03, { min: -1, max: 1, step: 0.01 });

const myStartGroup = myTab.group('Start Date');
const myStartRow = myStartGroup.row();
const myStartYear = myStartRow.number('Start Year', 1995, { min: 1900, max: 2100 });
const myStartMonth = myStartRow.number('Start Month', 1, { min: 1, max: 12 });
const myStartDay = myStartRow.number('Start Day', 1, { min: 1, max: 31 });

// === Calculations (built-in functions, computed outside loops) ===
const mySma200 = sma(close, mySmaLength);
const myUpperThreshold = mult(mySma200, 1 + myEntryThreshold);
const myLowerThreshold = mult(mySma200, 1 - myExitThreshold);

// Date.UTC is a static method, not an instantiation, so it is allowed here.
const myStartTimestamp = Date.UTC(myStartYear, myStartMonth - 1, myStartDay, 0, 0, 0) / 1000;

const myCandleCount = close.length;

// Output series
const myEnterLongArr = series_of(null);
const myExitLongArr = series_of(null);
const myNewOpenArr = series_of(null);
const myNewCloseArr = series_of(null);
const myIsAnniversaryArr = series_of(null);
const myInPositionArr = series_of(null);
const myBuyLabelPriceArr = series_of(null);
const mySellLabelPriceArr = series_of(null);
const myAnniversaryLabelPriceArr = series_of(null);

// 366 days expressed in seconds, since TrendSpider time series uses Unix seconds.
const mySecondsIn366Days = 366 * 24 * 60 * 60;

let myPositionSize = 0;
let myTargetTime = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myIsAfterStart = time[myIndex] >= myStartTimestamp;
	const myEnterLong = myIsAfterStart && close[myIndex] > myUpperThreshold[myIndex];
	const myExitLong = myIsAfterStart && close[myIndex] < myLowerThreshold[myIndex];

	const myPrevPositionSize = myPositionSize;

	const myNewOpen = myEnterLong && myPositionSize === 0;
	const myNewClose = myExitLong && myPositionSize > 0;

	if (myNewOpen) {
		myPositionSize = 1;
	}
	if (myNewClose) {
		myPositionSize = 0;
	}

	// Capture entry time only when a brand new position starts
	if (myPositionSize > 0 && myPrevPositionSize === 0) {
		myTargetTime = time[myIndex] + mySecondsIn366Days;
	}

	// If position is closed, reset the timer
	if (myPositionSize === 0) {
		myTargetTime = null;
	}

	const myPrevTime = myIndex > 0 ? time[myIndex - 1] : null;
	const myIsAnniversary = myTargetTime != null
		&& time[myIndex] >= myTargetTime
		&& (myPrevTime == null || myPrevTime < myTargetTime);

	myEnterLongArr[myIndex] = myEnterLong;
	myExitLongArr[myIndex] = myExitLong;
	myNewOpenArr[myIndex] = myNewOpen;
	myNewCloseArr[myIndex] = myNewClose;
	myIsAnniversaryArr[myIndex] = myIsAnniversary;
	myInPositionArr[myIndex] = myPositionSize > 0;

	myBuyLabelPriceArr[myIndex] = myNewOpen ? low[myIndex] * 0.97 : null;
	mySellLabelPriceArr[myIndex] = myNewClose ? high[myIndex] * 1.03 : null;
	myAnniversaryLabelPriceArr[myIndex] = myIsAnniversary ? high[myIndex] : null;
}

// === Visuals ===
const mySmaLinePainted = paint(mySma200, { name: 'SMA200', color: '#FF00F2', thickness: 2 });
const myUpperLinePainted = paint(myUpperThreshold, { name: 'Entry Threshold', color: '#00C800', thickness: 1 });
paint(myLowerThreshold, { name: 'Exit Threshold', color: '#FF0000', thickness: 1 });

fill(mySmaLinePainted, myUpperLinePainted, 'green', 0.2);

// Buy / Sell / Anniversary markers
paint(myBuyLabelPriceArr, { name: 'Buy Phase1', style: 'labels_below', color: '#00FF00' });
paint(mySellLabelPriceArr, { name: 'Sell Phase3', style: 'labels_above', color: '#FF0000' });
paint(myAnniversaryLabelPriceArr, { name: 'Anniversary Phase2', style: 'labels_above', color: '#FFD700' });

// === Scanner / Alert / Strategy signals ===
register_signal(myEnterLongArr, 'Enter Long Signal');
register_signal(myExitLongArr, 'Exit Long Signal');
register_signal(myNewOpenArr, 'Buy Phase1 Signal');
register_signal(myNewCloseArr, 'Sell Phase3 Signal');
register_signal(myIsAnniversaryArr, 'Anniversary Phase2 Signal');
register_signal(myInPositionArr, 'In Position');