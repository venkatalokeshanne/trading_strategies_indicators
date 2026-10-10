describe_indicator('KOOB Pre-Trade Checklist');

// ─────────────────────────────────────────────
// CHECKLIST INPUTS
// ─────────────────────────────────────────────

const checklistTab = input.tab('Pre-Trade Checklist');
const myBiasOK = checklistTab.boolean('1. Clear Bias Plus Liquidity Draw', false);
const myHtfFVGOK = checklistTab.boolean('2. Higher Timeframe FVG', false);
const mySweepSMTOK = checklistTab.boolean('3. Lower TF Sweep SMT', false);
const myInverseFVGOK = checklistTab.boolean('4. Inverse FVG', false);
const myEntryModelOK = checklistTab.boolean('5. Entry Model Confirmed', false);

// ─────────────────────────────────────────────
// TABLE SETTINGS
// ─────────────────────────────────────────────

const styleTab = input.tab('Table Settings');
const myShowTable = styleTab.boolean('Show Checklist', true);
const myTablePosition = styleTab.select('Table Position', 'Top Right', ['Top Right', 'Top Left', 'Bottom Right', 'Bottom Left']);

// maps the Pine Script "position.*" naming to the overlay position
// values accepted by paint_overlay()
const myPositionMap = {
	'Top Right': 'top_right',
	'Top Left': 'top_left',
	'Bottom Right': 'bottom_right',
	'Bottom Left': 'bottom_left'
};
const myPos = myPositionMap[myTablePosition];

// ─────────────────────────────────────────────
// STATUS
// ─────────────────────────────────────────────

const myAllConfirmed = myBiasOK && myHtfFVGOK && mySweepSMTOK && myInverseFVGOK && myEntryModelOK;

const myConfirmedCount =
	(myBiasOK ? 1 : 0) +
	(myHtfFVGOK ? 1 : 0) +
	(mySweepSMTOK ? 1 : 0) +
	(myInverseFVGOK ? 1 : 0) +
	(myEntryModelOK ? 1 : 0);

// ─────────────────────────────────────────────
// SCANNER / STRATEGY SIGNALS
// Since the checklist is driven by boolean inputs (not price data),
// these signals simply mirror the checklist state as of "now". They
// will be constant across history, since inputs don't vary per candle.
// ─────────────────────────────────────────────

register_signal(series_of(myBiasOK), 'Clear Bias And Liquidity Draw');
register_signal(series_of(myHtfFVGOK), 'Higher Timeframe FVG');
register_signal(series_of(mySweepSMTOK), 'Lower TF Sweep Or SMT');
register_signal(series_of(myInverseFVGOK), 'Inverse FVG');
register_signal(series_of(myEntryModelOK), 'Entry Model Confirmed');
register_signal(series_of(myAllConfirmed), 'All Conditions Met');

// ─────────────────────────────────────────────
// TABLE (overlay)
// ─────────────────────────────────────────────

const myStatusRow = {
	cells: [
		{ text: 'STATUS', color: 'white', background_color: 'rgb(20,20,20)' },
		{ text: myAllConfirmed ? 'READY' : 'NO TRADE', color: myAllConfirmed ? 'lime' : 'red', background_color: 'rgb(20,20,20)' }
	]
};

const myReminderRow = {
	cells: [
		{
			text: myAllConfirmed ? 'ALL CONDITIONS MET' : 'WAIT FOR CONFIRMATION',
			color: myAllConfirmed ? 'lime' : 'orange',
			background_color: 'rgb(15,15,15)',
			colspan: 2
		}
	]
};

function myChecklistRow(_label, _ok) {
	return {
		cells: [
			{ text: _label, color: 'white', background_color: 'rgb(35,35,35)' },
			{ text: _ok ? 'YES' : 'WAIT', color: _ok ? 'lime' : 'orange', background_color: 'rgb(35,35,35)' }
		]
	};
}

const myTableRows = [
	{
		cells: [
			{ text: 'KOOB TRADE CHECKLIST', color: 'white', background_color: 'rgb(25,25,25)' },
			{ text: `${myConfirmedCount}/5`, color: 'white', background_color: 'rgb(25,25,25)' }
		]
	},
	myChecklistRow('Clear Bias Plus Liquidity', myBiasOK),
	myChecklistRow('HTF FVG', myHtfFVGOK),
	myChecklistRow('LTF Sweep Or SMT', mySweepSMTOK),
	myChecklistRow('Inverse FVG', myInverseFVGOK),
	myChecklistRow('Entry Model Confirmed', myEntryModelOK),
	myStatusRow,
	myReminderRow
];

paint_overlay('KoobChecklistTable', { position: myPos }, {
	rows: myShowTable ? myTableRows : []
});