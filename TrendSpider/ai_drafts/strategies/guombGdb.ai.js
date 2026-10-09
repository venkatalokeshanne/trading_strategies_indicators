describe_indicator('Nasdaq NQ 24H Mejorada', 'price');

// === INPUTS ===
const myLen = input.number('Structure Length', 20, { min: 1, max: 500 });
const mySlPct = input.number('Stop Loss %', 1.0, { min: 0.1, max: 100 });
const myTpPct = input.number('Take Profit %', 2.0, { min: 0.1, max: 100 });
const myTrailPct = input.number('Trailing Stop %', 0.5, { min: 0.1, max: 100 });

// === TREND FILTER ===
const myEma200 = ema(close, 200);

// === STRUCTURE (trailing highest/lowest) ===
const myHighestHigh = highest(high, myLen);
const myLowestLow = lowest(low, myLen);

// shift by 1 candle, like Pine's [1]
const myHighestHighPrev = shift(myHighestHigh, 1);
const myLowestLowPrev = shift(myLowestLow, 1);

// === CROSSOVER / CROSSUNDER ===
// esAlcista = ta.crossover(close, highestHigh[1])
const myEsAlcista = for_every(close, shift(close, 1), myHighestHighPrev, shift(myHighestHighPrev, 1),
	(_close, _closePrev, _hhPrev, _hhPrevPrev) => {
		if (_closePrev === null || _hhPrevPrev === null) return false;
		return _closePrev <= _hhPrevPrev && _close > _hhPrev;
	});

// esBajista = ta.crossunder(close, lowestLow[1])
const myEsBajista = for_every(close, shift(close, 1), myLowestLowPrev, shift(myLowestLowPrev, 1),
	(_close, _closePrev, _llPrev, _llPrevPrev) => {
		if (_closePrev === null || _llPrevPrev === null) return false;
		return _closePrev >= _llPrevPrev && _close < _llPrev;
	});

// === TREND FILTERS ===
const myFiltroLong = for_every(close, myEma200, (_close, _ema) => _close > _ema);
const myFiltroShort = for_every(close, myEma200, (_close, _ema) => _close < _ema);

// === ENTRIES ===
const myLongCondition = for_every(myEsAlcista, myFiltroLong, (_a, _f) => _a && _f);
const myShortCondition = for_every(myEsBajista, myFiltroShort, (_b, _f) => _b && _f);

// === SL / TP PRICES (for reference, informational only) ===
// mySlPct/myTpPct are plain numbers (not series), so the multipliers
// below must be computed with plain JS math, not with sub()/div()/add(),
// which require their first argument to be a series. This was the cause
// of the "first argument is not a series" error.
const myLongSlFactor = 1 - (mySlPct / 100);
const myLongTpFactor = 1 + (myTpPct / 100);
const myShortSlFactor = 1 + (mySlPct / 100);
const myShortTpFactor = 1 - (myTpPct / 100);

const myLongSl = mult(close, myLongSlFactor);
const myLongTp = mult(close, myLongTpFactor);
const myShortSl = mult(close, myShortSlFactor);
const myShortTp = mult(close, myShortTpFactor);

// === DAILY CLOSE TIME ===
// cerrarFinDia = (hour == 23 and minute == 59)
const myCerrarFinDia = for_every(time, _t => {
	const myTimeInfo = time_of(_t);
	return myTimeInfo.hours === 23 && myTimeInfo.minutes === 59;
});

// === VISUAL ===
paint(myEma200, { name: 'EMA200', color: 'orange', thickness: 2, forceUsePriceAxis: true });

const myBuyMarks = for_every(myLongCondition, _c => _c ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myShortCondition, _c => _c ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// === SIGNALS FOR SCANNER / ALERTS / STRATEGY TESTER ===
register_signal(myLongCondition, 'Buy Entry');
register_signal(myShortCondition, 'Sell Entry');
register_signal(myCerrarFinDia, 'Daily Close');