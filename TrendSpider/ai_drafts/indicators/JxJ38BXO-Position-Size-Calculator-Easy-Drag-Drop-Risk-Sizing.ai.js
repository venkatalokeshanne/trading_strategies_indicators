// NOTE: This is an approximation. TrendSpider Custom JS API has no
// click-to-chart price inputs (Pine's input.price with confirm=true),
// no table.new()/line.new()/label.new() objects, and no syminfo.pointvalue.
// We rebuilt the same math using input.number() for stop/entry prices,
// a manual "$ per point per contract" input instead of syminfo.pointvalue,
// line()/paint_label_at_line() for the stop/entry lines, and
// paint_overlay() for the info table. Logic (contract math) is identical.
describe_indicator('Position Size Calculator', 'price');

const myRiskTab = input.tab('Risk');
const myRiskDollars = myRiskTab.number('Risk per trade $', 200, { min: 1, step: 10 });
const myRiskBuffer = myRiskTab.number('Allowed overage $', 25, { min: 0, step: 5 });

const myStopTab = input.tab('Stop');
const myStopMode = myStopTab.select('Stop input mode', 'Price line', ['Price line', 'Manual points']);
const myStopPrice = myStopTab.number('Stop price (manual)', 0, { min: 0, step: 0.01 });
const myEntryPrice = myStopTab.number('Entry price (manual)', 0, { min: 0, step: 0.01 });
const myStopPtsManual = myStopTab.number('Stop points (manual)', 25, { min: 0.01, step: 0.25 });

const myContractTab = input.tab('Contract');
const mySizeIn = myContractTab.select('Size contracts in', 'Micros (MNQ/MES)', ['This chart contract', 'Micros (MNQ/MES)']);
// syminfo.pointvalue has no equivalent in this API, so we expose it manually.
// Shortened the title below because the input() name length is limited.
const myPointValueFull = myContractTab.number('$ per point (full size)', 20, { min: 0.01, step: 0.01 });

const myTablePos = input.select('Table position', 'Top Right', ['Top Right', 'Top Left', 'Bottom Right', 'Bottom Left']);

// ── Calculation (mirrors Pine logic) ──────────────────────
const myUseLine = myStopMode === 'Price line' && myStopPrice > 0;
const myHasEntry = myEntryPrice > 0;
const myEntryLevel = myEntryPrice;
const myStopPoints = (myUseLine && myHasEntry) ? Math.abs(myEntryLevel - myStopPrice) : myStopPtsManual;

const myUseMicros = mySizeIn === 'Micros (MNQ/MES)';
const myPointValue = myUseMicros ? myPointValueFull / 10 : myPointValueFull;

const myRiskPerCtr = myStopPoints * myPointValue;
const myContracts = myRiskPerCtr > 0 ? Math.floor((myRiskDollars + myRiskBuffer) / myRiskPerCtr) : 0;
const myActualRisk = myContracts * myRiskPerCtr;
const myOverBudget = myActualRisk > myRiskDollars;
const myCtrLabel = myUseMicros ? 'MICRO CONTRACTS' : 'CONTRACTS';

// ── Stop / entry lines on the chart ───────────────────────
const myLastIndex = close.length - 1;
const myFromIndex = Math.max(0, myLastIndex - 20);
const myToIndex = myLastIndex + 10;

const myStopLineValues = (myUseLine && myLastIndex >= 0)
	? line(myFromIndex, myStopPrice, myToIndex, myStopPrice, false)
	: series_of(null);

const myEntryLineValues = (myUseLine && myHasEntry && myLastIndex >= 0)
	? line(myFromIndex, myEntryLevel, myToIndex, myEntryLevel, false)
	: series_of(null);

const myStopLinePainted = paint(myStopLineValues, { name: 'StopLine', color: 'red', thickness: 2, style: 'dotted' });
const myEntryLinePainted = paint(myEntryLineValues, { name: 'EntryLine', color: 'blue', thickness: 2, style: 'dotted' });

if (myUseLine && myLastIndex >= 0) {
	const myStopLabelText = 'STOP ' + myStopPoints.toFixed(2) + ' pts -> ' + myContracts + (myUseMicros ? ' micros' : ' contracts');
	paint_label_at_line(myStopLinePainted, myLastIndex, myStopLabelText, { color: 'white', background_color: 'red' });

	if (myHasEntry) {
		paint_label_at_line(myEntryLinePainted, myLastIndex, 'ENTRY', { color: 'white', background_color: 'blue' });
	}
}

// ── Info table overlay ─────────────────────────────────────
const myPositionMap = {
	'Top Right': 'top_right',
	'Top Left': 'top_left',
	'Bottom Right': 'bottom_right',
	'Bottom Left': 'bottom_left'
};

const myOkColor = myContracts > 0 ? '#006600' : 'red';
const myHeadBg = 'rgba(0,255,255,0.4)';
const myCellBg = 'rgba(192,192,192,0.6)';

paint_overlay('PositionSizeTable', { position: myPositionMap[myTablePos] }, {
	rows: [
		{ cells: [
			{ text: 'POSITION SIZE', color: 'black', background_color: myHeadBg },
			{ text: current.ticker + (myUseMicros ? ' micros' : ''), color: 'black', background_color: myHeadBg }
		]},
		{ cells: [
			{ text: 'Risk', color: 'black', background_color: myCellBg },
			{ text: '$' + myRiskDollars.toFixed(2), color: 'black', background_color: myCellBg }
		]},
		{ cells: [
			{ text: 'Stop', color: 'black', background_color: myCellBg },
			{ text: myStopPoints.toFixed(2) + ' pts', color: 'black', background_color: myCellBg }
		]},
		{ cells: [
			{ text: '$/pt/contract', color: 'black', background_color: myCellBg },
			{ text: '$' + myPointValue.toFixed(2), color: 'black', background_color: myCellBg }
		]},
		{ cells: [
			{ text: 'Risk per contract', color: 'black', background_color: myCellBg },
			{ text: '$' + myRiskPerCtr.toFixed(2), color: 'black', background_color: myCellBg }
		]},
		{ cells: [
			{ text: myCtrLabel, color: 'black', background_color: myHeadBg },
			{ text: String(myContracts) + (myContracts === 0 ? ' (stop too wide)' : ''), color: myOkColor, background_color: myHeadBg }
		]},
		{ cells: [
			{ text: 'Actual risk', color: 'black', background_color: myCellBg },
			{ text: '$' + myActualRisk.toFixed(2), color: 'black', background_color: myCellBg }
		]}
	]
});

// ── Scanner/Strategy signals ───────────────────────────────
const mySizeValidSignal = series_of(myContracts > 0);
const myOverBudgetSignal = series_of(myOverBudget);
register_signal(mySizeValidSignal, 'Position Size Valid');
register_signal(myOverBudgetSignal, 'Over Risk Budget');