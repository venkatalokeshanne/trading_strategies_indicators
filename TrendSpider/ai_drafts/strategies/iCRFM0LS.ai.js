describe_indicator('Real Strength Scalper 5m', 'lower');
// ===== INPUTS =====
const strengthTab = input.tab('Strength');
const momLen = strengthTab.number('Momentum ROC Length', 9, { min: 1, max: 200 });
const volLen = strengthTab.number('Volume MA Length', 20, { min: 1, max: 200 });
const adxLen = strengthTab.number('ADX Length', 14, { min: 1, max: 200 });
const diLen = strengthTab.number('DI Length', 14, { min: 1, max: 200 });
const smoothLen = strengthTab.number('Histogram Smoothing', 8, { min: 1, max: 200 });

const filtersTab = input.tab('Filters');
const adxMin = filtersTab.number('Min ADX', 14.0, { min: 0, max: 100 });
const volMin = filtersTab.number('Min Volume Ratio', 1.2, { min: 0.1, max: 10, step: 0.1 });
const strThr = filtersTab.number('Strength Threshold', 1.0, { min: -100, max: 100, step: 0.1 });

const trendTab = input.tab('Trend Filter');
const smaFastLen = trendTab.number('SMA Fast', 30, { min: 1, max: 500 });
const smaSlowLen = trendTab.number('SMA Slow', 60, { min: 1, max: 500 });
// shortened from "Use SMA Trend Filter" to satisfy input name length limit
const useTrend = trendTab.boolean('Use SMA Trend', true);

const riskTab = input.tab('Risk');
const slPct = riskTab.number('Stop Loss Percent', 1.0, { min: 0.1, max: 100, step: 0.1 });

const exitTab = input.tab('Exit');
// shortened from "Peak Drop Percent To Exit" to satisfy input name length limit
const peakDrop = exitTab.number('Peak Drop Percent', 25.0, { min: 1, max: 99, step: 5 });
// shortened from "Min Bars Before Peak Flip Exit" to satisfy input name length limit
const minHold = exitTab.number('Min Hold Bars', 3, { min: 0, max: 200 });
// shortened from "Flip Exit Threshold" to satisfy input name length limit
const flipThr = exitTab.number('Flip Exit Thresh', 0.8, { min: -100, max: 100, step: 0.1 });

// ===== CALC =====
// NOTE: Pine's ta.dmi(diLen, adxLen) supports two separate lengths
// (one for +DI/-DI smoothing, one for ADX smoothing). The Custom JS API
// indicators.adx() only exposes a single period, so diLen and adxLen
// are collapsed into one value (diLen is used). This is an approximation.
const myAdx = indicators.adx(diLen);
const diPlus = myAdx.dmiPlus;
const diMinus = myAdx.dmiMinus;
const adxVal = myAdx.adx;

const mom = roc(close, momLen);
const volMa = sma(volume, volLen);
const volRatio = div(volume, volMa);
const adxBoost = div(adxVal, 20.0);

const rawStr = for_every(mom, volRatio, adxBoost, (_m, _v, _a) => {
	const myVolTerm = Math.max(_v, 0.3);
	const myAdxTerm = Math.max(_a, 0.3);
	return _m * myVolTerm * myAdxTerm;
});

const strength = ema(rawStr, smoothLen);
const fastMA = sma(close, smaFastLen);
const slowMA = sma(close, smaSlowLen);

// ===== HISTOGRAM COLOR =====
const histColor = for_every(strength, (_s, _prev, _i) => {
	const myPrevStrength = _i > 0 ? strength[_i - 1] : _s;
	if (_s > 0 && _s > myPrevStrength) return '#00e676';
	if (_s > 0) return 'rgba(0,230,118,0.45)';
	if (_s < 0 && _s < myPrevStrength) return '#ff1744';
	return 'rgba(255,23,68,0.45)';
});

// ===== STATEFUL SIMULATION (positions, peaks, locks, exits) =====
const myLength = close.length;
const longSigSeries = series_of(false);
const shortSigSeries = series_of(false);
const longEntrySeries = series_of(false);
const shortEntrySeries = series_of(false);
const longExitSeries = series_of(false);
const shortExitSeries = series_of(false);

let myPositionSize = 0; // >0 long, <0 short, 0 flat
let myPrevPositionSize = 0;
let myLongPeak = null;
let myShortPeak = null;
let myEntryBar = null;
let myLongLocked = false;
let myShortLocked = false;
let myEntryAvgPrice = null;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myStrength = strength[myIndex];
	const myPrevStrength = myIndex > 0 ? strength[myIndex - 1] : myStrength;
	const myBullDir = diPlus[myIndex] > diMinus[myIndex];
	const myBearDir = diMinus[myIndex] > diPlus[myIndex];
	const myStrongAdx = adxVal[myIndex] >= adxMin;
	const myStrongVol = volRatio[myIndex] >= volMin;
	const myUptrend = fastMA[myIndex] > slowMA[myIndex];
	const myDowntrend = fastMA[myIndex] < slowMA[myIndex];

	const myLongSig = myStrength > strThr && myStrongAdx && myStrongVol && myBullDir && myStrength > myPrevStrength && (!useTrend || myUptrend);
	const myShortSig = myStrength < -strThr && myStrongAdx && myStrongVol && myBearDir && myStrength < myPrevStrength && (!useTrend || myDowntrend);

	longSigSeries[myIndex] = myLongSig;
	shortSigSeries[myIndex] = myShortSig;

	// position transition detection (based on previous bar's state)
	if (myPositionSize > 0 && myPrevPositionSize <= 0) {
		myLongPeak = myStrength;
		myEntryBar = myIndex;
	}
	if (myPositionSize < 0 && myPrevPositionSize >= 0) {
		myShortPeak = myStrength;
		myEntryBar = myIndex;
	}
	if (myPositionSize > 0) {
		myLongPeak = Math.max(myLongPeak === null ? myStrength : myLongPeak, myStrength);
	}
	if (myPositionSize < 0) {
		myShortPeak = Math.min(myShortPeak === null ? myStrength : myShortPeak, myStrength);
	}

	const myBarsHeld = myEntryBar === null ? 0 : myIndex - myEntryBar;

	const myLongPkExit = myLongPeak !== null && myLongPeak > 0 && myStrength < myLongPeak * (1 - peakDrop / 100) && myBarsHeld >= minHold;
	const myShortPkExit = myShortPeak !== null && myShortPeak < 0 && myStrength > myShortPeak * (1 - peakDrop / 100) && myBarsHeld >= minHold;
	const myLongFlipExit = myStrength <= -flipThr && myBarsHeld >= minHold;
	const myShortFlipExit = myStrength >= flipThr && myBarsHeld >= minHold;

	const myLongExit = myPositionSize > 0 && myLongPeak !== null && (myUptrend ? myLongFlipExit : myLongPkExit);
	const myShortExit = myPositionSize < 0 && myShortPeak !== null && (myDowntrend ? myShortFlipExit : myShortPkExit);

	// re-entry lock based on stop loss hit (position went to 0 from nonzero without close signal)
	const myLongSLHit = myPrevPositionSize > 0 && myPositionSize === 0;
	const myShortSLHit = myPrevPositionSize < 0 && myPositionSize === 0;
	if (myLongSLHit) myLongLocked = true;
	if (myShortSLHit) myShortLocked = true;
	if (myLongLocked && myStrength <= 0) myLongLocked = false;
	if (myShortLocked && myStrength >= 0) myShortLocked = false;

	// stop loss check (intrabar approximation using close vs avg price)
	let myStopHit = false;
	if (myPositionSize > 0 && myEntryAvgPrice !== null) {
		const mySlPrice = myEntryAvgPrice * (1 - slPct / 100);
		if (low[myIndex] <= mySlPrice) myStopHit = true;
	}
	if (myPositionSize < 0 && myEntryAvgPrice !== null) {
		const mySlPrice = myEntryAvgPrice * (1 + slPct / 100);
		if (high[myIndex] >= mySlPrice) myStopHit = true;
	}

	myPrevPositionSize = myPositionSize;

	// EXECUTE entries
	if (myLongSig && myPositionSize <= 0 && !myLongLocked) {
		myPositionSize = 1;
		myEntryAvgPrice = close[myIndex];
		longEntrySeries[myIndex] = true;
	}
	else if (myShortSig && myPositionSize >= 0 && !myShortLocked) {
		myPositionSize = -1;
		myEntryAvgPrice = close[myIndex];
		shortEntrySeries[myIndex] = true;
	}

	// EXECUTE exits
	if (myPositionSize > 0) {
		if (myStopHit) {
			myPositionSize = 0;
			myEntryAvgPrice = null;
			myLongPeak = null;
		}
		else if (myLongExit) {
			longExitSeries[myIndex] = true;
			myPositionSize = 0;
			myEntryAvgPrice = null;
			myLongLocked = false;
			myLongPeak = null;
		}
	}
	else {
		myLongPeak = null;
	}

	if (myPositionSize < 0) {
		if (myStopHit) {
			myPositionSize = 0;
			myEntryAvgPrice = null;
			myShortPeak = null;
		}
		else if (myShortExit) {
			shortExitSeries[myIndex] = true;
			myPositionSize = 0;
			myEntryAvgPrice = null;
			myShortLocked = false;
			myShortPeak = null;
		}
	}
	else {
		myShortPeak = null;
	}
}

// ===== PAINT =====
paint(strength, { name: 'Strength', color: histColor, style: 'column' });
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'dotted' });
paint(horizontal_line(strThr), { name: 'PlusThreshold', color: 'gray', style: 'dotted' });
paint(horizontal_line(-strThr), { name: 'MinusThreshold', color: 'gray', style: 'dotted' });
paint(horizontal_line(flipThr), { name: 'PlusFlipThreshold', color: 'yellow', style: 'dotted' });
paint(horizontal_line(-flipThr), { name: 'MinusFlipThreshold', color: 'yellow', style: 'dotted' });
paint(fastMA, { name: 'SMAFast', color: 'aqua', forceUsePriceAxis: true });
paint(slowMA, { name: 'SMASlow', color: 'orange', forceUsePriceAxis: true });

// ===== SIGNALS FOR SCANNER / ALERTS / STRATEGY =====
register_signal(longSigSeries, 'Long Signal');
register_signal(shortSigSeries, 'Short Signal');
register_signal(longEntrySeries, 'Long Entry');
register_signal(shortEntrySeries, 'Short Entry');
register_signal(longExitSeries, 'Long Exit');
register_signal(shortExitSeries, 'Short Exit');