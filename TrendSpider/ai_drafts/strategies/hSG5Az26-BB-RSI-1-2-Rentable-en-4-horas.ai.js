// This is a conversion of a Pine Script strategy (Bollinger Bands + RSI
// with fixed risk/reward position sizing) into a TrendSpider indicator.
// TrendSpider custom indicators cannot place real orders or manage a
// broker position like Pine Script strategies do. Instead, this script
// reproduces the exact same signal logic (entry/exit conditions, TP/SL
// price levels) and simulates the "open position" state bar by bar so
// that the visual boxes and lines match the Pine behavior as closely as
// possible. Position sizing ("tamano_posicion") has no visual meaning on
// a chart overlay, so it is computed but not painted (no price-axis use).
describe_indicator('BB Plus RSI Risk Reward Strategy', 'price');

const bbTab = input.tab('Bollinger Bands');
const myBBLength = bbTab.number('Length', 20, { min: 1, max: 500 });
const myBBMult = bbTab.number('Standard Deviation', 2.0, { min: 0.1, max: 10, step: 0.1 });

const rsiTab = input.tab('RSI');
const myRSILength = rsiTab.number('Length', 14, { min: 1, max: 200 });
const myRSIOverbought = rsiTab.number('Overbought', 70, { min: 50, max: 99 });
const myRSIOversold = rsiTab.number('Oversold', 30, { min: 1, max: 50 });

const riskTab = input.tab('Fixed Risk Management');
const myRiskUSD = riskTab.number('Max Risk Per Trade (USD)', 100.0, { min: 0.01 });
const myRatioRB = riskTab.number('Risk Reward Ratio', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myStopDistPercentInput = riskTab.number('Stop Loss Distance (%)', 0.5, { min: 0.01, max: 50, step: 0.1 });

// Percent converted to a fraction, matching "dist_sl_perc" in Pine.
// NOTE: myStopDistPercentInput is a plain number (from input.number),
// not a series, so div() (which expects a series as 1st argument)
// is not applicable here. Use plain JS division instead.
const myStopDistPercent = myStopDistPercentInput / 100;

// === Indicators ===
const myBasis = sma(close, myBBLength);
const myDeviation = mult(stdev(close, myBBLength), myBBMult);
const myUpperBand = add(myBasis, myDeviation);
const myLowerBand = sub(myBasis, myDeviation);
const myRsi = rsi(close, myRSILength);

// === Conditions ===
const myLongCondition = for_every(close, myLowerBand, myRsi, (_c, _lower, _r) => _c < _lower && _r < myRSIOversold);
const myShortCondition = for_every(close, myUpperBand, myRsi, (_c, _upper, _r) => _c > _upper && _r > myRSIOverbought);

// === Simulate position state bar by bar (replaces strategy.position_size) ===
// positionSide: 0 = flat, 1 = long, -1 = short
const myEntryPrice = series_of(null);
const myTakeProfit = series_of(null);
const myStopLoss = series_of(null);
const myPositionSide = series_of(0);
const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);

const myStopDistValueFraction = myStopDistPercent; // fraction, constant per-run (fixed % input)

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevSide = myIndex > 0 ? myPositionSide[myIndex - 1] : 0;
	let mySide = myPrevSide;
	let myEntry = myIndex > 0 ? myEntryPrice[myIndex - 1] : null;
	let myTP = myIndex > 0 ? myTakeProfit[myIndex - 1] : null;
	let mySL = myIndex > 0 ? myStopLoss[myIndex - 1] : null;
	let myEnteredNow = false;
	let myExitedNow = false;

	// Exit check: if price breaches SL or TP while in a position
	if (mySide === 1 && myEntry != null) {
		if (high[myIndex] >= myTP || low[myIndex] <= mySL) {
			myExitedNow = true;
			mySide = 0;
			myEntry = null;
			myTP = null;
			mySL = null;
		}
	}
	else if (mySide === -1 && myEntry != null) {
		if (low[myIndex] <= myTP || high[myIndex] >= mySL) {
			myExitedNow = true;
			mySide = 0;
			myEntry = null;
			myTP = null;
			mySL = null;
		}
	}

	// Entry check: only when flat, matching "strategy.position_size == 0"
	if (mySide === 0) {
		if (myLongCondition[myIndex]) {
			mySide = 1;
			myEntry = close[myIndex];
			mySL = myEntry * (1 - myStopDistValueFraction);
			myTP = myEntry * (1 + myStopDistValueFraction * myRatioRB);
			myEnteredNow = true;
		}
		else if (myShortCondition[myIndex]) {
			mySide = -1;
			myEntry = close[myIndex];
			mySL = myEntry * (1 + myStopDistValueFraction);
			myTP = myEntry * (1 - myStopDistValueFraction * myRatioRB);
			myEnteredNow = true;
		}
	}

	myPositionSide[myIndex] = mySide;
	myEntryPrice[myIndex] = myEntry;
	myTakeProfit[myIndex] = myTP;
	myStopLoss[myIndex] = mySL;
	myEntrySignal[myIndex] = myEnteredNow;
	myExitSignal[myIndex] = myExitedNow;
}

// === Painting ===
paint(myBasis, { name: 'Basis', color: '#9e9e9e', style: 'line' });
const myUpperPainted = paint(myUpperBand, { name: 'Upper Band', color: '#ef5350', style: 'line' });
const myLowerPainted = paint(myLowerBand, { name: 'Lower Band', color: '#26a69a', style: 'line' });
fill(myUpperPainted, myLowerPainted, '#4da3ff', 0.07, 'BB Background');

const myEntryLinePainted = paint(myEntryPrice, { name: 'Entry Line', color: '#2962ff', thickness: 2, style: 'ladder' });
const myTakeProfitLinePainted = paint(myTakeProfit, { name: 'Take Profit Line', color: '#26a69a', thickness: 2, style: 'ladder' });
const myStopLossLinePainted = paint(myStopLoss, { name: 'Stop Loss Line', color: '#ef5350', thickness: 2, style: 'ladder' });
fill(myEntryLinePainted, myTakeProfitLinePainted, '#26a69a', 0.15, 'Profit Box');
fill(myEntryLinePainted, myStopLossLinePainted, '#ef5350', 0.15, 'Loss Box');

// === Scanner / Alert / Strategy signals ===
register_signal(myLongCondition, 'Long Condition');
register_signal(myShortCondition, 'Short Condition');
register_signal(myEntrySignal, 'Position Entered');
register_signal(myExitSignal, 'Position Exited');
register_signal(for_every(myPositionSide, _s => _s === 1), 'In Long Position');
register_signal(for_every(myPositionSide, _s => _s === -1), 'In Short Position');