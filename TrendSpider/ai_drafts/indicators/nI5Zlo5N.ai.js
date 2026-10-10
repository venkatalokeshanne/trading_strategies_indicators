describe_indicator('Trade Checklist', 'price');

// --- DISPLAY SETTINGS ---
const myPositionTab = input.tab('Settings');
const myPositionGroup = myPositionTab.group('Display Settings');
const myPositionInput = myPositionGroup.select('Panel Position', 'Top Left', ['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right']);
const myPanelSize = myPositionGroup.select('Panel Size', 'Large', ['Small', 'Medium', 'Large']);

// --- CHECKLIST CRITERIA ---
const myChecklistGroup = myPositionTab.group('Pre-Entry Checklist');
const myCheck1 = myChecklistGroup.boolean('1. Is this Gold???', false);
const myCheck2 = myChecklistGroup.boolean('2. Valid OB present?', false);
const myCheck3 = myChecklistGroup.boolean('3. Liquidity already swept?', false);
const myCheck4 = myChecklistGroup.boolean('4. Stop loss set before entry?', false);
const myCheck5 = myChecklistGroup.boolean('5. Lot size not oversized?', false);
const myCheck6 = myChecklistGroup.boolean('6. Am I calm or tilted?', false);

// --- COLOR PALETTE ---
const myBgChecklist = '#242422';
const myBgHeader = '#2D2C28';
const myTextWhite = '#FFFFFF';
const myGoldAccent = '#E6C200';

// --- MAP POSITION ---
const myPositionMap = {
	'Top Left': 'top_left',
	'Top Right': 'top_right',
	'Bottom Left': 'bottom_left',
	'Bottom Right': 'bottom_right'
};
const myOverlayPosition = myPositionMap[myPositionInput];

// --- MAP FONT SIZE ---
// TrendSpider overlay tables don't expose a direct "text_size" per-cell
// control the way Pine does; we approximate it via font-size in px.
const myFontSizeMap = {
	'Small': '11px',
	'Medium': '13px',
	'Large': '15px'
};
const myFontSize = myFontSizeMap[myPanelSize];

// --- CHECKLIST STATE ---
const myQuestions = [
	'Is this Gold???',
	'Valid OB present?',
	'Liquidity already swept?',
	'Stop loss set before entry?',
	'Lot size not oversized?',
	'Am I calm or tilted?'
];
const myChecks = [myCheck1, myCheck2, myCheck3, myCheck4, myCheck5, myCheck6];
const myPassed = myChecks.filter(_check => _check).length;
const myAllPassed = myPassed === 6;

const myStatusText = myAllPassed ? 'READY TO ENTER!' : `(${myPassed}/6)`;
const myStatusBg = myAllPassed ? 'rgba(8,153,129,0.8)' : 'rgba(242,54,69,0.8)';
const myReadyLabel = myAllPassed ? 'ALL CONDITIONS MET' : 'CHECK ALL ITEMS!';

// --- BUILD TABLE ROWS ---
const myHeaderRow = {
	cells: [{
		text: 'CHECKLIST ' + myStatusText,
		background_color: myBgHeader,
		color: myGoldAccent,
		font_size: myFontSize,
		colspan: 2
	}]
};

const myQuestionRows = myQuestions.map((_question, _i) => ({
	cells: [{
		text: _question,
		background_color: myBgChecklist,
		color: myTextWhite,
		font_size: myFontSize
	}, {
		text: myChecks[_i] ? 'YES' : 'NO',
		background_color: myBgChecklist,
		color: myChecks[_i] ? '#089981' : '#F23645',
		font_size: myFontSize
	}]
}));

const myFooterRow = {
	cells: [{
		text: myReadyLabel,
		background_color: myStatusBg,
		color: myTextWhite,
		font_size: myFontSize,
		colspan: 2
	}]
};

paint_overlay('TradeChecklistTable', { position: myOverlayPosition }, {
	rows: [myHeaderRow, ...myQuestionRows, myFooterRow]
});

// --- SCANNER/STRATEGY SIGNAL ---
// Signal is true on every candle while all 6 checklist items are checked
// (this mirrors the "barstate.islast" readiness state, since inputs are
// static booleans and not time series).
const myReadySignal = series_of(myAllPassed);
register_signal(myReadySignal, 'Checklist Complete');