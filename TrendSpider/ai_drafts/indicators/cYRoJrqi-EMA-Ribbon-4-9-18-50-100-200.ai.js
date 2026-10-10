describe_indicator('EMA Ribbon 4 9 18 50 100 200', 'price');

// ───────────── Inputs ─────────────
const myLengthsTab = input.tab('EMA Lengths');
const myLen1 = myLengthsTab.number('EMA 1', 4, { min: 1, max: 500 });
const myLen2 = myLengthsTab.number('EMA 2', 9, { min: 1, max: 500 });
const myLen3 = myLengthsTab.number('EMA 3', 18, { min: 1, max: 500 });
const myLen4 = myLengthsTab.number('EMA 4', 50, { min: 1, max: 500 });
const myLen5 = myLengthsTab.number('EMA 5', 100, { min: 1, max: 500 });
const myLen6 = myLengthsTab.number('EMA 6', 200, { min: 1, max: 500 });

const myToggleTab = input.tab('Show Hide');
const myShowRow1 = myToggleTab.row();
const myShow1 = myShowRow1.boolean('Show EMA 4', true);
const myShow2 = myShowRow1.boolean('Show EMA 9', true);
const myShowRow2 = myToggleTab.row();
const myShow3 = myShowRow2.boolean('Show EMA 18', true);
const myShow4 = myShowRow2.boolean('Show EMA 50', true);
const myShowRow3 = myToggleTab.row();
const myShow5 = myShowRow3.boolean('Show EMA 100', true);
const myShow6 = myShowRow3.boolean('Show EMA 200', true);

const myStyleTab = input.tab('Style');
const mySrcSelect = myStyleTab.select('Price source', 'close', constants.price_source_options);
const myShowFill = myStyleTab.boolean('Fill Between Fast Slow 4 and 9', true);
const myShowTable = myStyleTab.boolean('Show Status Table', true);

const mySource = market[mySrcSelect];

// ───────────── Calculations ─────────────
const myEma1 = ema(mySource, myLen1);
const myEma2 = ema(mySource, myLen2);
const myEma3 = ema(mySource, myLen3);
const myEma4 = ema(mySource, myLen4);
const myEma5 = ema(mySource, myLen5);
const myEma6 = ema(mySource, myLen6);

// ───────────── Plots ─────────────
const myLine1 = paint(myShow1 ? myEma1 : series_of(null), { name: 'EMA 4', color: '#00e5ff', thickness: 2 });
const myLine2 = paint(myShow2 ? myEma2 : series_of(null), { name: 'EMA 9', color: '#2962ff', thickness: 2 });
paint(myShow3 ? myEma3 : series_of(null), { name: 'EMA 18', color: '#00c853', thickness: 2 });
paint(myShow4 ? myEma4 : series_of(null), { name: 'EMA 50', color: '#ff9800', thickness: 2 });
paint(myShow5 ? myEma5 : series_of(null), { name: 'EMA 100', color: '#ff5252', thickness: 2 });
paint(myShow6 ? myEma6 : series_of(null), { name: 'EMA 200', color: '#9c27b0', thickness: 2 });

// fill between EMA4/EMA9, color depends on which is higher
color_cloud(
	myShowFill ? myEma1 : series_of(null),
	myShowFill ? myEma2 : series_of(null),
	'rgba(0,200,83,0.15)',
	'rgba(255,82,82,0.15)',
	'Bullish49',
	'Bearish49',
	1
);

// ───────────── Cross signals ─────────────
const myBullCross = for_every(myEma1, myEma2, (_e1, _e2, _prev, _idx) => _idx > 0 && myEma1[_idx] > myEma2[_idx] && myEma1[_idx - 1] <= myEma2[_idx - 1]);
const myBearCross = for_every(myEma1, myEma2, (_e1, _e2, _prev, _idx) => _idx > 0 && myEma1[_idx] < myEma2[_idx] && myEma1[_idx - 1] >= myEma2[_idx - 1]);

const myBullMarks = for_every(myBullCross, _c => _c ? constants.icons.triangle_up : null);
const myBearMarks = for_every(myBearCross, _c => _c ? constants.icons.triangle_down : null);

paint(myBullMarks, { style: 'labels_below', color: 'green', name: 'Bull Cross 4 9' });
paint(myBearMarks, { style: 'labels_above', color: 'red', name: 'Bear Cross 4 9' });

register_signal(myBullCross, 'EMA 4 9 Bullish Cross');
register_signal(myBearCross, 'EMA 4 9 Bearish Cross');

// ───────────── Status Table ─────────────
const myCloseLast = close.length - 1;
const myRows = [
	{ cells: [{ text: 'EMA', color: 'white' }, { text: 'Price vs EMA', color: 'white' }] },
	{ cells: [{ text: '4', color: '#00e5ff' }, { text: close[myCloseLast] > myEma1[myCloseLast] ? 'Above' : 'Below', color: close[myCloseLast] > myEma1[myCloseLast] ? 'green' : 'red' }] },
	{ cells: [{ text: '9', color: '#2962ff' }, { text: close[myCloseLast] > myEma2[myCloseLast] ? 'Above' : 'Below', color: close[myCloseLast] > myEma2[myCloseLast] ? 'green' : 'red' }] },
	{ cells: [{ text: '18', color: '#00c853' }, { text: close[myCloseLast] > myEma3[myCloseLast] ? 'Above' : 'Below', color: close[myCloseLast] > myEma3[myCloseLast] ? 'green' : 'red' }] },
	{ cells: [{ text: '50', color: '#ff9800' }, { text: close[myCloseLast] > myEma4[myCloseLast] ? 'Above' : 'Below', color: close[myCloseLast] > myEma4[myCloseLast] ? 'green' : 'red' }] },
	{ cells: [{ text: '100', color: '#ff5252' }, { text: close[myCloseLast] > myEma5[myCloseLast] ? 'Above' : 'Below', color: close[myCloseLast] > myEma5[myCloseLast] ? 'green' : 'red' }] },
	{ cells: [{ text: '200', color: '#9c27b0' }, { text: close[myCloseLast] > myEma6[myCloseLast] ? 'Above' : 'Below', color: close[myCloseLast] > myEma6[myCloseLast] ? 'green' : 'red' }] }
];

paint_overlay('EmaStatusTable', { position: 'top_right' }, {
	rows: myShowTable ? myRows : []
});