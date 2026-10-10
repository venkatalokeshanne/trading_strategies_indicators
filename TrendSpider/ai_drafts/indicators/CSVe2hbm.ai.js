describe_indicator('Double CCI (Woodies Style)', 'lower');

// ─────────────────────────────────────────────
// Manual period inputs
// ─────────────────────────────────────────────
const myManualTab = input.tab('Manual Periods');
const myTrendCCIPeriodInput = myManualTab.number('TrendCCI Period (Manual)', 100, { min: 1, max: 500 });
const myEntryCCIPeriodInput = myManualTab.number('EntryCCI Period (Manual)', 14, { min: 1, max: 500 });
const myTurboCCIPeriodInput = myManualTab.number('TurboCCI Period (Manual)', 7, { min: 1, max: 500 });

const myGeneralTab = input.tab('General');
const myZeroCrossAlert = myGeneralTab.boolean('Zero Cross Alert', false);
const myAutoTimeframe = myGeneralTab.boolean('Automatic Timeframe Setting', true);

// ─────────────────────────────────────────────
// Per timeframe inputs
// ─────────────────────────────────────────────
const myTFTab = input.tab('Timeframe Settings');

const myM1Row = myTFTab.row();
const myM1Trend = myM1Row.number('M1 Trend', 55, { min: 1, max: 500 });
const myM1Entry = myM1Row.number('M1 Entry', 14, { min: 1, max: 500 });
const myM1Turbo = myM1Row.number('M1 Turbo', 7, { min: 1, max: 500 });

const myM5Row = myTFTab.row();
const myM5Trend = myM5Row.number('M5 Trend', 55, { min: 1, max: 500 });
const myM5Entry = myM5Row.number('M5 Entry', 14, { min: 1, max: 500 });
const myM5Turbo = myM5Row.number('M5 Turbo', 7, { min: 1, max: 500 });

const myM15Row = myTFTab.row();
const myM15Trend = myM15Row.number('M15 Trend', 55, { min: 1, max: 500 });
const myM15Entry = myM15Row.number('M15 Entry', 14, { min: 1, max: 500 });
const myM15Turbo = myM15Row.number('M15 Turbo', 7, { min: 1, max: 500 });

const myM30Row = myTFTab.row();
const myM30Trend = myM30Row.number('M30 Trend', 55, { min: 1, max: 500 });
const myM30Entry = myM30Row.number('M30 Entry', 21, { min: 1, max: 500 });
const myM30Turbo = myM30Row.number('M30 Turbo', 7, { min: 1, max: 500 });

const myH1Row = myTFTab.row();
const myH1Trend = myH1Row.number('H1 Trend', 55, { min: 1, max: 500 });
const myH1Entry = myH1Row.number('H1 Entry', 21, { min: 1, max: 500 });
const myH1Turbo = myH1Row.number('H1 Turbo', 7, { min: 1, max: 500 });

const myH4Row = myTFTab.row();
const myH4Trend = myH4Row.number('H4 Trend', 55, { min: 1, max: 500 });
const myH4Entry = myH4Row.number('H4 Entry', 21, { min: 1, max: 500 });
const myH4Turbo = myH4Row.number('H4 Turbo', 7, { min: 1, max: 500 });

const myD1Row = myTFTab.row();
const myD1Trend = myD1Row.number('D1 Trend', 55, { min: 1, max: 500 });
const myD1Entry = myD1Row.number('D1 Entry', 21, { min: 1, max: 500 });
const myD1Turbo = myD1Row.number('D1 Turbo', 7, { min: 1, max: 500 });

const myW1Row = myTFTab.row();
const myW1Trend = myW1Row.number('W1 Trend', 55, { min: 1, max: 500 });
const myW1Entry = myW1Row.number('W1 Entry', 21, { min: 1, max: 500 });
const myW1Turbo = myW1Row.number('W1 Turbo', 7, { min: 1, max: 500 });

const myMNRow = myTFTab.row();
const myMNTrend = myMNRow.number('MN Trend', 55, { min: 1, max: 500 });
const myMNEntry = myMNRow.number('MN Entry', 21, { min: 1, max: 500 });
const myMNTurbo = myMNRow.number('MN Turbo', 7, { min: 1, max: 500 });

// ─────────────────────────────────────────────
// Automatic period selection, based on current chart resolution.
// NOTE: Pine's timeframe.isminutes/isdaily/isweekly/ismonthly logic is
// approximated here by parsing TrendSpider's current.resolution string:
// a purely numeric string is treated as "minutes", "D" as daily,
// "W" as weekly, "M" as monthly.
// ─────────────────────────────────────────────
function myGetPeriods() {
	let myTrend = myTrendCCIPeriodInput;
	let myEntry = myEntryCCIPeriodInput;
	let myTurbo = myTurboCCIPeriodInput;

	if (myAutoTimeframe) {
		const myResolution = current.resolution;

		if (!isNaN(Number(myResolution))) {
			const myMultiplier = Number(myResolution);

			if (myMultiplier === 1) {
				myTrend = myM1Trend; myEntry = myM1Entry; myTurbo = myM1Turbo;
			}
			else if (myMultiplier === 5) {
				myTrend = myM5Trend; myEntry = myM5Entry; myTurbo = myM5Turbo;
			}
			else if (myMultiplier === 15) {
				myTrend = myM15Trend; myEntry = myM15Entry; myTurbo = myM15Turbo;
			}
			else if (myMultiplier === 30) {
				myTrend = myM30Trend; myEntry = myM30Entry; myTurbo = myM30Turbo;
			}
			else if (myMultiplier === 60) {
				myTrend = myH1Trend; myEntry = myH1Entry; myTurbo = myH1Turbo;
			}
			else if (myMultiplier === 240) {
				myTrend = myH4Trend; myEntry = myH4Entry; myTurbo = myH4Turbo;
			}
		}
		else if (myResolution === 'D') {
			myTrend = myD1Trend; myEntry = myD1Entry; myTurbo = myD1Turbo;
		}
		else if (myResolution === 'W') {
			myTrend = myW1Trend; myEntry = myW1Entry; myTurbo = myW1Turbo;
		}
		else if (myResolution === 'M') {
			myTrend = myMNTrend; myEntry = myMNEntry; myTurbo = myMNTurbo;
		}
	}

	return { trend: myTrend, entry: myEntry, turbo: myTurbo };
}

const myPeriods = myGetPeriods();

// ─────────────────────────────────────────────
// CCI calculations
// ─────────────────────────────────────────────
const myTrendCCI = cci(hlc3, myPeriods.trend);
const myEntryCCI = cci(hlc3, myPeriods.entry);
const myTurboCCI = cci(hlc3, myPeriods.turbo);

// ─────────────────────────────────────────────
// Woodies trend bars logic.
// Computed with a plain loop (not an indicator call) because it
// needs 2 running counters carried across candles.
// ─────────────────────────────────────────────
const myCciTrendUp = series_of(null);
const myCciTrendDown = series_of(null);
const myCciNoTrend = series_of(null);
const myCciTimeBar = series_of(null);

let myTrendUpCount = 0;
let myTrendDownCount = 0;

for (let myIndex = 0; myIndex < myTrendCCI.length; myIndex += 1) {
	const myValue = myTrendCCI[myIndex];

	if (myValue === null || myValue === undefined || isNaN(myValue)) {
		continue;
	}

	if (myValue >= 0) {
		myTrendUpCount += 1;
		myTrendDownCount = 0;

		if (myTrendUpCount === 5) {
			myCciTimeBar[myIndex] = myValue;
		}
		else if (myTrendUpCount > 5) {
			myCciTrendUp[myIndex] = myValue;
		}
		else {
			myCciNoTrend[myIndex] = myValue;
		}
	}
	else {
		myTrendDownCount += 1;
		myTrendUpCount = 0;

		if (myTrendDownCount === 5) {
			myCciTimeBar[myIndex] = myValue;
		}
		else if (myTrendDownCount > 5) {
			myCciTrendDown[myIndex] = myValue;
		}
		else {
			myCciNoTrend[myIndex] = myValue;
		}
	}
}

// ─────────────────────────────────────────────
// Zero cross signals
// ─────────────────────────────────────────────
const myTrendCCIPrev = shift(myTrendCCI, 1);

const myBullishCross = for_every(myTrendCCI, myTrendCCIPrev, myEntryCCI, (_trendNow, _trendPrev, _entryNow) =>
	_entryNow > 0 && _trendPrev <= 0 && _trendNow > 0
);

const myBearishCross = for_every(myTrendCCI, myTrendCCIPrev, myEntryCCI, (_trendNow, _trendPrev, _entryNow) =>
	_entryNow < 0 && _trendPrev >= 0 && _trendNow < 0
);

// Signals are always registered, regardless of the "Zero Cross Alert" toggle,
// since register_signal() must never be conditional. The toggle in Pine only
// controlled whether an alert() fired; here it has no effect on the signal
// outputs themselves (alerts are configured by the user in the platform UI).
register_signal(myBullishCross, 'Bullish Zero Cross');
register_signal(myBearishCross, 'Bearish Zero Cross');

// ─────────────────────────────────────────────
// Painting
// ─────────────────────────────────────────────
paint(myCciTrendUp, { name: 'Trend Up', color: 'green', style: 'column' });
paint(myCciTrendDown, { name: 'Trend Down', color: 'red', style: 'column' });
paint(myCciNoTrend, { name: 'No Trend', color: 'gray', style: 'column' });
paint(myCciTimeBar, { name: 'Time Bar', color: 'orange', style: 'column' });

paint(myTrendCCI, { name: 'Trend CCI', color: 'gray', thickness: 1 });
paint(myEntryCCI, { name: 'Entry CCI', color: 'silver', thickness: 1 });
paint(myTurboCCI, { name: 'Turbo CCI', color: 'red', thickness: 1 });

paint(horizontal_line(300), { name: 'Level Plus300', color: 'gray', style: 'dotted' });
paint(horizontal_line(200), { name: 'Level Plus200', color: 'gray', style: 'dotted' });
paint(horizontal_line(100), { name: 'Level Plus100', color: 'gray', style: 'dotted' });
paint(horizontal_line(50), { name: 'Level Plus50', color: 'gray', style: 'dotted' });
paint(horizontal_line(0), { name: 'Zero Line', color: 'orange' });
paint(horizontal_line(-50), { name: 'Level Minus50', color: 'gray', style: 'dotted' });
paint(horizontal_line(-100), { name: 'Level Minus100', color: 'gray', style: 'dotted' });
paint(horizontal_line(-200), { name: 'Level Minus200', color: 'gray', style: 'dotted' });
paint(horizontal_line(-300), { name: 'Level Minus300', color: 'gray', style: 'dotted' });