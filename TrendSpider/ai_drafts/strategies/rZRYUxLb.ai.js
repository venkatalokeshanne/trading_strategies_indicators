describe_indicator('BTC Smart Pullback Liquidity Adaptive RSI', 'price', { decimals: 2 });

// === Parameters (grouped in tabs) ===
const myTabCore = input.tab('Core');
const myRsiLen = myTabCore.number('RSI Length', 14, { min: 1, max: 100 });
const myLookbackLow = myTabCore.number('Lookback Low', 20, { min: 1, max: 200 });
const myReclaimBars = myTabCore.number('Reclaim Max Bars', 5, { min: 1, max: 50 });

const myTabTrend = input.tab('Trend');
const myEmaFastLen = myTabTrend.number('EMA Fast', 50, { min: 1, max: 500 });
const myEmaSlowLen = myTabTrend.number('EMA Slow', 200, { min: 1, max: 500 });
const myUseDailyTrend = myTabTrend.boolean('Use Daily Trend Filter', true);

const myTabRisk = input.tab('Risk');
const myAtrLen = myTabRisk.number('ATR Length', 14, { min: 1, max: 100 });
const myStopATR = myTabRisk.number('Stop ATR Mult', 1.8, { min: 0.1, max: 20, step: 0.1 });
const myTp1ATR = myTabRisk.number('TP1 ATR Mult', 2.2, { min: 0.1, max: 20, step: 0.1 });
const myTp2ATR = myTabRisk.number('TP2 ATR Mult', 4.5, { min: 0.1, max: 20, step: 0.1 });

const myTabFilters = input.tab('Filters');
const myUseADX = myTabFilters.boolean('Use ADX Filter', true);
const myAdxMin = myTabFilters.number('ADX Min', 17, { min: 0, max: 100, step: 0.5 });
const myUseVolume = myTabFilters.boolean('Use Volume Filter', true);
const myVolLen = myTabFilters.number('Volume SMA Length', 50, { min: 1, max: 500 });
const myVolMult = myTabFilters.number('Volume Mult', 1.05, { min: 0.1, max: 10, step: 0.05 });

// === 1H (current chart) indicators ===
const myRsi = rsi(close, myRsiLen);
const myEma50 = ema(close, myEmaFastLen);
const myEma200 = ema(close, myEmaSlowLen);
const myAtr = atr(high, low, close, myAtrLen);

const myVolSma = sma(volume, myVolLen);
const myVolOK = for_every(volume, myVolSma, (_v, _s) => !myUseVolume || (_s != null && _v > _s * myVolMult));

const myAdxObj = indicators.adx(14);
const myAdxOK = for_every(myAdxObj.adx, _a => !myUseADX || (_a != null && _a > myAdxMin));

// === Daily trend (requested via request.history) ===
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

const myDailyEma50 = ema(myDailyData.close, 50);
const myDailyEma200 = ema(myDailyData.close, 200);
const myDailyRsi = rsi(myDailyData.close, 14);

const myDailyTrendRaw = for_every(myDailyData.close, myDailyEma50, myDailyEma200, myDailyRsi, (_c, _e50, _e200, _r) =>
	(_c > _e200 && _e50 > _e200 && _r > 45) ? 1 : 0
);

const myDailyTrendLanded = land_points_onto_series(myDailyData.time, myDailyTrendRaw, time, 'le');
const myDailyTrendInterp = interpolate_sparse_series(myDailyTrendLanded, 'constant');
const myDailyTrendOK = for_every(myDailyTrendInterp, _v => _v === 1);

const myTrendOK = for_every(close, myEma50, myEma200, myDailyTrendOK, (_c, _e50, _e200, _dOK) =>
	_c > _e200 && _e50 > _e200 && (!myUseDailyTrend || _dOK)
);

// === Adaptive RSI z-score ===
const myRsiMean = sma(myRsi, 50);
const myRsiDev = stdev(myRsi, 50);
const myRsiZ = for_every(myRsi, myRsiMean, myRsiDev, (_r, _m, _d) => (_d !== 0 && _d != null) ? (_r - _m) / _d : 0);

const myRsiCapitulation = for_every(myRsiZ, _z => _z < -1.0);

// crossover of rsiZ above -0.35 (manual, path-dependent, computed in a single forward loop)
const myRsiRebound = series_of(false);
for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	myRsiRebound[myIndex] = myRsiZ[myIndex - 1] <= -0.35 && myRsiZ[myIndex] > -0.35;
}

// === Liquidity sweep ===
const myPreviousLow = lowest(shift(low, 1), myLookbackLow);
const mySweep = for_every(low, close, myPreviousLow, (_l, _c, _pl) => _pl != null && _l < _pl && _c > _pl);

// barssince(sweep) computed via forward loop
const myBarsSinceSweep = series_of(-1);
let myLastSweepIndex = -1;
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (mySweep[myIndex]) {
		myLastSweepIndex = myIndex;
	}
	myBarsSinceSweep[myIndex] = myLastSweepIndex >= 0 ? (myIndex - myLastSweepIndex) : -1;
}

const myReclaimAfterSweep = for_every(myBarsSinceSweep, close, myPreviousLow, (_b, _c, _pl) =>
	_b >= 0 && _b <= myReclaimBars && _pl != null && _c > _pl
);

// === Structure ===
const myHigherClose = for_every(close, shift(close, 1), (_c, _cp) => _c > _cp);
const myNotExtended = for_every(close, myEma50, myAtr, (_c, _e50, _a) => _c < _e50 + _a * 1.5);

const myRsiCapitulationPrev = shift(myRsiCapitulation, 1);

const myBuySignal = series_of(false);
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myBuySignal[myIndex] = Boolean(
		myTrendOK[myIndex] &&
		myAdxOK[myIndex] &&
		myVolOK[myIndex] &&
		myReclaimAfterSweep[myIndex] &&
		myRsiCapitulationPrev[myIndex] &&
		myRsiRebound[myIndex] &&
		myHigherClose[myIndex] &&
		myNotExtended[myIndex]
	);
}

// === Simplified position / exit simulation (single position, no pyramiding) ===
// NOTE: this is an approximation of the strategy's exit engine (no partial fills,
// first condition hit wins: stop or tp1 then tp2 is ignored once stop/tp1 hit fully).
const myStopLine = series_of(null);
const myTp1Line = series_of(null);
const myTp2Line = series_of(null);
const myExitRegime = series_of(false);

let myInPosition = false;
let myEntryPrice = null;
let myStopPrice = null;
let myTp1Price = null;
let myTp2Price = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (!myInPosition && myBuySignal[myIndex]) {
		myInPosition = true;
		myEntryPrice = close[myIndex];
		myStopPrice = myEntryPrice - myAtr[myIndex] * myStopATR;
		myTp1Price = myEntryPrice + myAtr[myIndex] * myTp1ATR;
		myTp2Price = myEntryPrice + myAtr[myIndex] * myTp2ATR;
	}

	if (myInPosition) {
		myStopLine[myIndex] = myStopPrice;
		myTp1Line[myIndex] = myTp1Price;
		myTp2Line[myIndex] = myTp2Price;

		const myRegimeBroken = close[myIndex] < myEma200[myIndex];
		myExitRegime[myIndex] = myRegimeBroken;

		if (myRegimeBroken || low[myIndex] <= myStopPrice || high[myIndex] >= myTp2Price) {
			myInPosition = false;
			myEntryPrice = null;
			myStopPrice = null;
			myTp1Price = null;
			myTp2Price = null;
		}
	}
}

// === Painting ===
paint(myEma50, { name: 'EMA50', color: '#FF9800', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#F44336', thickness: 2 });
paint(myPreviousLow, { name: 'LiquidityLevel', color: '#2196F3', style: 'ladder', thickness: 1 });

paint(myStopLine, { name: 'Stop', color: '#E53935', style: 'ladder', thickness: 1 });
paint(myTp1Line, { name: 'TP1', color: '#43A047', style: 'ladder', thickness: 1 });
paint(myTp2Line, { name: 'TP2', color: '#1B5E20', style: 'ladder', thickness: 1 });

const mySweepMarks = for_every(mySweep, _s => _s ? 1 : null);
paint(mySweepMarks, { name: 'Sweep', style: 'labels_below', color: '#2196F3' });

const myBuyMarks = for_every(myBuySignal, _b => _b ? 1 : null);
paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#00E676' });

// === Signals for scanners, alerts and strategy tester ===
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySweep, 'Liquidity Sweep');
register_signal(myExitRegime, 'Exit Regime Broken');
register_signal(myTrendOK, 'Trend OK');
register_signal(myDailyTrendOK, 'Daily Trend OK');