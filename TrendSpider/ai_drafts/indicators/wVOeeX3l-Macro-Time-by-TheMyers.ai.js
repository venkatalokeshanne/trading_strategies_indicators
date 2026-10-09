describe_indicator('MACROS (NY Sessions Brackets)', 'price');
// ─────────────────────────────────────────────────────────────────────────
// NOTE: TrendSpider Custom JS has no box.new()/label.new() dynamic drawing
// API like Pine Script. This version reproduces the MACRO logic (session
// windows, running session high, offset/stacking math, labels & signals)
// using horizontal "ladder" lines (bracket top) + paint_label_at_line()
// for the text, and register_signal() for scanner/alert/strategy use.
// Visual result (a growing bracket box) is approximated by a flat line at
// the running session-high level, which is the closest equivalent available.
// ─────────────────────────────────────────────────────────────────────────
const myLabelMode = input.select('Label Mode', 'Name + Hour', ['Name + Hour', 'Only Name', 'Only Hour']);
const myOffsetBase = input.number('Distance Ticks', 35, { min: 0 });
const myStackStep = input.number('Macro Separation', 50, { min: 10 });
const myLineColor = 'black';

const futTab = input.tab('FUTURES');
const myU1 = futTab.boolean('Opening Range 930 1030', true);
const myU2 = futTab.boolean('Opening Range Bell 930 1000', true);
const myU3 = futTab.boolean('London 1st Macro 250 310', false);
const myU4 = futTab.boolean('London 2nd Macro 350 410', false);
const myU5 = futTab.boolean('Macro 520 540', false);
const myU6 = futTab.boolean('Macro 550 610', false);
const myU7 = futTab.boolean('Macro 750 810', false);
const myU8 = futTab.boolean('Macro 820 840', false);
const myU9 = futTab.boolean('Macro 850 910', false);
const myU10 = futTab.boolean('Macro 920 940', false);
const myU11 = futTab.boolean('Macro 930 945', true);
const myU12 = futTab.boolean('NY 1st Macro 950 1010', true);
const myU13 = futTab.boolean('Macro 1020 1040', true);
const myU14 = futTab.boolean('NY 2nd Macro 1050 1110', false);
const myU15 = futTab.boolean('Macro 1120 1140', false);
const myU16 = futTab.boolean('Pre NY Lunch 1130 1330', false);
const myU17 = futTab.boolean('Macro 1150 1210', false);
const myU18 = futTab.boolean('Lunch Hour 1200 1330', false);
const myU19 = futTab.boolean('Macro 1310 1340', false);
const myU20 = futTab.boolean('Macro 1420 1440', false);
const myU21 = futTab.boolean('Macro 1515 1545', false);
const myU22 = futTab.boolean('Macro 1550 1610', false);

// Tick size is not exposed by the Custom JS API. We approximate it from
// current.decimals (e.g. 2 decimals -> 0.01). This may not exactly match
// the real instrument's minimum tick (syminfo.mintick in Pine).
const myTick = Math.pow(10, -(current.decimals || 2));

// Session definitions: [enabled, codeName, displayName, timeLabel, fromH, fromM, toH, toM, level]
const mySessions = [
	[myU1, 'OpeningRange', 'Opening Range', '930 1030', 9, 30, 10, 30, 2],
	[myU2, 'OpeningRangeBell', 'Opening Range Bell', '930 1000', 9, 30, 10, 0, 1],
	[myU11, 'Macro930', 'MACRO', '930 945', 9, 30, 9, 45, 0],
	[myU3, 'LondonMacro1', 'LONDON 1st MACRO', '250 310', 2, 50, 3, 10, 0],
	[myU4, 'LondonMacro2', 'LONDON 2nd MACRO', '350 410', 3, 50, 4, 10, 0],
	[myU5, 'Macro520', 'MACRO', '520 540', 5, 20, 5, 40, 0],
	[myU6, 'Macro550', 'MACRO', '550 610', 5, 50, 6, 10, 0],
	[myU7, 'Macro750', 'MACRO', '750 810', 7, 50, 8, 10, 0],
	[myU8, 'Macro820', 'MACRO', '820 840', 8, 20, 8, 40, 0],
	[myU9, 'Macro850', 'MACRO', '850 910', 8, 50, 9, 10, 0],
	[myU10, 'Macro920', 'MACRO', '920 940', 9, 20, 9, 40, 0],
	[myU12, 'NyMacro1', 'NY MACRO', '950 1010', 9, 50, 10, 10, 0],
	[myU13, 'Macro1020', 'MACRO', '1020 1040', 10, 20, 10, 40, 0],
	[myU14, 'NyMacro2', 'MACRO', '1050 1110', 10, 50, 11, 10, 0],
	[myU15, 'Macro1120', 'MACRO', '1120 1140', 11, 20, 11, 40, 0],
	[myU16, 'PreLunch', 'PRE LUNCH', '1130 1330', 11, 30, 13, 30, 1],
	[myU18, 'LunchHour', 'LUNCH HOUR', '1200 1330', 12, 0, 13, 30, 0],
	[myU17, 'Macro1150', 'MACRO', '1150 1210', 11, 50, 12, 10, 0],
	[myU19, 'Macro1310', 'MACRO', '1310 1340', 13, 10, 13, 40, 0],
	[myU20, 'Macro1420', 'MACRO', '1420 1440', 14, 20, 14, 40, 0],
	[myU21, 'Macro1515', 'MACRO', '1515 1545', 15, 15, 15, 45, 0],
	[myU22, 'Macro1550', 'MACRO', '1550 1610', 15, 50, 16, 10, 0]
];

const myCount = close.length;

// Precompute total-minutes-of-day for every candle once (NY time assumed
// equal to exchange time of current ticker; cross-timezone override is not
// available via time_of()).
// NOTE: replaced "new Array(myCount)" with "Array(myCount)" since the
// "new" keyword is prohibited by the scripting engine.
const myTotalMinutes = Array(myCount);
for (let myIndex = 0; myIndex < myCount; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	myTotalMinutes[myIndex] = myTimeInfo.hours * 60 + myTimeInfo.minutes;
}

mySessions.forEach(mySessionDef => {
	const [myEnabled, myCode, myName, myTimeLabel, myFromH, myFromM, myToH, myToM, myLevel] = mySessionDef;
	const myFromTotal = myFromH * 60 + myFromM;
	const myToTotal = myToH * 60 + myToM;

	// NOTE: replaced "new Array(myCount).fill(null)" with
	// "Array(myCount).fill(null)" since the "new" keyword is prohibited.
	const myBracketTop = Array(myCount).fill(null);
	let myRunningHigh = null;
	let myWasActive = false;

	for (let myIndex = 0; myIndex < myCount; myIndex += 1) {
		const myTotal = myTotalMinutes[myIndex];
		const myIsActive = myEnabled && myTotal >= myFromTotal && myTotal < myToTotal;

		if (myIsActive) {
			myRunningHigh = myWasActive ? Math.max(myRunningHigh, high[myIndex]) : high[myIndex];
			myBracketTop[myIndex] = myRunningHigh + (myOffsetBase * myTick) + (myLevel * myStackStep * myTick);
		}
		else {
			myRunningHigh = null;
		}
		myWasActive = myIsActive;
	}

	const myLinePainted = paint(myBracketTop, { name: myCode, color: myLineColor, style: 'ladder', thickness: 1 });

	// Label at the first candle of every occurrence of this session window.
	for (let myIndex = 0; myIndex < myCount; myIndex += 1) {
		const myIsStart = myBracketTop[myIndex] !== null && (myIndex === 0 || myBracketTop[myIndex - 1] === null);
		if (myIsStart) {
			const myLabelText = myLabelMode === 'Name + Hour' ? (myName + ' ' + myTimeLabel) :
				myLabelMode === 'Only Name' ? myName : myTimeLabel;
			paint_label_at_line(myLinePainted, myIndex, myLabelText, { color: myLineColor });
		}
	}

	// Signal for scanners/alerts/strategies: true while this macro window is active.
	const mySignal = myBracketTop.map(myValue => myValue !== null);
	register_signal(mySignal, myCode + 'Active');
});