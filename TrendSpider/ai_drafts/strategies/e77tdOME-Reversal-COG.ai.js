describe_indicator('Reversal and COG', 'lower');

// --- Inputs ---
const inputTab1 = input.tab('Signal Settings');
const myLength = inputTab1.number('COG Length', 5, { min: 1, max: 200 });
const myKSmoothing = inputTab1.number('K Smoothing', 20, { min: 1, max: 200 });
const myDLength = inputTab1.number('D Length', 4, { min: 1, max: 200 });
const myLevel = inputTab1.number('Reversal Level', 4, { min: 1, max: 200 });
const myLengthCoF = inputTab1.number('Reversal Length', 4, { min: 1, max: 200 });
const myOffsetM = inputTab1.number('COG Offset (m)', 14, { min: 0, max: 200 });
const myPercent = inputTab1.number('Percent', 1.0, { min: 0, max: 100 });
const mySignalLine = inputTab1.select('Trade from line', '1', ['1', '2']);
const myReverse = inputTab1.boolean('Trade reverse', false);

const inputTab2 = input.tab('Trading Settings');
const myEnableLong = inputTab2.boolean('Enable Long Trades', true);
const myEnableShort = inputTab2.boolean('Enable Short Trades', true);
const myUseSL = inputTab2.boolean('Use Stop Loss Percent', false);
const mySlPercentRow = inputTab2.row();
const mySlPercent = mySlPercentRow.number('Stop Loss Percent', 1.5, { min: 0.1, max: 50, step: 0.1 });

// --- Reversal123 math ---
// vFast = sma(stoch(close, high, low, LengthCoF), KSmoothing)
// vSlow = sma(vFast, DLength)
const myStoch = stochastic(close, high, low, myLengthCoF);
const myVFast = sma(myStoch, myKSmoothing);
const myVSlow = sma(myVFast, myDLength);
const myClose1 = shift(close, 1);
const myClose2 = shift(close, 2);

// --- CenterOfGravity math ---
// NOTE: Pine's ta.linreg(close, L, offset) supports an endpoint offset parameter
// which is not supported by this platform's linreg(). We approximate using
// linreg(close, L) with offset 0. This is a deviation from the exact Pine math.
const myLinReg = linreg(close, myLength);
const myPriceAdj = mult(div(mult(close, myPercent), 100), 1);
const myLG1r = add(myLinReg, myPriceAdj);
const myLG1s = sub(myLinReg, myPriceAdj);
const myLG2r = add(myLinReg, mult(myPriceAdj, 2));
const myLG2s = sub(myLinReg, mult(myPriceAdj, 2));
const mySignalR = mySignalLine === '1' ? myLG1r : myLG2r;
const mySignalS = mySignalLine === '1' ? myLG1s : myLG2s;

// --- Main simulation loop (plain arithmetic only, no indicator calls) ---
const myN = close.length;

const myPosReversal = series_of(0);
const myPosCOG = series_of(0);
const myPos = series_of(0);
const myPosSig = series_of(0);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myCloseAllSignal = series_of(false);
const mySLExitSignal = series_of(false);

let myPrevPosReversal = 0.0;
let myPrevPosCOG = 0.0;
let myCurrentPositionSide = 0; // 1 long, -1 short, 0 flat
let myPositionAvgPrice = 0.0;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	// Reversal123 persistence logic
	let myPosR = myPrevPosReversal;
	if (myClose2[myIndex] !== null && myClose1[myIndex] !== null && myVFast[myIndex] !== null && myVSlow[myIndex] !== null) {
		if (myClose2[myIndex] < myClose1[myIndex] && close[myIndex] > myClose1[myIndex] && myVFast[myIndex] < myVSlow[myIndex] && myVFast[myIndex] > myLevel) {
			myPosR = 1.0;
		}
		else if (myClose2[myIndex] > myClose1[myIndex] && close[myIndex] < myClose1[myIndex] && myVFast[myIndex] > myVSlow[myIndex] && myVFast[myIndex] < myLevel) {
			myPosR = -1.0;
		}
	}
	myPrevPosReversal = myPosR;
	myPosReversal[myIndex] = myPosR;

	// CenterOfGravity persistence logic
	let myPosC = myPrevPosCOG;
	if (mySignalR[myIndex] !== null && mySignalS[myIndex] !== null) {
		if (close[myIndex] > mySignalR[myIndex]) {
			myPosC = 1.0;
		}
		else if (close[myIndex] < mySignalS[myIndex]) {
			myPosC = -1.0;
		}
	}
	myPrevPosCOG = myPosC;
	myPosCOG[myIndex] = myPosC;

	// Combined signal
	let myCombinedPos = 0;
	if (myPosR === 1.0 && myPosC === 1.0) {
		myCombinedPos = 1;
	}
	else if (myPosR === -1.0 && myPosC === -1.0) {
		myCombinedPos = -1;
	}
	myPos[myIndex] = myCombinedPos;

	let myFinalSignal = myCombinedPos;
	if (myReverse) {
		myFinalSignal = myCombinedPos === 1 ? -1 : (myCombinedPos === -1 ? 1 : 0);
	}
	myPosSig[myIndex] = myFinalSignal;

	// Strategy entry/exit simulation
	let myDidEnterLong = false;
	let myDidEnterShort = false;
	let myDidCloseAll = false;
	let myDidSLExit = false;

	if (myFinalSignal === 1 && myEnableLong && myCurrentPositionSide !== 1) {
		myCurrentPositionSide = 1;
		myPositionAvgPrice = close[myIndex];
		myDidEnterLong = true;
	}
	else if (myFinalSignal === -1 && myEnableShort && myCurrentPositionSide !== -1) {
		myCurrentPositionSide = -1;
		myPositionAvgPrice = close[myIndex];
		myDidEnterShort = true;
	}
	else if (myFinalSignal === 0 && myCurrentPositionSide !== 0) {
		myCurrentPositionSide = 0;
		myPositionAvgPrice = 0.0;
		myDidCloseAll = true;
	}

	if (myUseSL && myCurrentPositionSide !== 0 && myPositionAvgPrice !== 0) {
		if (myCurrentPositionSide === 1) {
			const myLongSL = myPositionAvgPrice * (1 - mySlPercent / 100);
			if (low[myIndex] <= myLongSL) {
				myDidSLExit = true;
				myCurrentPositionSide = 0;
				myPositionAvgPrice = 0.0;
			}
		}
		else if (myCurrentPositionSide === -1) {
			const myShortSL = myPositionAvgPrice * (1 + mySlPercent / 100);
			if (high[myIndex] >= myShortSL) {
				myDidSLExit = true;
				myCurrentPositionSide = 0;
				myPositionAvgPrice = 0.0;
			}
		}
	}

	myLongEntrySignal[myIndex] = myDidEnterLong;
	myShortEntrySignal[myIndex] = myDidEnterShort;
	myCloseAllSignal[myIndex] = myDidCloseAll;
	mySLExitSignal[myIndex] = myDidSLExit;
}

// --- Visuals ---
const myCandleColors = for_every(close, (_c, _p, _i) => {
	const myValue = myPosSig[_i];
	if (myValue === -1) return '#b50404';
	if (myValue === 1) return '#079605';
	return '#0536b3';
});
color_candles(myCandleColors);

paint(myPosSig, { name: 'Signal', style: 'column', color: '#4DA3FF' });

// --- Signals for scanner/alerts/backtest ---
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myCloseAllSignal, 'Close All');
register_signal(mySLExitSignal, 'Stop Loss Exit');
register_signal(for_every(myPosSig, _v => _v === 1), 'Bullish Signal');
register_signal(for_every(myPosSig, _v => _v === -1), 'Bearish Signal');