describe_indicator('ADR Panel and Current Day Range');

// Fetch daily history for the current ticker; need current (forming) day
// plus 6 fully completed prior days.
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, "Error fetching daily data: " + myDailyData.error);

const myDayCount = myDailyData.high.length;
assert(myDayCount >= 7, "Not enough daily history to compute ADR");

// Last element is the current (live, forming) day.
const myTodayHigh = myDailyData.high[myDayCount - 1];
const myTodayLow = myDailyData.low[myDayCount - 1];
const myTodayRange = myTodayHigh - myTodayLow;

// Completed days, offset by 1 (yesterday) through 6.
const myYH1 = myDailyData.high[myDayCount - 2];
const myYL1 = myDailyData.low[myDayCount - 2];
const myYH2 = myDailyData.high[myDayCount - 3];
const myYL2 = myDailyData.low[myDayCount - 3];
const myYH3 = myDailyData.high[myDayCount - 4];
const myYL3 = myDailyData.low[myDayCount - 4];
const myYH4 = myDailyData.high[myDayCount - 5];
const myYL4 = myDailyData.low[myDayCount - 5];
const myYH5 = myDailyData.high[myDayCount - 6];
const myYL5 = myDailyData.low[myDayCount - 6];
const myYH6 = myDailyData.high[myDayCount - 7];
const myYL6 = myDailyData.low[myDayCount - 7];

const myYesterdayRange = myYH1 - myYL1;
const myRange2 = myYH2 - myYL2;
const myRange3 = myYH3 - myYL3;
const myRange4 = myYH4 - myYL4;
const myRange5 = myYH5 - myYL5;
const myRange6 = myYH6 - myYL6;

const myAdr3 = (myRange2 + myRange3 + myRange4) / 3.0;
const myAdr5 = (myRange2 + myRange3 + myRange4 + myRange5 + myRange6) / 5.0;

const myBreak3 = myYesterdayRange > myAdr3;
const myBreak5 = myYesterdayRange > myAdr5;

// Pine's fmt() floors the value for display, keeping full precision for math.
function myFormat(_value) {
	return "$" + Math.floor(_value).toString();
}

function myStatusText(_isBreak) {
	return _isBreak ? "BREAK" : "NO BREAK";
}

function myStatusColor(_isBreak) {
	return _isBreak ? "red" : "green";
}

const myHeaderBg = "#1F4E79";
const myDarkBg = "#373737";

paint_overlay('ADRPanel', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: current.ticker, color: 'white', background_color: myHeaderBg, bold: true },
			{ text: 'VALUE', color: 'white', background_color: myHeaderBg, bold: true },
			{ text: 'STATUS', color: 'white', background_color: myHeaderBg, bold: true }
		]
	}, {
		cells: [
			{ text: 'TODAY RANGE', bold: true },
			{ text: myFormat(myTodayRange), bold: true },
			{ text: 'LIVE', background_color: myDarkBg, color: 'white', bold: true }
		]
	}, {
		cells: [
			{ text: 'YESTERDAY RANGE', bold: true },
			{ text: myFormat(myYesterdayRange), bold: true },
			{ text: '—', bold: true }
		]
	}, {
		cells: [
			{ text: '3D ADR', bold: true },
			{ text: myFormat(myAdr3), bold: true },
			{ text: myStatusText(myBreak3), background_color: myStatusColor(myBreak3), color: 'white', bold: true }
		]
	}, {
		cells: [
			{ text: '5D ADR', bold: true },
			{ text: myFormat(myAdr5), bold: true },
			{ text: myStatusText(myBreak5), background_color: myStatusColor(myBreak5), color: 'white', bold: true }
		]
	}, {
		cells: [
			{ text: '3D INPUTS', background_color: myDarkBg, color: 'white', bold: true },
			{ text: myFormat(myRange2) + " + " + myFormat(myRange3) + " + " + myFormat(myRange4), background_color: myDarkBg, color: 'white', bold: true },
			{ text: '', background_color: myDarkBg }
		]
	}, {
		cells: [
			{ text: '5D INPUTS', background_color: myDarkBg, color: 'white', bold: true },
			{ text: myFormat(myRange2) + " + " + myFormat(myRange3) + " + " + myFormat(myRange4) + " + " + myFormat(myRange5) + " + " + myFormat(myRange6), background_color: myDarkBg, color: 'white', bold: true },
			{ text: '', background_color: myDarkBg }
		]
	}]
});

// Expose values and signals for use in Scanners, Alerts and Strategy Tester.
register_signal(series_of(myBreak3), "3D ADR Break");
register_signal(series_of(myBreak5), "5D ADR Break");
register_signal(series_of(myTodayRange), "Today Range");
register_signal(series_of(myYesterdayRange), "Yesterday Range");
register_signal(series_of(myAdr3), "3D ADR Value");
register_signal(series_of(myAdr5), "5D ADR Value");