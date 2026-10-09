describe_indicator('EMA 5 13 26 Cross Strategy', 'price');

// Assumption: Pine's process_orders_on_close=true normally only
// affects ENTRY order fills; stop/limit EXIT orders are still
// checked intrabar using High/Low. This port follows that logic.
// Entry fill price is approximated as the Close of the signal bar
// (Pine fills on the same bar close since process_orders_on_close
// is enabled). Position flips (opposite signal while in a trade)
// close the open position and open the new one on the same bar.

const myTab = input.tab('EMA / Volume');
const myEma5Len = myTab.number('EMA 5 Length', 5, { min: 1, max: 200 });
const myEma13Len = myTab.number('EMA 13 Length', 13, { min: 1, max: 200 });
const myEma26Len = myTab.number('EMA 26 Length', 26, { min: 1, max: 200 });
const myVolLen = myTab.number('Volume MA Length', 20, { min: 1, max: 200 });

const myRiskTab = input.tab('Risk / Exit');
const myMaxRiskPercent = myRiskTab.number('Max Risk Percent', 1.0, { min: 0.01, max: 100 });
const myExitHour = myRiskTab.number('Exit Hour', 23, { min: 0, max: 23 });
const myExitMinute = myRiskTab.number('Exit Minute', 10, { min: 0, max: 59 });

const mySrc = close;

// ================= EMA / Volume =================
const myEma5 = ema(mySrc, myEma5Len);
const myEma13 = ema(mySrc, myEma13Len);
const myEma26 = ema(mySrc, myEma26Len);
const myAvgVolume = sma(volume, myVolLen);

const myCandleCount = close.length;

const myBuySignal = series_of(null);
const mySellSignal = series_of(null);
const myLongExitSignal = series_of(null);
const myShortExitSignal = series_of(null);
const mySlLine = series_of(null);
const myTargetLine = series_of(null);

let myPosSize = 0;
let myEntryPrice = null;
let mySlFinal = null;
let myTarget = null;

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	const myVolumeCondition = volume[myIndex] > myAvgVolume[myIndex];

	const myBuyCondition =
		myEma5[myIndex - 1] < myEma13[myIndex - 1] && myEma5[myIndex - 1] < myEma26[myIndex - 1] &&
		myEma5[myIndex] > myEma13[myIndex] && myEma5[myIndex] > myEma26[myIndex] &&
		myVolumeCondition;

	const mySellCondition =
		myEma5[myIndex - 1] > myEma13[myIndex - 1] && myEma5[myIndex - 1] > myEma26[myIndex - 1] &&
		myEma5[myIndex] < myEma13[myIndex] && myEma5[myIndex] < myEma26[myIndex] &&
		myVolumeCondition;

	myBuySignal[myIndex] = myBuyCondition ? true : null;
	mySellSignal[myIndex] = mySellCondition ? true : null;

	// Check stop / target hits intrabar for an open position
	if (myPosSize === 1 && mySlFinal !== null && myTarget !== null) {
		if (low[myIndex] <= mySlFinal || high[myIndex] >= myTarget) {
			myLongExitSignal[myIndex] = true;
			myPosSize = 0;
			myEntryPrice = null;
			mySlFinal = null;
			myTarget = null;
		}
	}
	else if (myPosSize === -1 && mySlFinal !== null && myTarget !== null) {
		if (high[myIndex] >= mySlFinal || low[myIndex] <= myTarget) {
			myShortExitSignal[myIndex] = true;
			myPosSize = 0;
			myEntryPrice = null;
			mySlFinal = null;
			myTarget = null;
		}
	}

	// Intraday forced exit
	const myBarTime = time_of(time[myIndex]);
	const myIsExitTime = myBarTime.hours === myExitHour && myBarTime.minutes >= myExitMinute;
	if (myIsExitTime && myPosSize !== 0) {
		if (myPosSize === 1) myLongExitSignal[myIndex] = true;
		if (myPosSize === -1) myShortExitSignal[myIndex] = true;
		myPosSize = 0;
		myEntryPrice = null;
		mySlFinal = null;
		myTarget = null;
	}

	// Entries (close opposite position first, then open new one)
	if (myBuyCondition) {
		if (myPosSize === -1) {
			myShortExitSignal[myIndex] = true;
		}
		if (myPosSize !== 1) {
			myEntryPrice = close[myIndex];
			const myLongSL = low[myIndex];
			const myLongRiskRaw = myEntryPrice - myLongSL;
			const myMaxLongRisk = myEntryPrice * myMaxRiskPercent / 100;
			const myLongRisk = Math.min(myLongRiskRaw, myMaxLongRisk);
			const myLongCandlePerc = (high[myIndex] - low[myIndex]) / low[myIndex] * 100;
			const myLongRR = myLongCandlePerc > 1 ? 1 : 2;

			mySlFinal = myEntryPrice - myLongRisk;
			myTarget = myEntryPrice + (myLongRR * myLongRisk);
			myPosSize = 1;
		}
	}
	else if (mySellCondition) {
		if (myPosSize === 1) {
			myLongExitSignal[myIndex] = true;
		}
		if (myPosSize !== -1) {
			myEntryPrice = close[myIndex];
			const myShortSL = high[myIndex];
			const myShortRiskRaw = myShortSL - myEntryPrice;
			const myMaxShortRisk = myEntryPrice * myMaxRiskPercent / 100;
			const myShortRisk = Math.min(myShortRiskRaw, myMaxShortRisk);
			const myShortCandlePerc = (high[myIndex] - low[myIndex]) / low[myIndex] * 100;
			const myShortRR = myShortCandlePerc > 1 ? 1 : 2;

			mySlFinal = myEntryPrice + myShortRisk;
			myTarget = myEntryPrice - (myShortRR * myShortRisk);
			myPosSize = -1;
		}
	}

	if (myPosSize !== 0) {
		mySlLine[myIndex] = mySlFinal;
		myTargetLine[myIndex] = myTarget;
	}
}

// ================= Plots =================
paint(myEma5, { name: 'EMA5', color: '#e74c3c', thickness: 1 });
paint(myEma13, { name: 'EMA13', color: '#3498db', thickness: 1 });
paint(myEma26, { name: 'EMA26', color: '#9b59b6', thickness: 1 });
paint(mySlLine, { name: 'StopLoss', style: 'ladder', color: '#f39c12' });
paint(myTargetLine, { name: 'Target', style: 'ladder', color: '#2ecc71' });

const myBuyArrow = myBuySignal.map(myVal => myVal ? constants.icons.arrow_up : null);
const mySellArrow = mySellSignal.map(myVal => myVal ? constants.icons.arrow_down : null);

paint(myBuyArrow, { name: 'BuyArrow', style: 'labels_below', color: '#2ecc71' });
paint(mySellArrow, { name: 'SellArrow', style: 'labels_above', color: '#e74c3c' });

// ================= Signals =================
register_signal(myBuySignal.map(myVal => !!myVal), 'Buy Entry');
register_signal(mySellSignal.map(myVal => !!myVal), 'Sell Entry');
register_signal(myLongExitSignal.map(myVal => !!myVal), 'Long Exit');
register_signal(myShortExitSignal.map(myVal => !!myVal), 'Short Exit');