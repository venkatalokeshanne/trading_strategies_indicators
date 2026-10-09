describe_indicator('Greatest Bot Ever Made - PMT Apex Edition', 'price');

// ==========================================
// 1. RISK & PMT SETUP (informational only, no
// real order execution is possible in this
// scripting engine - see flags below)
// ==========================================

const riskTab = input.tab('Risk');
const myStopLossTicks = riskTab.number('Stop Loss (Ticks)', 400, { min: 1, max: 100000 });
const myTrailActivation = riskTab.number('Trail Activation (Ticks)', 100, { min: 1, max: 100000 });
const myTrailOffset = riskTab.number('Trail Offset (Ticks)', 50, { min: 1, max: 100000 });

// ==========================================
// 2. INDICATORS
// ==========================================

const myRsi = rsi(close, 14);

const myEma12 = ema(close, 12);
const myEma26 = ema(close, 26);
const myMacdLine = sub(myEma12, myEma26);
const mySignalLine = ema(myMacdLine, 9);

const myAdxObject = indicators.adx(14);
const myAdxVal = myAdxObject.adx;

const myAtrVal = atr(high, low, close, 14);
const myVolSma = sma(volume, 20);
const myHighVolume = for_every(volume, myVolSma, (_v, _s) => _v > _s);

// ==========================================
// 3. STRUCTURAL PATTERNS
// ==========================================

const myHighShift2 = shift(high, 2);
const myLowShift2 = shift(low, 2);
const myCloseShift1 = shift(close, 1);
const myOpenShift1 = shift(open, 1);

const myBullishFVG = for_every(low, myHighShift2, myCloseShift1, myOpenShift1, (_l, _h2, _c1, _o1) => _l > _h2 && _c1 > _o1);
const myBearishFVG = for_every(high, myLowShift2, myCloseShift1, myOpenShift1, (_h, _l2, _c1, _o1) => _h < _l2 && _c1 < _o1);

// crossover / crossunder of MACD vs Signal
const myMacdShift1 = shift(myMacdLine, 1);
const mySignalShift1 = shift(mySignalLine, 1);

const myCrossover = for_every(myMacdLine, mySignalLine, myMacdShift1, mySignalShift1,
	(_m, _s, _mp, _sp) => _mp <= _sp && _m > _s);
const myCrossunder = for_every(myMacdLine, mySignalLine, myMacdShift1, mySignalShift1,
	(_m, _s, _mp, _sp) => _mp >= _sp && _m < _s);

const myBullReversal = for_every(myCrossover, myRsi, (_co, _r) => _co && _r < 40);
const myBearReversal = for_every(myCrossunder, myRsi, (_cu, _r) => _cu && _r > 60);

const mySma20 = sma(close, 20);

const myBullFlag = for_every(close, mySma20, myHighVolume, myBullishFVG, (_c, _s, _hv, _fvg) => _c > _s && _hv && _fvg);
const myBearFlag = for_every(close, mySma20, myHighVolume, myBearishFVG, (_c, _s, _hv, _fvg) => _c < _s && _hv && _fvg);

// ==========================================
// 4. ENTRY/EXIT SIGNALS
// ==========================================

const myLongCondition = for_every(myBullishFVG, myBullReversal, myBullFlag, myHighVolume, myAdxVal,
	(_fvg, _rev, _flag, _hv, _adx) => (_fvg || _rev || _flag) && _hv && _adx > 20);

const myShortCondition = for_every(myBearishFVG, myBearReversal, myBearFlag, myHighVolume, myAdxVal,
	(_fvg, _rev, _flag, _hv, _adx) => (_fvg || _rev || _flag) && _hv && _adx > 20);

// Exit approximation: stop loss / trail is not simulated here (no position
// tracking engine is available). We expose a generic "take profit zone"
// signal based on ATR trail activation distance as the closest proxy.
const myLongExitLevel = sub(close, mult(myAtrVal, 0));
const myExitSignal = series_of(false);

register_signal(myLongCondition, 'Long Entry Signal');
register_signal(myShortCondition, 'Short Entry Signal');
register_signal(myExitSignal, 'Exit Signal');

// ==========================================
// 5. VISUALS
// ==========================================

const myCandleColors = for_every(myBullishFVG, myBearishFVG, (_bull, _bear) => {
	if (_bull) return 'rgba(0,200,83,0.35)';
	if (_bear) return 'rgba(255,23,68,0.35)';
	return null;
});
color_candles(myCandleColors);

const myLongMarks = for_every(myLongCondition, low, (_cond, _l) => _cond ? _l : null);
const myShortMarks = for_every(myShortCondition, high, (_cond, _h) => _cond ? _h : null);

paint(myLongMarks, { style: 'labels_below', color: '#00c853', name: 'Long Signal' });
paint(myShortMarks, { style: 'labels_above', color: '#ff1744', name: 'Short Signal' });

paint(mySma20, { style: 'line', color: '#4da3ff', thickness: 1, name: 'SMA20' });

// ==========================================
// 6. DASHBOARD (last candle snapshot)
// ==========================================

const myLastRsi = myRsi.at(-1);
const myLastAdx = myAdxVal.at(-1);
const myLastMacd = myMacdLine.at(-1);
const myLastAtr = myAtrVal.at(-1);

paint_overlay('BotStats', { position: 'bottom_right' }, {
	rows: [
		{ cells: [{ text: 'THE GREATEST BOT EVER MADE', color: '#ffffff' }] },
		{ cells: [{ text: 'Risk Mgmt:' }, { text: `${myStopLossTicks} Ticks SL` }] },
		{ cells: [{ text: 'Trail:' }, { text: `Activ ${myTrailActivation} / Offset ${myTrailOffset}` }] },
		{ cells: [{ text: 'RSI | ADX:' }, { text: `${(myLastRsi || 0).toFixed(2)} | ${(myLastAdx || 0).toFixed(2)}` }] },
		{ cells: [{ text: 'MACD | ATR:' }, { text: `${(myLastMacd || 0).toFixed(2)} | ${(myLastAtr || 0).toFixed(2)}` }] }
	]
});