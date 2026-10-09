describe_indicator('Setup Checklist', 'price');

// This is a manual checklist tool, not a calculated indicator.
// Each checkbox is a boolean input the trader ticks manually as
// their setup develops. The table and signals simply reflect the
// state of these checkboxes - there is no price-based calculation.

const checklistTab = input.tab('Checklist - tick in order');
const myStep1 = checklistTab.boolean('1. Draw identified (session H/L named + price)', false);
const myStep2 = checklistTab.boolean('2. Manipulation into the opposite side (sweep)', false);
const myStep3 = checklistTab.boolean('3. Sweep landed inside 15m+ FVG', false);
const myStep4 = checklistTab.boolean('4. Reaction off the gap (rejection)', false);
const myStep5 = checklistTab.boolean('5. V-shaped recovery (sharp displacement)', false);
const myStep6 = checklistTab.boolean('6. iFVG formed', false);
const myStep7 = checklistTab.boolean('7. Entry: iFVG retest / stop at wick / target = draw', false);

const displayTab = input.tab('Display');
const myPosition = displayTab.select('Table Position', 'bottom_right', ['top_right', 'middle_right', 'bottom_right', 'top_left', 'bottom_left']);
const myTextSize = displayTab.select('Text Size', 'small', ['tiny', 'small', 'normal']);

// Count how many steps are checked
const myCompletedCount = (myStep1 ? 1 : 0) + (myStep2 ? 1 : 0) + (myStep3 ? 1 : 0) +
	(myStep4 ? 1 : 0) + (myStep5 ? 1 : 0) + (myStep6 ? 1 : 0) + (myStep7 ? 1 : 0);

const myAllDone = myCompletedCount === 7;

// Determine which step the trader is waiting on, mirroring the
// nested ternary chain from the Pine Script, in order.
let myNextStepText = 'ALL CLEAR TAKE IT';
if (!myStep1) {
	myNextStepText = 'STEP 1 NAME THE DRAW';
}
else if (!myStep2) {
	myNextStepText = 'WAIT SWEEP';
}
else if (!myStep3) {
	myNextStepText = 'CHECK 15m FVG';
}
else if (!myStep4) {
	myNextStepText = 'WAIT REACTION';
}
else if (!myStep5) {
	myNextStepText = 'WAIT V SHAPE';
}
else if (!myStep6) {
	myNextStepText = 'WAIT iFVG';
}
else if (!myStep7) {
	myNextStepText = 'SET ENTRY PLAN';
}

function myRowCells(_label, _done) {
	return [
		{ text: _label, color: _done ? '#000000' : 'rgba(128,128,128,0.7)' },
		{ text: _done ? 'OK' : 'X', color: _done ? '#008000' : '#d00000' }
	];
}

const myHeaderColor = myAllDone ? '#008000' : '#000000';
const myFooterTextColor = myAllDone ? '#ffffff' : '#000000';
const myFooterBgColor = myAllDone ? '#008000' : 'rgba(255,165,0,0.3)';

paint_overlay('SetupChecklistTable', { position: myPosition }, {
	rows: [
		{
			cells: [
				{ text: 'SWEEP TO DRAW', color: '#000000' },
				{ text: myCompletedCount + '/7', color: myHeaderColor }
			]
		},
		{ cells: myRowCells('1 Draw identified', myStep1) },
		{ cells: myRowCells('2 Manipulation sweep', myStep2) },
		{ cells: myRowCells('3 Inside 15m+ FVG', myStep3) },
		{ cells: myRowCells('4 Reaction off gap', myStep4) },
		{ cells: myRowCells('5 V-shape recovery', myStep5) },
		{ cells: myRowCells('6 iFVG formed', myStep6) },
		{ cells: myRowCells('7 Entry plan set', myStep7) },
		{
			cells: [
				{ text: myNextStepText, color: myFooterTextColor, backgroundColor: myFooterBgColor },
				{ text: '', backgroundColor: myFooterBgColor }
			]
		}
	]
});

// Expose signals so this checklist can be used in scanners, alerts
// and strategy tester. Signals are constant across all candles since
// they only depend on the manual checkbox inputs (not price action).
const myAllStepsSignal = series_of(myAllDone);
const myStep1Signal = series_of(myStep1);
const myStep2Signal = series_of(myStep2);
const myStep3Signal = series_of(myStep3);
const myStep4Signal = series_of(myStep4);
const myStep5Signal = series_of(myStep5);
const myStep6Signal = series_of(myStep6);
const myStep7Signal = series_of(myStep7);

register_signal(myAllStepsSignal, 'All Seven Steps Checked');
register_signal(myStep1Signal, 'Step1 Draw Identified');
register_signal(myStep2Signal, 'Step2 Manipulation Sweep');
register_signal(myStep3Signal, 'Step3 Inside 15m FVG');
register_signal(myStep4Signal, 'Step4 Reaction Off Gap');
register_signal(myStep5Signal, 'Step5 V Shape Recovery');
register_signal(myStep6Signal, 'Step6 iFVG Formed');
register_signal(myStep7Signal, 'Step7 Entry Plan Set');