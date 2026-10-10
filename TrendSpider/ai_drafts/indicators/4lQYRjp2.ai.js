describe_indicator('10 Circles Trade Tracker (v6 Gold)', 'price');

// NOTE: This indicator is a manual trade tracker. It has no actual
// price-based logic in the original Pine script (no entries, no TP/SL
// computed from candles). All values are manually input by the user.
// Because of that, "same signal bars" cannot really apply here -
// register_signal() outputs below are derived from the manual inputs only,
// not from price action, and will be constant across the whole chart.

const myDayTab = input.tab('Day Selection');
// Shortened input title to avoid "name is too lengthy" error
const myDayOffset = myDayTab.number('View Day', 0, { min: 0, max: 10 });
const myPositionInput = myDayTab.select('Table Position', 'Top Right', ['Top Right', 'Top Left', 'Bottom Right', 'Bottom Left']);

const myTradesTab = input.tab('10 Trades Results');
const myStatusOptions = ['None', 'Take Profit', 'Stop Loss'];

const myTradeRow1 = myTradesTab.row();
const myTrade1Status = myTradeRow1.select('Trade 1', 'None', myStatusOptions);
const myTrade1Note = myTradeRow1.text('Note 1', '');

const myTradeRow2 = myTradesTab.row();
const myTrade2Status = myTradeRow2.select('Trade 2', 'None', myStatusOptions);
const myTrade2Note = myTradeRow2.text('Note 2', '');

const myTradeRow3 = myTradesTab.row();
const myTrade3Status = myTradeRow3.select('Trade 3', 'None', myStatusOptions);
const myTrade3Note = myTradeRow3.text('Note 3', '');

const myTradeRow4 = myTradesTab.row();
const myTrade4Status = myTradeRow4.select('Trade 4', 'None', myStatusOptions);
const myTrade4Note = myTradeRow4.text('Note 4', '');

const myTradeRow5 = myTradesTab.row();
const myTrade5Status = myTradeRow5.select('Trade 5', 'None', myStatusOptions);
const myTrade5Note = myTradeRow5.text('Note 5', '');

const myTradeRow6 = myTradesTab.row();
const myTrade6Status = myTradeRow6.select('Trade 6', 'None', myStatusOptions);
const myTrade6Note = myTradeRow6.text('Note 6', '');

const myTradeRow7 = myTradesTab.row();
const myTrade7Status = myTradeRow7.select('Trade 7', 'None', myStatusOptions);
const myTrade7Note = myTradeRow7.text('Note 7', '');

const myTradeRow8 = myTradesTab.row();
const myTrade8Status = myTradeRow8.select('Trade 8', 'None', myStatusOptions);
const myTrade8Note = myTradeRow8.text('Note 8', '');

const myTradeRow9 = myTradesTab.row();
const myTrade9Status = myTradeRow9.select('Trade 9', 'None', myStatusOptions);
const myTrade9Note = myTradeRow9.text('Note 9', '');

const myTradeRow10 = myTradesTab.row();
const myTrade10Status = myTradeRow10.select('Trade 10', 'None', myStatusOptions);
const myTrade10Note = myTradeRow10.text('Note 10', '');

const myTrades = [
	{ status: myTrade1Status, note: myTrade1Note },
	{ status: myTrade2Status, note: myTrade2Note },
	{ status: myTrade3Status, note: myTrade3Note },
	{ status: myTrade4Status, note: myTrade4Note },
	{ status: myTrade5Status, note: myTrade5Note },
	{ status: myTrade6Status, note: myTrade6Note },
	{ status: myTrade7Status, note: myTrade7Note },
	{ status: myTrade8Status, note: myTrade8Note },
	{ status: myTrade9Status, note: myTrade9Note },
	{ status: myTrade10Status, note: myTrade10Note }
];

const myBgPanel = '#1E222D';
const myBgHeader = '#2A2E39';
const myGoldColor = '#FFD700';
const myGreenColor = '#089981';
const myRedColor = '#F23645';

function myGetCircleColor(_status) {
	if (_status === 'Take Profit') return myGreenColor;
	if (_status === 'Stop Loss') return myRedColor;
	return myGoldColor;
}

function myGetStatusEmoji(_status) {
	if (_status === 'Take Profit') return '\u{1F7E2}';
	if (_status === 'Stop Loss') return '\u{1F534}';
	return '\u{1F7E1}';
}

const myPositionMap = {
	'Top Right': 'top_right',
	'Top Left': 'top_left',
	'Bottom Right': 'bottom_right',
	'Bottom Left': 'bottom_left'
};

const myHeaderCell = {
	text: `Trades (Day -${myDayOffset})`,
	background_color: myBgHeader,
	color: myGoldColor
};

const myCircleCells = myTrades.map((_myTrade, _myIndex) => ({
	text: `${myGetStatusEmoji(_myTrade.status)}`,
	background_color: myBgPanel,
	color: myGetCircleColor(_myTrade.status),
	tooltip: `Trade #${_myIndex + 1}\nResult: ${_myTrade.status}` + (_myTrade.note ? `\nNote: ${_myTrade.note}` : '')
}));

paint_overlay('TradeTrackerTable', { position: myPositionMap[myPositionInput], order: 'above_all' }, {
	rows: [
		{ cells: [myHeaderCell] },
		{ cells: myCircleCells }
	]
});

// Signals for Visual Scripts: counts of take profits / stop losses
// among the 10 manually entered trade results.
const myTakeProfitCount = myTrades.filter(_myTrade => _myTrade.status === 'Take Profit').length;
const mySLCount = myTrades.filter(_myTrade => _myTrade.status === 'Stop Loss').length;

const myHasTakeProfitSignal = for_every(close, () => myTakeProfitCount > 0);
const myHasStopLossSignal = for_every(close, () => mySLCount > 0);
const myAllTakeProfitSignal = for_every(close, () => myTakeProfitCount === myTrades.length);

register_signal(myHasTakeProfitSignal, "Has Take Profit Trade");
register_signal(myHasStopLossSignal, "Has Stop Loss Trade");
register_signal(myAllTakeProfitSignal, "All Trades Take Profit");