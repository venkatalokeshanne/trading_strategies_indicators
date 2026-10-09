// This indicator is a best-effort reimplementation of a Pine Script v6
// strategy that relies on a private external Pine library
// ("richardgong1988/HanJinSignals26"). That library's source code is not
// available to this engine, so each pattern-detection function below is a
// reasonable, self-contained reimplementation of the pattern it is named
// after (Pinbar, Engulfing, Fractal, Harami, Big body). Numeric values may
// not match the original library exactly, bar-for-bar.
//
// TrendSpider Custom JS has no concept of strategy.entry(), pyramiding,
// margin, or alert()/webhook payloads. There is no broker/strategy engine
// here. Instead, every signal is exposed as a register_signal() so it can
// be used in Scanners, Alerts and the Strategy Tester module of
// TrendSpider (which is the native equivalent of a Pine strategy).
describe_indicator('5 Signals 7 Patterns', 'price');

// ─── Inputs ────────────────────────────────────────────────────────
const paramsTab = input.tab('Params');
const myPinLong = paramsTab.number('Pinbar long ratio minimum', 0.667, { min: 0.5, max: 0.95, step: 0.01 });
const myPinShort = paramsTab.number('Pinbar short ratio maximum', 0.2, { min: 0.05, max: 0.5, step: 0.01 });
const myPinStrict = paramsTab.boolean('Pinbar strict', true);
const myBigFrac = paramsTab.number('Big body ratio minimum', 0.7, { min: 0.5, max: 0.95, step: 0.01 });

const enableTab = input.tab('Enable');
const myUseS1 = enableTab.boolean('Pinbar', true);
const myUseS2 = enableTab.boolean('Engulfing', true);
const myUseS3a = enableTab.boolean('Top fractal', true);
const myUseS3b = enableTab.boolean('Bottom fractal', true);
const myUseS4 = enableTab.boolean('Single harami', true);
const myUseS5 = enableTab.boolean('Double harami', true);
const myUseS6 = enableTab.boolean('Big body candle', true);

// ─── Pattern math ────────────────────────────────────────────────────
const myRange = sub(high, low);
const myBody = for_every(open, close, (_o, _c) => Math.abs(_c - _o));

// Pinbar: long lower wick => BUY, long upper wick => SELL
const myPinSignal = for_every(open, high, low, close, (_o, _h, _l, _c) => {
	const myRangeVal = _h - _l;
	if (myRangeVal <= 0) return null;
	const myLowerWick = Math.min(_o, _c) - _l;
	const myUpperWick = _h - Math.max(_o, _c);
	const myLowerRatio = myLowerWick / myRangeVal;
	const myUpperRatio = myUpperWick / myRangeVal;
	if (myLowerRatio >= myPinLong && (!myPinStrict || myUpperRatio <= myPinShort)) return 'BUY';
	if (myUpperRatio >= myPinLong && (!myPinStrict || myLowerRatio <= myPinShort)) return 'SELL';
	return null;
});

// Engulfing
const myPrevOpen = shift(open, 1);
const myPrevClose = shift(close, 1);
const myEngulfSignal = for_every(open, close, myPrevOpen, myPrevClose, (_o, _c, _po, _pc) => {
	const myBullPrev = _pc < _po;
	const myBearPrev = _pc > _po;
	const myBullNow = _c > _o;
	const myBearNow = _c < _o;
	if (myBullPrev && myBullNow && _c > _po && _o < _pc) return 'BUY';
	if (myBearPrev && myBearNow && _c < _po && _o > _pc) return 'SELL';
	return null;
});

// Fractals (classic Williams 5-bar fractal). Top fractal -> SELL marker,
// Bottom fractal -> BUY marker, matching the original Pine plot semantics.
const myFractalHighRaw = fractal_high(high, 5);
const myFractalLowRaw = fractal_low(low, 5);
const myTopSignal = for_every(myFractalHighRaw, _f => _f !== null ? 'SELL' : null);
const myBotSignal = for_every(myFractalLowRaw, _f => _f !== null ? 'BUY' : null);

// Harami (single): small body fully inside previous larger opposite-colored body
const myHaramiSignal = for_every(open, close, myPrevOpen, myPrevClose, (_o, _c, _po, _pc) => {
	const myPrevBullish = _pc > _po;
	const myPrevBearish = _pc < _po;
	const myInside = Math.max(_o, _c) <= Math.max(_po, _pc) && Math.min(_o, _c) >= Math.min(_po, _pc);
	const myPrevBody = Math.abs(_pc - _po);
	const myNowBody = Math.abs(_c - _o);
	if (!myInside || myNowBody >= myPrevBody) return null;
	if (myPrevBearish && _c > _o) return 'BUY';
	if (myPrevBullish && _c < _o) return 'SELL';
	return null;
});

// Double harami: two consecutive small bodies, both inside the candle
// that preceded them (an approximation of a "double inside bar" setup)
const myPrevOpen2 = shift(open, 2);
const myPrevClose2 = shift(close, 2);
const myDoubleHaramiSignal = for_every(open, close, myPrevOpen, myPrevClose, myPrevOpen2, myPrevClose2, (_o, _c, _po, _pc, _po2, _pc2) => {
	const myOuterHigh = Math.max(_po2, _pc2);
	const myOuterLow = Math.min(_po2, _pc2);
	const myOuterBullish = _pc2 > _po2;
	const myOuterBearish = _pc2 < _po2;
	const myBar1Inside = Math.max(_po, _pc) <= myOuterHigh && Math.min(_po, _pc) >= myOuterLow;
	const myBar2Inside = Math.max(_o, _c) <= myOuterHigh && Math.min(_o, _c) >= myOuterLow;
	if (!myBar1Inside || !myBar2Inside) return null;
	if (myOuterBearish && _c > _o) return 'BUY';
	if (myOuterBullish && _c < _o) return 'SELL';
	return null;
});

// Big body candle
const myBigBodySignal = for_every(open, close, myBody, myRange, (_o, _c, _b, _r) => {
	if (_r <= 0) return null;
	if (_b / _r < myBigFrac) return null;
	return _c > _o ? 'BUY' : 'SELL';
});

// ─── Apply enable toggles ──────────────────────────────────────────
const myPin = myUseS1 ? myPinSignal : constants.empty_series;
const myEng = myUseS2 ? myEngulfSignal : constants.empty_series;
const myTop = myUseS3a ? myTopSignal : constants.empty_series;
const myBot = myUseS3b ? myBotSignal : constants.empty_series;
const myHar = myUseS4 ? myHaramiSignal : constants.empty_series;
const myDbl = myUseS5 ? myDoubleHaramiSignal : constants.empty_series;
const myBig = myUseS6 ? myBigBodySignal : constants.empty_series;

// ─── Markers (labels on candles) ────────────────────────────────────
paint(for_every(myPin, _s => _s === 'BUY' ? constants.icons.triangle_up : null), { style: 'labels_below', color: 'lime', name: 'Pinbar Buy' });
paint(for_every(myPin, _s => _s === 'SELL' ? constants.icons.triangle_down : null), { style: 'labels_above', color: 'red', name: 'Pinbar Sell' });
paint(for_every(myEng, _s => _s === 'BUY' ? constants.icons.circle : null), { style: 'labels_below', color: 'green', name: 'Engulf Buy' });
paint(for_every(myEng, _s => _s === 'SELL' ? constants.icons.circle : null), { style: 'labels_above', color: 'maroon', name: 'Engulf Sell' });
paint(for_every(myTop, _s => _s === 'SELL' ? constants.icons.star : null), { style: 'labels_above', color: 'orange', name: 'Top Fractal' });
paint(for_every(myBot, _s => _s === 'BUY' ? constants.icons.star : null), { style: 'labels_below', color: 'aqua', name: 'Bottom Fractal' });
paint(for_every(myHar, _s => _s === 'BUY' ? constants.icons.diamond : null), { style: 'labels_below', color: 'teal', name: 'Harami Buy' });
paint(for_every(myHar, _s => _s === 'SELL' ? constants.icons.diamond : null), { style: 'labels_above', color: 'purple', name: 'Harami Sell' });
paint(for_every(myDbl, _s => _s === 'BUY' ? constants.icons.square : null), { style: 'labels_below', color: 'teal', name: 'Double Harami Buy' });
paint(for_every(myDbl, _s => _s === 'SELL' ? constants.icons.square : null), { style: 'labels_above', color: 'purple', name: 'Double Harami Sell' });
paint(for_every(myBig, _s => _s === 'BUY' ? constants.icons.flag : null), { style: 'labels_below', color: 'green', name: 'Big Body Buy' });
paint(for_every(myBig, _s => _s === 'SELL' ? constants.icons.flag : null), { style: 'labels_above', color: 'red', name: 'Big Body Sell' });

// ─── Signals for Scanner / Alerts / Strategy Tester ─────────────────
// Note: register_signal names must not collide with paint() names or
// with each other, so these are suffixed with "Signal" to keep every
// output name unique across the whole indicator.
register_signal(for_every(myPin, _s => _s === 'BUY'), 'Pinbar Buy Signal');
register_signal(for_every(myPin, _s => _s === 'SELL'), 'Pinbar Sell Signal');
register_signal(for_every(myEng, _s => _s === 'BUY'), 'Engulfing Buy Signal');
register_signal(for_every(myEng, _s => _s === 'SELL'), 'Engulfing Sell Signal');
register_signal(for_every(myTop, _s => _s === 'SELL'), 'Top Fractal Signal');
register_signal(for_every(myBot, _s => _s === 'BUY'), 'Bottom Fractal Signal');
register_signal(for_every(myHar, _s => _s === 'BUY'), 'Harami Buy Signal');
register_signal(for_every(myHar, _s => _s === 'SELL'), 'Harami Sell Signal');
register_signal(for_every(myDbl, _s => _s === 'BUY'), 'Double Harami Buy Signal');
register_signal(for_every(myDbl, _s => _s === 'SELL'), 'Double Harami Sell Signal');
register_signal(for_every(myBig, _s => _s === 'BUY'), 'Big Body Buy Signal');
register_signal(for_every(myBig, _s => _s === 'SELL'), 'Big Body Sell Signal');