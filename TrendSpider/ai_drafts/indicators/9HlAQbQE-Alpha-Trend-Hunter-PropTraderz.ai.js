describe_indicator('Alpha Trend Hunter PropTraderz', 'price');

// ── Inputs ──────────────────────────────────────────────────────────
const myHeikenGroup = input.group('Heiken Settings');
const myHkPeriod = myHeikenGroup.number('HA Period', 14, { min: 1, max: 200 });
const mySmoothLen = myHeikenGroup.number('Smooth', 2, { min: 1, max: 100 });

const myTrendGroup = input.group('Trend Filter');
const myAtrLen = myTrendGroup.number('ATR Period', 2, { min: 1, max: 200 });
const myStFactor = myTrendGroup.number('Factor', 2.0, { min: 0.01, max: 20, step: 0.01 });

// ── Heiken Ashi EMA values ──────────────────────────────────────────
const myHkOpen = ema(open, myHkPeriod);
const myHkClose = ema(close, myHkPeriod);
const myHkHigh = ema(high, myHkPeriod);
const myHkLow = ema(low, myHkPeriod);
const myHkTypical = div(add(add(myHkOpen, myHkHigh), add(myHkLow, myHkClose)), 4);

// recursive synthetic "open" of the Heiken Ashi, replicated via for_every
// using the previous output and the previous candle's typical value
const myShiftedTypical = shift(myHkTypical, 1);
const myHkPrev = for_every(myHkOpen, myHkClose, myShiftedTypical, (_o, _c, _st, _prev, _idx) => {
	if (_idx === 0) {
		return (_o + _c) / 2;
	}
	const myPrevValue = _prev == null ? 0 : _prev;
	return (myPrevValue + _st) / 2;
});

const myHkMax = max_of(myHkHigh, max_of(myHkPrev, myHkTypical));
const myHkMin = min_of(myHkLow, min_of(myHkPrev, myHkTypical));
const myMidLine = add(myHkMin, div(sub(myHkMax, myHkMin), 2));
const myBarColor = for_every(myHkPrev, myHkTypical, (_prev, _typ) => _prev > _typ ? '#ff0057' : '#00dbff');
const myTrendLine = ema(myMidLine, mySmoothLen);

paint(myTrendLine, { name: 'TrendLine', color: myBarColor, thickness: 3 });

// ── SuperTrend Filter ────────────────────────────────────────────────
// Fix: supertrend() returns a plain series (the ST line itself), not an
// object with "value"/"direction" properties. Direction is derived here
// by comparing price to the ST line (bullish when close is above it).
const myStLine = supertrend(myAtrLen, myStFactor, false);
const myStDir = for_every(close, myStLine, (_c, _l) => _c >= _l ? -1 : 1);

const myCandleMid = div(add(open, close), 2);
const myBullTrendLine = for_every(myStDir, myStLine, (_d, _l) => _d < 0 ? _l : null);
const myBearTrendLine = for_every(myStDir, myStLine, (_d, _l) => _d < 0 ? null : _l);

const myCandleMidPainted = paint(myCandleMid, { name: 'CandleMid', hidden: true });
const myBullTrendPainted = paint(myBullTrendLine, { name: 'BullTrend', color: 'green', style: 'line' });
const myBearTrendPainted = paint(myBearTrendLine, { name: 'BearTrend', color: 'red', style: 'line' });

fill(myCandleMidPainted, myBullTrendPainted, '#00dbff', 0.1);
fill(myCandleMidPainted, myBearTrendPainted, '#ff0057', 0.1);

// ── Signal Logic ───────────────────────────────────────────────────
const myHkBull = for_every(myHkPrev, myHkTypical, (_prev, _typ) => _prev < _typ);
const myHkBear = for_every(myHkPrev, myHkTypical, (_prev, _typ) => _prev > _typ);
const myStBull = for_every(myStDir, _d => _d < 0);
const myStBear = for_every(myStDir, _d => _d > 0);

const myGoLong = for_every(myHkBull, myStBull, (_a, _b) => _a && _b);
const myGoShort = for_every(myHkBear, myStBear, (_a, _b) => _a && _b);

const myPrevGoLong = shift(myGoLong, 1);
const myPrevGoShort = shift(myGoShort, 1);

const mySignal = for_every(myGoLong, myGoShort, myPrevGoLong, myPrevGoShort, (_gl, _gs, _pgl, _pgs, _prev, _idx) => {
	let mySignalValue = _prev == null ? 0 : _prev;
	if (_gl && !_pgl && mySignalValue !== 1) {
		mySignalValue = 1;
	}
	if (_gs && !_pgs && mySignalValue !== -1) {
		mySignalValue = -1;
	}
	return mySignalValue;
});

const myPrevSignal = shift(mySignal, 1);
const myBuySignal = for_every(mySignal, myPrevSignal, (_s, _ps) => _s === 1 && _s !== _ps);
const mySellSignal = for_every(mySignal, myPrevSignal, (_s, _ps) => _s === -1 && _s !== _ps);

register_signal(myBuySignal, 'BuySignal');
register_signal(mySellSignal, 'SellSignal');

const myBuyLabelSeries = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellLabelSeries = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyLabelSeries, { name: 'Buy', style: 'labels_below', color: '#00dbff' });
paint(mySellLabelSeries, { name: 'Sell', style: 'labels_above', color: '#ff0057' });