describe_indicator('EMA Stack Strategy (EMA 1 to 6)', 'price');

// === Plot Toggles ===
const showTab = input.tab('Plot Toggles');
const showEma1 = showTab.boolean('Show EMA 1', true);
const showEma2 = showTab.boolean('Show EMA 2', true);
const showEma3 = showTab.boolean('Show EMA 3', true);
const showEma4 = showTab.boolean('Show EMA 4', true);
const showEma5 = showTab.boolean('Show EMA 5', true);
const showEma6 = showTab.boolean('Show EMA 6', true);

// === Bias Logic Toggles ===
const biasTab = input.tab('Bias Logic');
const useEma1 = biasTab.boolean('Use EMA 1 In Bias', true);
const useEma2 = biasTab.boolean('Use EMA 2 In Bias', true);
const useEma3 = biasTab.boolean('Use EMA 3 In Bias', true);
const useEma4 = biasTab.boolean('Use EMA 4 In Bias', true);
const useEma5 = biasTab.boolean('Use EMA 5 In Bias', true);
const useEma6 = biasTab.boolean('Use EMA 6 In Bias', true);

// === Length Inputs ===
const lenTab = input.tab('EMA Lengths');
const ema1Len = lenTab.number('EMA 1 Length', 5, { min: 1, max: 500 });
const ema2Len = lenTab.number('EMA 2 Length', 20, { min: 1, max: 500 });
const ema3Len = lenTab.number('EMA 3 Length', 50, { min: 1, max: 500 });
const ema4Len = lenTab.number('EMA 4 Length', 90, { min: 1, max: 500 });
const ema5Len = lenTab.number('EMA 5 Length', 140, { min: 1, max: 500 });
const ema6Len = lenTab.number('EMA 6 Length', 200, { min: 1, max: 500 });

// === EMA Calculations ===
const myEma1 = ema(close, ema1Len);
const myEma2 = ema(close, ema2Len);
const myEma3 = ema(close, ema3Len);
const myEma4 = ema(close, ema4Len);
const myEma5 = ema(close, ema5Len);
const myEma6 = ema(close, ema6Len);

// === Plot EMAs ===
paint(showEma1 ? myEma1 : constants.empty_series, { name: 'EMA1', color: 'blue', thickness: 2 });
paint(showEma2 ? myEma2 : constants.empty_series, { name: 'EMA2', color: 'green', thickness: 2 });
paint(showEma3 ? myEma3 : constants.empty_series, { name: 'EMA3', color: 'red', thickness: 2 });
paint(showEma4 ? myEma4 : constants.empty_series, { name: 'EMA4', color: 'white', thickness: 2 });
paint(showEma5 ? myEma5 : constants.empty_series, { name: 'EMA5', color: 'purple', thickness: 2 });
paint(showEma6 ? myEma6 : constants.empty_series, { name: 'EMA6', color: 'orange', thickness: 2 });

// === Build enabled bias EMA list in EMA1 to EMA6 order ===
// This array of series is built once, outside of the per-candle loop below.
const myBiasSeriesList = [];
if (useEma1) myBiasSeriesList.push(myEma1);
if (useEma2) myBiasSeriesList.push(myEma2);
if (useEma3) myBiasSeriesList.push(myEma3);
if (useEma4) myBiasSeriesList.push(myEma4);
if (useEma5) myBiasSeriesList.push(myEma5);
if (useEma6) myBiasSeriesList.push(myEma6);

const myFastAlignmentRequired = useEma1 && useEma2;

// === Main per candle computation ===
// We replicate Pine's bar-by-bar state (bias change detection, strategy
// position state for the exit conditions) with a single forward loop,
// since these are inherently stateful / sequential computations.
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myExitLongSignal = series_of(false);
const myExitShortSignal = series_of(false);
const myCloseLongOrder = series_of(false);
const myCloseShortOrder = series_of(false);
const myOpenLongOrder = series_of(false);
const myOpenShortOrder = series_of(false);

let myPrevBullBias = false;
let myPrevBearBias = false;
let myPositionSize = 0; // 1 = long, -1 = short, 0 = flat (simulated strategy state)

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	let myBullBias = true;
	let myBearBias = true;

	if (myBiasSeriesList.length >= 2) {
		for (let myInnerIndex = 0; myInnerIndex < myBiasSeriesList.length - 1; myInnerIndex += 1) {
			const myCurrentValue = myBiasSeriesList[myInnerIndex][myIndex];
			const myNextValue = myBiasSeriesList[myInnerIndex + 1][myIndex];
			myBullBias = myBullBias && (myCurrentValue > myNextValue);
			myBearBias = myBearBias && (myCurrentValue < myNextValue);
		}
	}

	const myNewBullBias = myBullBias && !myPrevBullBias;
	const myNewBearBias = myBearBias && !myPrevBearBias;

	const myFastBullOk = myFastAlignmentRequired ? (myEma1[myIndex] > myEma2[myIndex]) : true;
	const myFastBearOk = myFastAlignmentRequired ? (myEma1[myIndex] < myEma2[myIndex]) : true;

	const myFullBull = myBullBias && myFastBullOk;
	const myFullBear = myBearBias && myFastBearOk;

	let myCrossOver = false;
	let myCrossUnder = false;

	if (myIndex > 0) {
		const myPrevEma1 = myEma1[myIndex - 1];
		const myPrevEma2 = myEma2[myIndex - 1];
		myCrossOver = (myPrevEma1 <= myPrevEma2) && (myEma1[myIndex] > myEma2[myIndex]);
		myCrossUnder = (myPrevEma1 >= myPrevEma2) && (myEma1[myIndex] < myEma2[myIndex]);
	}

	const myLong = myFullBull && (myCrossOver || myNewBullBias);
	const myShort = myFullBear && (myCrossUnder || myNewBearBias);

	const myExitLong = (myPositionSize > 0) && myCrossUnder;
	const myExitShort = (myPositionSize < 0) && myCrossOver;

	myLongSignal[myIndex] = myLong;
	myShortSignal[myIndex] = myShort;
	myExitLongSignal[myIndex] = myExitLong;
	myExitShortSignal[myIndex] = myExitShort;

	// === Order Execution (simulated strategy position state) ===
	let myCloseLong = false;
	let myCloseShort = false;
	let myOpenLong = false;
	let myOpenShort = false;

	if (myLong && myPositionSize <= 0) {
		if (myPositionSize < 0) { myCloseShort = true; }
		myOpenLong = true;
		myPositionSize = 1;
	}

	if (myShort && myPositionSize >= 0) {
		if (myPositionSize > 0) { myCloseLong = true; }
		myOpenShort = true;
		myPositionSize = -1;
	}

	if (myExitLong && !myShort) {
		myCloseLong = true;
		if (myPositionSize > 0) { myPositionSize = 0; }
	}

	if (myExitShort && !myLong) {
		myCloseShort = true;
		if (myPositionSize < 0) { myPositionSize = 0; }
	}

	myCloseLongOrder[myIndex] = myCloseLong;
	myCloseShortOrder[myIndex] = myCloseShort;
	myOpenLongOrder[myIndex] = myOpenLong;
	myOpenShortOrder[myIndex] = myOpenShort;

	myPrevBullBias = myBullBias;
	myPrevBearBias = myBearBias;
}

// === Signals for Scanner, Alerts and Strategy Tester ===
register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');
register_signal(myExitLongSignal, 'Long Exit Signal Raw');
register_signal(myExitShortSignal, 'Short Exit Signal Raw');
register_signal(myOpenLongOrder, 'Open Long Order');
register_signal(myOpenShortOrder, 'Open Short Order');
register_signal(myCloseLongOrder, 'Close Long Order');
register_signal(myCloseShortOrder, 'Close Short Order');