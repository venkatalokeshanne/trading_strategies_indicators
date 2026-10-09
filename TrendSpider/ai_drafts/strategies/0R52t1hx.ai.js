describe_indicator('Nasdaq NQ 24H Mejorada', 'price');

// === INPUTS ===
const myLen = input.number('Structure Length', 20, { min: 1, max: 500 });
const mySlPct = input.number('Stop Loss %', 1.0, { min: 0.1, max: 100 });
const myTpPct = input.number('Take Profit %', 2.0, { min: 0.1, max: 100 });
const myTrailPct = input.number('Trailing Stop %', 0.5, { min: 0.1, max: 100 });

// === TREND FILTER ===
const myEma200 = ema(close, 200);

// === STRUCTURE ===
const myHighestHigh = highest(high, myLen);
const myLowestLow = lowest(low, myLen);

// shifted by 1 bar (Pine's [1])
const myHighestHighPrev = shift(myHighestHigh, 1);
const myLowestLowPrev = shift(myLowestLow, 1);

// === CROSSOVER / CROSSUNDER (manual, since no built-in crossover function) ===
// crossover: close crosses above highestHigh[1]
// crossunder: close crosses below lowestLow[1]
const myEsAlcista = for_every(close, myHighestHighPrev, shift(close, 1), shift(myHighestHighPrev, 1), (_c, _hh, _pc, _phh, _prev, _i) => {
	if (_hh == null || _phh == null || _pc == null) return false;
	return _pc <= _phh && _c > _hh;
});

const myEsBajista = for_every(close, myLowestLowPrev, shift(close, 1), shift(myLowestLowPrev, 1), (_c, _ll, _pc, _pll, _prev, _i) => {
	if (_ll == null || _pll == null || _pc == null) return false;
	return _pc >= _pll && _c < _ll;
});

// === TREND FILTERS ===
const myFiltroLong = for_every(close, myEma200, (_c, _e) => _c > _e);
const myFiltroShort = for_every(close, myEma200, (_c, _e) => _c < _e);

// === ENTRY CONDITIONS ===
const myLongCondition = for_every(myEsAlcista, myFiltroLong, (_a, _f) => _a && _f);
const myShortCondition = for_every(myEsBajista, myFiltroShort, (_b, _f) => _b && _f);

// === SL / TP PRICES (available for reference, not plotted since not price-axis lines requested) ===
// FIX: div()/sub()/add() require their FIRST argument to be a series, not a
// plain number. mySlPct and myTpPct are plain numbers (from input.number),
// so we wrap them with series_of() before passing them as the first
// argument to div(). This was the root cause of the "first argument is not
// a series" error.
const mySlPctSeries = series_of(mySlPct);
const myTpPctSeries = series_of(myTpPct);

const myLongSl = mult(close, sub(series_of(1), div(mySlPctSeries, 100)));
const myLongTp = mult(close, add(series_of(1), div(myTpPctSeries, 100)));
const myShortSl = mult(close, add(series_of(1), div(mySlPctSeries, 100)));
const myShortTp = mult(close, sub(series_of(1), div(myTpPctSeries, 100)));

// === DAILY CLOSE (23:59 of exchange time) ===
const myCerrarFinDia = for_every(time, _t => {
	const myParts = time_of(_t);
	return myParts.hours == 23 && myParts.minutes == 59;
});

// === PAINT ===
paint(myEma200, { color: 'orange', thickness: 2, name: 'EMA200' });

const myBuyMarks = for_every(myLongCondition, low, (_cond, _l) => _cond ? _l : null);
const mySellMarks = for_every(myShortCondition, high, (_cond, _h) => _cond ? _h : null);

paint(myBuyMarks, { style: 'labels_below', color: 'green', name: 'BuySignal' });
paint(mySellMarks, { style: 'labels_above', color: 'red', name: 'SellSignal' });

// === SIGNALS FOR SCANNERS / ALERTS / STRATEGY TESTER ===
register_signal(myLongCondition, 'Buy Entry');
register_signal(myShortCondition, 'Sell Entry');
register_signal(myCerrarFinDia, 'Daily Close');