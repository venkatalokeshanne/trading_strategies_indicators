describe_indicator('Institutional Footprint Alerts v6', 'price');

// --- Inputs ---
const myVolMultiplier = input.number('Volume Spike Multiplier', 2.5, { min: 1.0 });
const myVolLength = input.number('Volume Moving Average Length', 20, { min: 1, max: 500 });
const myShowShapes = input.boolean('Plot Visual Shapes on Chart', true);

// --- Calculations ---
const myAvgVolume = sma(volume, myVolLength);
const myIsHugeVol = for_every(volume, myAvgVolume, (_v, _av) => _v > (_av * myVolMultiplier));

const myIsBullish = for_every(close, open, (_c, _o) => _c > _o);
const myIsBearish = for_every(close, open, (_c, _o) => _c < _o);

const myInstBuying = for_every(myIsHugeVol, myIsBullish, (_h, _b) => _h && _b);
const myInstSelling = for_every(myIsHugeVol, myIsBearish, (_h, _b) => _h && _b);

// Fair Value Gap detection (3-candle structural shift)
// Shift the series backwards by 1 and 2 candles to access
// previous values (shift with negative offset moves to the past)
const myHigh2 = shift(high, -2);
const myLow2 = shift(low, -2);
const myClose1 = shift(close, -1);
const myOpen1 = shift(open, -1);

const myBullishFVG = for_every(low, myHigh2, myClose1, myOpen1, (_l, _h2, _c1, _o1) => (_l > _h2) && (_c1 > _o1));
const myBearishFVG = for_every(high, myLow2, myClose1, myOpen1, (_h, _l2, _c1, _o1) => (_h < _l2) && (_c1 < _o1));

// --- Visual Layout Elements ---
const myInstBuyShape = for_every(myInstBuying, low, (_cond, _l) => (myShowShapes && _cond) ? _l : null);
const myInstSellShape = for_every(myInstSelling, high, (_cond, _h) => (myShowShapes && _cond) ? _h : null);
const myBullishFVGShape = for_every(myBullishFVG, low, (_cond, _l) => (myShowShapes && _cond) ? _l : null);
const myBearishFVGShape = for_every(myBearishFVG, high, (_cond, _h) => (myShowShapes && _cond) ? _h : null);

paint(myInstBuyShape, { name: 'InstBuyVolume', style: 'labels_below', color: 'green' });
paint(myInstSellShape, { name: 'InstSellVolume', style: 'labels_above', color: 'red' });
paint(myBullishFVGShape, { name: 'BullishFVG', style: 'labels_below', color: 'lime' });
paint(myBearishFVGShape, { name: 'BearishFVG', style: 'labels_above', color: 'maroon' });

// --- Signals for scanners, alerts, strategies ---
register_signal(myInstBuying, 'Institutional Buy Volume');
register_signal(myInstSelling, 'Institutional Sell Volume');
register_signal(myBullishFVG, 'Bullish Fair Value Gap');
register_signal(myBearishFVG, 'Bearish Fair Value Gap');