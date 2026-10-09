describe_indicator('EMA 9 21 GoldenX Pro TSL', 'price');

// ═══════════════════════════════════════════════════════════════
// INPUTS
// ═══════════════════════════════════════════════════════════════
const myEmaTab = input.tab('EMA / Trend');
const myEmaRow = myEmaTab.row();
const myEmaFastLen = myEmaRow.number('Fast EMA', 9, { min: 1, max: 200 });
const myEmaSlowLen = myEmaRow.number('Slow EMA', 21, { min: 1, max: 400 });
const myTradeDir = myEmaTab.select('Trade Direction', 'Both', ['Long', 'Short', 'Both']);

const myAdxGroup = myEmaTab.group('ADX / DMI');
const myAdxRow = myAdxGroup.row();
const myAdxLen = myAdxRow.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxThresh = myAdxRow.number('ADX Threshold', 20, { min: 1, max: 100 });
const myUseAdxFlip = myAdxGroup.boolean('Exit and flip on DMI reversal', true);

const myStopTab = input.tab('Stops');
const myAtrRow = myStopTab.row();
const myAtrLen = myAtrRow.number('ATR Length', 14, { min: 1, max: 100 });
const myAtrMult = myAtrRow.number('ATR Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myMaxLossPerc = myStopTab.number('Max Stop Loss Percent', 1.0, { min: 0.1, max: 50, step: 0.1 });

// ═══════════════════════════════════════════════════════════════
// CORE CALCULATIONS
// ═══════════════════════════════════════════════════════════════
const myFastEMA = ema(close, myEmaFastLen);
const mySlowEMA = ema(close, myEmaSlowLen);

// DMI / ADX (approximation of Pine's ta.dmi which uses same length for
// DI smoothing and ADX smoothing; indicators.adx() reproduces the
// standard Wilder DMI/ADX calculation)
const myAdxObject = indicators.adx(myAdxLen);
const myAdxValue = myAdxObject.adx;
const myDiPlus = myAdxObject.dmiPlus;
const myDiMinus = myAdxObject.dmiMinus;

const myDiDiff = sub(myDiPlus, myDiMinus);
const myIsTrending = for_every(myAdxValue, myDiDiff, (_adx, _diff) => (_adx > myAdxThresh) || (Math.abs(_diff) > 10));

const myVolSma5 = sma(volume, 5);
const myCloseSma5 = sma(close, 5);
const myVolRising = for_every(volume, myVolSma5, (_v, _s) => _v > _s);
const myPriceRising = for_every(close, myCloseSma5, (_c, _s) => _c > _s);
const myPriceFalling = for_every(close, myCloseSma5, (_c, _s) => _c < _s);

const myAtr = atr(high, low, close, myAtrLen);
const myLongStop = sub(close, mult(myAtr, myAtrMult));
const myShortStop = add(close, mult(myAtr, myAtrMult));

// Crossover / Crossunder helpers (built from EMA difference)
const myEmaDiff = sub(myFastEMA, mySlowEMA);
const myEmaDiffPrev = shift(myEmaDiff, 1);
const myCrossoverEma = for_every(myEmaDiff, myEmaDiffPrev, (_d, _p) => _d > 0 && _p <= 0);
const myCrossunderEma = for_every(myEmaDiff, myEmaDiffPrev, (_d, _p) => _d < 0 && _p >= 0);

const myDiDiffPrev = shift(myDiDiff, 1);
const myDmiBearishFlip = for_every(myDiDiff, myDiDiffPrev, (_d, _p) => _d < 0 && _p >= 0);
const myDmiBullishFlip = for_every(myDiDiff, myDiDiffPrev, (_d, _p) => _d > 0 && _p <= 0);

const myLongOK = (myTradeDir === 'Long') || (myTradeDir === 'Both');
const myShortOK = (myTradeDir === 'Short') || (myTradeDir === 'Both');

const myLongSignalRaw = for_every(
	myCrossoverEma, myVolRising, myPriceRising, myIsTrending,
	(_co, _vr, _pr, _tr) => _co && (_vr || _pr) && _tr
);
const myShortSignalRaw = for_every(
	myCrossunderEma, myVolRising, myPriceFalling, myIsTrending,
	(_cu, _vr, _pf, _tr) => _cu && (_vr || _pf) && _tr
);

const myAdxConfirmsTrend = for_every(myAdxValue, (_adx) => _adx > myAdxThresh);
const myFlipLongToShort = for_every(myAdxConfirmsTrend, myDmiBearishFlip, (_c, _f) => myUseAdxFlip && _c && _f && myShortOK);
const myFlipShortToLong = for_every(myAdxConfirmsTrend, myDmiBullishFlip, (_c, _f) => myUseAdxFlip && _c && _f && myLongOK);

// ═══════════════════════════════════════════════════════════════
// POSITION / STOP SIMULATION
// (Approximates Pine's strategy engine using close for signal fills
// and low/high for intrabar stop fills. Exact fills may differ from
// the TradingView strategy tester due to broker emulation details.)
// ═══════════════════════════════════════════════════════════════
const myCandleCount = close.length;
const myFinalStop = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

let myPosSize = 0;
let myEntryPrice = 0;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myLongSig = myLongSignalRaw[myIndex] && myLongOK;
	const myShortSig = myShortSignalRaw[myIndex] && myShortOK;

	if (myLongSig) {
		if (myPosSize < 0) {
			myLongExitSignal[myIndex] = true;
			myPosSize = 1;
			myEntryPrice = close[myIndex];
			myLongEntrySignal[myIndex] = true;
		}
		else if (myPosSize === 0) {
			myPosSize = 1;
			myEntryPrice = close[myIndex];
			myLongEntrySignal[myIndex] = true;
		}
	}

	if (myShortSig) {
		if (myPosSize > 0) {
			myShortExitSignal[myIndex] = true;
			myPosSize = -1;
			myEntryPrice = close[myIndex];
			myShortEntrySignal[myIndex] = true;
		}
		else if (myPosSize === 0) {
			myPosSize = -1;
			myEntryPrice = close[myIndex];
			myShortEntrySignal[myIndex] = true;
		}
	}

	if (myPosSize > 0) {
		const myHardStopPrice = myEntryPrice * (1 - (myMaxLossPerc / 100));
		const myStopValue = Math.min(myLongStop[myIndex], myHardStopPrice);
		myFinalStop[myIndex] = myStopValue;

		if (low[myIndex] <= myStopValue) {
			myLongExitSignal[myIndex] = true;
			myPosSize = 0;
		}
	}
	else if (myPosSize < 0) {
		const myHardStopPrice = myEntryPrice * (1 + (myMaxLossPerc / 100));
		const myStopValue = Math.max(myShortStop[myIndex], myHardStopPrice);
		myFinalStop[myIndex] = myStopValue;

		if (high[myIndex] >= myStopValue) {
			myShortExitSignal[myIndex] = true;
			myPosSize = 0;
		}
	}
}

// ═══════════════════════════════════════════════════════════════
// VISUALS
// ═══════════════════════════════════════════════════════════════
paint(myFastEMA, { name: 'Fast EMA', color: '#FF9800', thickness: 2 });
paint(mySlowEMA, { name: 'Slow EMA', color: '#2196F3', thickness: 2 });
paint(myFinalStop, { name: 'Final Stop', color: '#E53935', style: 'dotted', thickness: 2 });

// ═══════════════════════════════════════════════════════════════
// SIGNALS (for Scanners, Alerts, Strategy Tester)
// ═══════════════════════════════════════════════════════════════
register_signal(myLongEntrySignal, 'Long Entry GoldenX');
register_signal(myShortEntrySignal, 'Short Entry DeathX');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');
register_signal(myFlipLongToShort, 'DMI Flip Long To Short');
register_signal(myFlipShortToLong, 'DMI Flip Short To Long');