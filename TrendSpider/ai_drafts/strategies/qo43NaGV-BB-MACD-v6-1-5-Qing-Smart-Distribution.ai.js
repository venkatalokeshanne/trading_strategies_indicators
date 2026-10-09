describe_indicator('Qing BB and MACD Smart Distribution', 'price');

// NOTE: This indicator cannot replicate Pine's strategy.position_size
// state (it has no backtest/position engine). The buy/exit markers
// are therefore shown purely based on the raw signal conditions,
// without filtering for "currently in/out of a position". Use the
// registered signals in Strategy Tester to simulate actual position
// logic.

const myTab = input.tab('Bollinger Bands');
const myBbLength = myTab.number('BB Length', 20, { min: 1, max: 300 });
const myBbMult = myTab.number('BB Multiplier', 2, { min: 0.1, max: 10 });

const myMacdTab = input.tab('MACD');
const myFastLen = myMacdTab.number('MACD Fast Length', 6, { min: 1, max: 100 });
const mySlowLen = myMacdTab.number('MACD Slow Length', 12, { min: 1, max: 200 });
const mySigLen = myMacdTab.number('MACD Signal Length', 8, { min: 1, max: 100 });

const myFiltersTab = input.tab('Filters');
const myAtrMult = myFiltersTab.number('Exit ATR Buffer (Trend End)', 0.5, { min: 0, max: 10 });
const myUseVol = myFiltersTab.boolean('Require Volume Confirmation', true);

// ===== Core computations =====
const myBasis = sma(close, myBbLength);
const myDev = mult(stdev(close, myBbLength), myBbMult);
const myUpper = add(myBasis, myDev);
const myLower = sub(myBasis, myDev);

const myMacdLine = sub(ema(close, myFastLen), ema(close, mySlowLen));
const mySignalLine = ema(myMacdLine, mySigLen);
const myHist = sub(myMacdLine, mySignalLine);

const myAtr = atr(high, low, close, 14);
const myAvgVol = sma(volume, 20);

const myVolOK = myUseVol
	? for_every(volume, myAvgVol, (_v, _a) => _v >= _a)
	: for_every(close, (_c) => true);

// ===== Entry logic =====
const myIsSolidMomentum = for_every(
	myMacdLine,
	mySignalLine,
	myHist,
	shift(myHist, 1),
	(_m, _s, _h, _ph) => _m > _s && _h > 0 && _h > _ph
);

const myPriceBreakout = for_every(
	close,
	myBasis,
	shift(close, 1),
	shift(myBasis, 1),
	myIsSolidMomentum,
	(_c, _b, _pc, _pb, _solid, _idx) => (_c > _b && _pc <= _pb) && _solid
);

const myMacdBreakout = for_every(
	myMacdLine,
	mySignalLine,
	shift(myMacdLine, 1),
	shift(mySignalLine, 1),
	close,
	myBasis,
	myHist,
	(_m, _s, _pm, _ps, _c, _b, _h) => (_m > _s && _pm <= _ps) && (_c > _b) && (_h > 0)
);

const myEntrySignal = for_every(
	myPriceBreakout,
	myMacdBreakout,
	myVolOK,
	close,
	open,
	(_pb, _mb, _vol, _c, _o) => (_pb || _mb) && _vol && (_c > _o)
);

// ===== Exit logic =====
const myNearUpperBB = for_every(
	highest(high, 3),
	shift(myUpper, 1),
	(_hh, _pu) => _hh >= _pu
);

const myMacdBleeding = for_every(
	myHist,
	shift(myHist, 1),
	shift(myHist, 2),
	(_h, _ph, _pph) => (_h < _ph) && (_ph < _pph)
);

const myPriceStalling = for_every(
	close,
	open,
	shift(close, 1),
	(_c, _o, _pc) => (_c < _o) && (_c <= _pc)
);

const myExitDistribution = for_every(
	myNearUpperBB,
	myMacdBleeding,
	myPriceStalling,
	(_near, _bleed, _stall) => _near && _bleed && _stall
);

const myExitTrendEnd = for_every(
	close,
	myBasis,
	myAtr,
	open,
	(_c, _b, _a, _o) => (_c < (_b - (_a * myAtrMult))) && (_c < _o)
);

const myExitExhaustion = for_every(
	close,
	myUpper,
	myMacdLine,
	mySignalLine,
	(_c, _u, _m, _s) => (_c > _u) && (_m > 0) && (_m > (_s * 2.5))
);

// ===== Signals for scanners/strategies/alerts =====
register_signal(myEntrySignal, 'Entry Signal');
register_signal(myExitDistribution, 'Exit Distribution');
register_signal(myExitTrendEnd, 'Exit Trend End');
register_signal(myExitExhaustion, 'Exit Blowoff Exhaustion');

// ===== Plotting =====
paint(myBasis, { name: 'Basis', color: 'white', thickness: 2 });

const myUpperLinePainted = paint(myUpper, { name: 'Upper', color: '#F23645' });
const myLowerLinePainted = paint(myLower, { name: 'Lower', color: '#089981' });
fill(myUpperLinePainted, myLowerLinePainted, 'blue', 0.1);

paint(sub(myBasis, mult(myAtr, myAtrMult)), { name: 'Exit Buffer Limit', color: 'orange', style: 'dotted' });

// Markers (position-state filtering is not available, see note above)
const myBuyMarker = for_every(myEntrySignal, (_e) => (_e ? constants.icons.triangle_up : null));
paint(myBuyMarker, { name: 'Buy Signal', style: 'labels_below', color: 'green' });

const myDistMarker = for_every(myExitDistribution, (_e) => (_e ? constants.icons.triangle_down : null));
paint(myDistMarker, { name: 'Distribution Exit', style: 'labels_above', color: 'fuchsia' });

const myBlowoffMarker = for_every(myExitExhaustion, (_e) => (_e ? constants.icons.triangle_down : null));
paint(myBlowoffMarker, { name: 'Blowoff Exit', style: 'labels_above', color: 'orange' });