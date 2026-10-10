describe_indicator('AS 1M Smart Money Strategy', 'price');

/*
 * This is a best-effort port of the supplied Pine Script strategy into the
 * TrendSpider Custom JS engine. Some Pine Script features (box.new, bgcolor,
 * strategy.entry/exit execution, plot.style_stepline) have no direct
 * equivalent in this API - see notes at the bottom.
 */

// ───────────────── INPUTS ─────────────────
const myTrendTab = input.tab('Trend Lengths');
const myLenSma9 = myTrendTab.number('Trigger SMA', 7, { min: 1, max: 500 });
const myLenSma20 = myTrendTab.number('Fast Trend', 20, { min: 1, max: 500 });
const myLenSma50 = myTrendTab.number('Short Trend', 50, { min: 1, max: 500 });
const myLenSma89 = myTrendTab.number('Classic Trend', 89, { min: 1, max: 500 });
const myLenSma200 = myTrendTab.number('Standard Filter', 200, { min: 1, max: 1000 });
const myLenSma500 = myTrendTab.number('Macro Filter', 500, { min: 1, max: 2000 });

const myRiskTab = input.tab('Risk and Session');
const myTpMult = myRiskTab.number('Take Profit ATR Mult', 2.5, { min: 0.1, max: 20 });
const mySlMult = myRiskTab.number('Stop Loss ATR Mult', 1.5, { min: 0.1, max: 20 });
const myUseTime = myRiskTab.boolean('Only US Session', true);
const myShowSession = myRiskTab.boolean('Highlight Session', true);

// ───────────────── CORE CALCULATIONS ─────────────────
const mySma9 = sma(close, myLenSma9);
const mySma20 = sma(close, myLenSma20);
const mySma50 = sma(close, myLenSma50);
const mySma89 = sma(close, myLenSma89);
const mySma200 = sma(close, myLenSma200);
const mySma500 = sma(close, myLenSma500);

const myAtr = atr(high, low, close, 14);
const myAtrShort = atr(high, low, close, 5);

const myBbBasis = sma(close, 20);
const myBbDev = stdev(close, 20);
const myBbUpper = add(myBbBasis, mult(myBbDev, 2));
const myBbLower = sub(myBbBasis, mult(myBbDev, 2));
const myBbWidth = div(sub(myBbUpper, myBbLower), myBbBasis);

const myIsExpansion = for_every(myAtrShort, myAtr, (_a, _b) => _a > _b);
const myBbWidthLowest50 = lowest(myBbWidth, 50);
const myIsSqueeze = for_every(myBbWidth, myBbWidthLowest50, (_w, _lw) => _w < _lw * 1.1);
const myValidMarket = for_every(myIsExpansion, myIsSqueeze, (_exp, _sq) => _exp && !_sq);

// Liquidity sweeps & FVG
const mySwingHigh = highest(high, 15);
const mySwingLow = lowest(low, 15);
const mySwingHighPrev = shift(mySwingHigh, 1);
const mySwingLowPrev = shift(mySwingLow, 1);
const myLiqSweepHigh = for_every(high, close, mySwingHighPrev, (_h, _c, _sh) => _h > _sh && _c < _sh);
const myLiqSweepLow = for_every(low, close, mySwingLowPrev, (_l, _c, _sl) => _l < _sl && _c > _sl);

const myHighShift2 = shift(high, 2);
const myLowShift2 = shift(low, 2);
const myBullFvg = for_every(low, myHighShift2, (_l, _h2) => _l > _h2);
const myBearFvg = for_every(high, myLowShift2, (_h, _l2) => _h < _l2);

// Trend & cross
const myBullTrend = for_every(close, mySma50, mySma500, (_c, _s50, _s500) => _c > _s50 && _s50 > _s500);
const myBearTrend = for_every(close, mySma50, mySma500, (_c, _s50, _s500) => _c < _s50 && _s50 < _s500);
const myClosePrev = shift(close, 1);
const mySma9Prev = shift(mySma9, 1);
const myBullCross = for_every(close, mySma9, myClosePrev, mySma9Prev, (_c, _s, _cp, _sp) => _c > _s && _cp <= _sp);
const myBearCross = for_every(close, mySma9, myClosePrev, mySma9Prev, (_c, _s, _cp, _sp) => _c < _s && _cp >= _sp);

// ───────────────── SCORE ENGINE ─────────────────
const myScoreLong = for_every(myBullTrend, myBullCross, myBullFvg, myLiqSweepLow, (_a, _b, _c, _d) =>
	(_a ? 1 : 0) + (_b ? 1 : 0) + (_c ? 1 : 0) + (_d ? 1 : 0));
const myScoreShort = for_every(myBearTrend, myBearCross, myBearFvg, myLiqSweepHigh, (_a, _b, _c, _d) =>
	(_a ? 1 : 0) + (_b ? 1 : 0) + (_c ? 1 : 0) + (_d ? 1 : 0));

const myConfLong = mult(myScoreLong, 25);
const myConfShort = mult(myScoreShort, 25);

// US session time filter: Mon-Fri 09:30-16:00 (exchange time zone)
const myIsUsSession = time.map(_t => {
	const myParsed = time_of(_t);
	const myMinutesOfDay = myParsed.hours * 60 + myParsed.minutes;
	const myInWeekday = myParsed.dayOfWeek >= 1 && myParsed.dayOfWeek <= 5;
	const myInSessionWindow = myMinutesOfDay >= (9 * 60 + 30) && myMinutesOfDay <= (16 * 60);
	return myInWeekday && myInSessionWindow;
});

const myTimeCondition = for_every(series_of(myUseTime ? 1 : 0), myIsUsSession, (_use, _sess) => _use ? _sess : true);

const myLongSignal = for_every(myScoreLong, myValidMarket, myTimeCondition, (_sl, _vm, _tc) => _sl >= 3 && _vm && _tc);
const myShortSignal = for_every(myScoreShort, myValidMarket, myTimeCondition, (_ss, _vm, _tc) => _ss >= 3 && _vm && _tc);

register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');

// ───────────────── RISK LEVELS (informational only) ─────────────────
const myLongStop = sub(close, mult(myAtr, mySlMult));
const myLongTarget = add(close, mult(myAtr, myTpMult));
const myShortStop = add(close, mult(myAtr, mySlMult));
const myShortTarget = sub(close, mult(myAtr, myTpMult));

// ───────────────── VISUALS ─────────────────
// Candle coloring, mirrors the Pine barcolor() priority logic
const myCandleColors = for_every(myLongSignal, myShortSignal, close, mySma9, (_long, _short, _c, _s9) => {
	if (_long) return 'green';
	if (_short) return 'red';
	return _c > _s9 ? 'rgba(0,255,8,0.3)' : 'rgba(255,0,0,0.3)';
});
color_candles(myCandleColors);

// Trend SMAs (closest style to Pine's plot.style_stepline is 'ladder')
paint(mySma500, { name: 'Macro Trend', color: '#7f009c', thickness: 2, style: 'ladder' });
paint(mySma200, { name: 'Standard Trend', color: '#0059a1', thickness: 2, style: 'ladder' });
paint(mySma89, { name: 'Classic Term Trend', color: '#6b6b6b', thickness: 2, style: 'ladder' });
paint(mySma50, { name: 'Short Term Trend', color: '#a10000', thickness: 1, style: 'ladder' });
paint(mySma20, { name: 'Fast Term Trend', color: '#a1a100', thickness: 1, style: 'ladder' });
paint(mySma9, { name: 'Trigger SMA', color: '#5a5a5a', thickness: 1, style: 'ladder' });

// Entry markers
paint(for_every(myLongSignal, (_v) => _v ? low : null), { name: 'Long Signal Marker', style: 'labels_below', color: 'green' });
paint(for_every(myShortSignal, (_v) => _v ? high : null), { name: 'Short Signal Marker', style: 'labels_above', color: 'red' });

// ───────────────── DASHBOARD ─────────────────
const myLastIndex = close.length - 1;
const myTrendTxt = myBullTrend[myLastIndex] ? 'UP' : (myBearTrend[myLastIndex] ? 'DOWN' : 'RANGE');
const myTrendColor = myBullTrend[myLastIndex] ? 'green' : (myBearTrend[myLastIndex] ? 'red' : 'gray');
const myConfLongColor = myConfLong[myLastIndex] >= 75 ? 'green' : 'white';
const myConfShortColor = myConfShort[myLastIndex] >= 75 ? 'red' : 'white';
const myVolatilityTxt = myIsExpansion[myLastIndex] ? 'EXPANSION' : 'SQUEEZE';
const myVolatilityColor = myIsExpansion[myLastIndex] ? 'green' : 'orange';

paint_overlay('SmartMoneyDashboard', { position: 'bottom_left' }, {
	rows: [
		{ cells: [{ text: 'Trend', background_color: 'rgba(128,128,128,0.1)' }, { text: myTrendTxt, color: myTrendColor }] },
		{ cells: [{ text: 'Long Pct', background_color: 'rgba(128,128,128,0.1)' }, { text: `${myConfLong[myLastIndex]}%`, color: myConfLongColor }] },
		{ cells: [{ text: 'Short Pct', background_color: 'rgba(128,128,128,0.1)' }, { text: `${myConfShort[myLastIndex]}%`, color: myConfShortColor }] },
		{ cells: [{ text: 'Volatility', background_color: 'rgba(128,128,128,0.1)' }, { text: myVolatilityTxt, color: myVolatilityColor }] }
	]
});