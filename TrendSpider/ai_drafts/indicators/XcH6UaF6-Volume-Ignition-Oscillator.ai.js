describe_indicator('Volume Ignition Oscillator', 'lower');

// NOTE: TrendSpider Custom JS API has no equivalent to Pine's
// color.from_gradient() or bgcolor(); the gradient bar coloring and
// the "watch window" background shading from the original script
// are approximated with flat colors instead.

const moveTab = input.tab('Big Move Detection');
const myBigMoveLen = moveTab.number('Move Lookback bars', 5, { min: 1 });
const myAtrLen = moveTab.number('ATR Length', 14, { min: 1 });
const myBigMoveMult = moveTab.number('Move Threshold x ATR', 2.0, { min: 0.1 });
const myPostMoveBars = moveTab.number('Post Move Watch Window bars', 8, { min: 1 });

const volTab = input.tab('Volume');
const myVolLen = volTab.number('Volume MA Length', 20, { min: 1 });

const rangeTab = input.tab('Range Position');
const myRangeLen = rangeTab.number('Range Lookback bars', 20, { min: 2 });
const myTopZone = rangeTab.number('Top Zone Threshold', 0.75, { min: 0.5, max: 0.95 });
const myBottomZone = rangeTab.number('Bottom Zone Threshold', 0.25, { min: 0.05, max: 0.5 });

const sigTab = input.tab('Signal');
const mySmoothLen = sigTab.number('Oscillator Smoothing', 3, { min: 1 });
const mySignalThresh = sigTab.number('Signal Trigger Level', 0.15, { min: 0.01 });

const myBearColor = '#ef5350';
const myBullColor = '#26a69a';

// Big move detection
const myAtrVal = atr(high, low, close, myAtrLen);
const myPriceMove = sub(close, shift(close, myBigMoveLen));

const myBigMoveUp = for_every(myPriceMove, myAtrVal, (_p, _a) => _p > myBigMoveMult * _a);
const myBigMoveDown = for_every(myPriceMove, myAtrVal, (_p, _a) => _p < -myBigMoveMult * _a);

const myBarsSinceUp = for_every(myBigMoveUp, (_b, _prev) => _b ? 0 : (_prev == null ? 9999 : _prev) + 1);
const myBarsSinceDown = for_every(myBigMoveDown, (_b, _prev) => _b ? 0 : (_prev == null ? 9999 : _prev) + 1);

const myGateTop = for_every(myBarsSinceUp, _b => _b <= myPostMoveBars);
const myGateBottom = for_every(myBarsSinceDown, _b => _b <= myPostMoveBars);

// Range position
const myHH = highest(high, myRangeLen);
const myLL = lowest(low, myRangeLen);
const myRangeSize = sub(myHH, myLL);

const myPosInRange = for_every(close, myLL, myRangeSize, (_c, _l, _r) => _r !== 0 ? (_c - _l) / _r : 0.5);

const myInTop = for_every(myPosInRange, _p => _p >= myTopZone);
const myInBottom = for_every(myPosInRange, _p => _p <= myBottomZone);

// Volume surge
const myVolSMA = sma(volume, myVolLen);
const myVolRatio = for_every(volume, myVolSMA, (_v, _s) => _s !== 0 ? _v / _s : 1.0);
const myVolExcess = for_every(myVolRatio, _r => Math.max(_r - 1.0, 0.0));

// Oscillator value
const myOscTopRaw = for_every(myGateTop, myInTop, myVolExcess, myPosInRange, (_gt, _it, _ve, _p) => (_gt && _it) ? _ve * _p : 0.0);
const myOscBottomRaw = for_every(myGateBottom, myInBottom, myVolExcess, myPosInRange, (_gb, _ib, _ve, _p) => (_gb && _ib) ? -_ve * (1 - _p) : 0.0);
const myOscRaw = add(myOscTopRaw, myOscBottomRaw);

const myOsc = ema(myOscRaw, mySmoothLen);
const mySignalLine = ema(myOsc, mySmoothLen * 2);

// Crossover / crossunder signals
const myOscPrev = shift(myOsc, 1);
const myTopSignal = for_every(myOsc, myOscPrev, (_o, _po) => _o > mySignalThresh && _po <= mySignalThresh);
const myBottomSignal = for_every(myOsc, myOscPrev, (_o, _po) => _o < -mySignalThresh && _po >= -mySignalThresh);

// Bar color approximation (sign based, not a true gradient)
const myOscColor = for_every(myOsc, _o => _o > 0 ? myBearColor : (_o < 0 ? myBullColor : 'gray'));

paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'line' });
paint(horizontal_line(mySignalThresh), { name: 'Top Signal Level', color: myBearColor, style: 'dotted' });
paint(horizontal_line(-mySignalThresh), { name: 'Bottom Signal Level', color: myBullColor, style: 'dotted' });

paint(myOsc, { name: 'VIO', style: 'column', color: myOscColor });
paint(mySignalLine, { name: 'Signal', style: 'line', color: 'gray', thickness: 1 });

const myTopSignalMarks = for_every(myTopSignal, myOsc, (_s, _o) => _s ? _o : null);
const myBottomSignalMarks = for_every(myBottomSignal, myOsc, (_s, _o) => _s ? _o : null);

const myTopLinePainted = paint(myTopSignalMarks, { name: 'ShortSignal', style: 'labels_above', color: myBearColor });
const myBottomLinePainted = paint(myBottomSignalMarks, { name: 'LongSignal', style: 'labels_below', color: myBullColor });

register_signal(myTopSignal, 'VIO Short Signal');
register_signal(myBottomSignal, 'VIO Long Signal');

// Info panel overlay (static snapshot of latest values)
const myLastOsc = myOsc[myOsc.length - 1];
const myLastVolRatio = myVolRatio[myVolRatio.length - 1];
const myLastPosInRange = myPosInRange[myPosInRange.length - 1];
const myLastGateTop = myGateTop[myGateTop.length - 1];
const myLastGateBottom = myGateBottom[myGateBottom.length - 1];
const myZoneText = myLastGateTop ? 'Top Watch' : (myLastGateBottom ? 'Bottom Watch' : '-');

paint_overlay('VIOInfoPanel', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'VIO', color: 'white' }, { text: String(myLastOsc != null ? myLastOsc.toFixed(3) : '-'), color: 'white' }] },
		{ cells: [{ text: 'Vol Ratio', color: 'white' }, { text: String(myLastVolRatio != null ? myLastVolRatio.toFixed(2) + 'x' : '-'), color: 'white' }] },
		{ cells: [{ text: 'Range Pos', color: 'white' }, { text: String(myLastPosInRange != null ? Math.round(myLastPosInRange * 100) + '%' : '-'), color: 'white' }] },
		{ cells: [{ text: 'Zone', color: 'white' }, { text: myZoneText, color: 'white' }] }
	]
});