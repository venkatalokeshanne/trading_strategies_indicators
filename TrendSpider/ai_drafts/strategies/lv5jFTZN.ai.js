describe_indicator('XAUUSD Elliott V17 - H4 Filter Edition', 'price');

// ------------------------------------------------------------------
// NOTE: TrendSpider Custom JS API has no strategy/broker engine
// (no strategy.entry/close_all/openprofit/position_size/pyramiding).
// This script reproduces the Pine Script's SIGNAL LOGIC exactly
// (long_sniper / short_sniper / recovery triggers / DD stop / TP exit)
// by manually simulating position state (price, size, cycle count)
// in a plain loop. It does NOT compute real equity, commissions or
// true position sizing - it only outputs the same signal bars the
// Pine strategy would act on.
// ------------------------------------------------------------------

const myStepDist = input.number('Distancia de Recuperacion', 24.0, { min: 0.1, max: 10000 });
const myMult = input.number('Multiplicador Progresivo', 1.6, { min: 1.0, max: 10 });
const myTpGlobal = input.number('Objetivo de Ganancia Ciclo', 200.0, { min: 1, max: 100000 });
const myH4Resolution = input.text('Temporalidad del Filtro', '240');
const myEmaLength = input.number('EMA Periodos H4', 200, { min: 1, max: 1000 });
const myDdPct = input.number('Max Open Loss Percent', 5.0, { min: 0.1, max: 100 });
const myInitialCapital = input.number('Initial Capital', 10000, { min: 1, max: 10000000 });

// --- H4 EMA filter ---
const myH4Data = await request.history(current.ticker, myH4Resolution);
assert(!myH4Data.error, `Error fetching H4 data: "${myH4Data.error}"`);
const myH4Ema = ema(myH4Data.close, myEmaLength);
const myH4EmaLanded = land_points_onto_series(myH4Data.time, myH4Ema, time, 'ge');
const myH4EmaInterpolated = interpolate_sparse_series(myH4EmaLanded, 'constant');

// --- High probability filters ---
const myEwo = sub(sma(close, 5), sma(close, 35));
const myAdxObject = indicators.adx(14);
const myAdxValue = myAdxObject.adx;
const myUpper = shift(highest(high, 40), 1);
const myLower = shift(lowest(low, 40), 1);
const myTrendUp = for_every(close, myH4EmaInterpolated, (_c, _e) => _c > _e);
const myTrendDown = for_every(close, myH4EmaInterpolated, (_c, _e) => _c < _e);

// crossover / crossunder of close vs upper/lower bands
const myCrossOver = for_every(close, myUpper, shift(close, 1), shift(myUpper, 1), (_c, _u, _pc, _pu) => _c > _u && _pc <= _pu);
const myCrossUnder = for_every(close, myLower, shift(close, 1), shift(myLower, 1), (_c, _l, _pc, _pl) => _c < _l && _pc >= _pl);

const myLongSniper = for_every(myAdxValue, myCrossOver, myEwo, myTrendUp, (_adx, _cross, _ewo, _trend) => _adx > 25 && _cross && _ewo > 0 && _trend);
const myShortSniper = for_every(myAdxValue, myCrossUnder, myEwo, myTrendDown, (_adx, _cross, _ewo, _trend) => _adx > 25 && _cross && _ewo < 0 && _trend);

// --- Manual position state simulation (approximation of the strategy engine) ---
const myDdLimit = -(myInitialCapital * myDdPct / 100);

const myLongEntryMarks = series_of(null);
const myShortEntryMarks = series_of(null);
const myRecoveryEntryMarks = series_of(null);
const myDdStopMarks = series_of(null);
const myTpExitMarks = series_of(null);

const mySignalLong = series_of(false);
const mySignalShort = series_of(false);
const mySignalRecovery = series_of(false);
const mySignalDdStop = series_of(false);
const mySignalTpExit = series_of(false);

let myPositionSize = 0;
let myLastPrice = null;
let myCycleCount = 0;
let myOpenProfit = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myClose = close[myIndex];
	const myAdx = myAdxValue[myIndex];

	// approximate open profit using unit qty * price change (no real sizing/commission model)
	if (myPositionSize !== 0 && myLastPrice !== null) {
		myOpenProfit = (myClose - myLastPrice) * myPositionSize;
	}
	else {
		myOpenProfit = 0;
	}

	// drawdown stop
	if (myOpenProfit <= myDdLimit && myPositionSize !== 0) {
		myDdStopMarks[myIndex] = myClose;
		mySignalDdStop[myIndex] = true;
		myPositionSize = 0;
		myCycleCount = 0;
		myLastPrice = null;
	}

	// entry logic
	if (myPositionSize === 0) {
		myCycleCount = 0;
		if (myLongSniper[myIndex]) {
			myPositionSize = 1;
			myLastPrice = myClose;
			myLongEntryMarks[myIndex] = myClose;
			mySignalLong[myIndex] = true;
		}
		else if (myShortSniper[myIndex]) {
			myPositionSize = -1;
			myLastPrice = myClose;
			myShortEntryMarks[myIndex] = myClose;
			mySignalShort[myIndex] = true;
		}
	}

	// recovery for longs
	if (myPositionSize > 0 && myLastPrice !== null && myClose < myLastPrice - myStepDist && myAdx > 20) {
		myCycleCount += 1;
		const myRecoveryQty = Math.pow(myMult, myCycleCount);
		myPositionSize += myRecoveryQty;
		myLastPrice = myClose;
		myRecoveryEntryMarks[myIndex] = myClose;
		mySignalRecovery[myIndex] = true;
	}

	// recovery for shorts
	if (myPositionSize < 0 && myLastPrice !== null && myClose > myLastPrice + myStepDist && myAdx > 20) {
		myCycleCount += 1;
		const myRecoveryQty = Math.pow(myMult, myCycleCount);
		myPositionSize -= myRecoveryQty;
		myLastPrice = myClose;
		myRecoveryEntryMarks[myIndex] = myClose;
		mySignalRecovery[myIndex] = true;
	}

	// profit target exit
	if (myOpenProfit >= myTpGlobal) {
		myTpExitMarks[myIndex] = myClose;
		mySignalTpExit[myIndex] = true;
		myPositionSize = 0;
		myCycleCount = 0;
		myLastPrice = null;
	}
}

// --- Painting ---
paint(myH4EmaInterpolated, { name: 'EmaH4Trend', color: 'gray', thickness: 2, forceUsePriceAxis: true });

// NOTE: paint_label_at_line() does not support labels_above/labels_below
// styled lines, which caused the previous error. These marker lines
// already carry their meaning visually (color/position), so the
// extra text labels were removed instead of switching line styles.
paint(myLongEntryMarks, { style: 'labels_below', color: '#26A69A', thickness: 3, name: 'LongEntry' });
paint(myShortEntryMarks, { style: 'labels_above', color: '#EF5350', thickness: 3, name: 'ShortEntry' });
paint(myRecoveryEntryMarks, { style: 'labels_below', color: '#FFB300', thickness: 3, name: 'RecoveryEntry' });
paint(myDdStopMarks, { style: 'labels_above', color: 'red', thickness: 3, name: 'DrawdownStop' });
paint(myTpExitMarks, { style: 'labels_above', color: 'blue', thickness: 3, name: 'ProfitTargetExit' });

// --- Signals for Scanner/Alerts/Strategy Tester ---
register_signal(mySignalLong, 'Long Sniper Entry');
register_signal(mySignalShort, 'Short Sniper Entry');
register_signal(mySignalRecovery, 'Recovery Entry');
register_signal(mySignalDdStop, 'Drawdown Stop');
register_signal(mySignalTpExit, 'Profit Target Exit');