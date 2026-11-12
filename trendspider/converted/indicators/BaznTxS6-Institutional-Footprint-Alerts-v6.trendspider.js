/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Institutional Footprint Alerts v6
 * Author       : asaurabh053
 * Source URL   : https://www.tradingview.com/script/BaznTxS6-Institutional-Footprint-Alerts-v6
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Institutional Footprint Alerts v6_TV
 *
 * The Pine original, in words: INST BUY / INST SELL on volume > 2.5x its SMA(20) with a bullish / bearish candle;
 *   bullish FVG when low > high 2 bars ago after an up bar, bearish the mirror image.
 *
 * Deviations from the original: fixed from the AI draft: it read high/low two bars AHEAD (shift -2, look-ahead); now
 *   two bars back as in the Pine.
 * Not carried over: alert() messages — use the four signals.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Institutional Footprint Alerts v6_TV', 'price');

// --- Inputs ---
const myVolMultiplier = input.number('Volume Spike Multiplier', 2.5, { min: 1.0 });
const myVolLength = input.number('Volume Moving Average Length', 20, { min: 1, max: 500 });
const myShowShapes = input.boolean('Plot Visual Shapes on Chart', true);

// --- Calculations ---
const myAvgVolume = sma(volume, myVolLength);
const myIsHugeVol = for_every(volume, myAvgVolume, (_v, _av) => _av !== null && _v > (_av * myVolMultiplier));

const myIsBullish = for_every(close, open, (_c, _o) => _c > _o);
const myIsBearish = for_every(close, open, (_c, _o) => _c < _o);

const myInstBuying = for_every(myIsHugeVol, myIsBullish, (_h, _b) => _h && _b);
const myInstSelling = for_every(myIsHugeVol, myIsBearish, (_h, _b) => _h && _b);

// Fair Value Gap detection (3-candle structural shift)
// Shift the series backwards by 1 and 2 candles to access
// previous values (shift with negative offset moves to the past)
const myHigh2 = shift(high, 2);
const myLow2 = shift(low, 2);
const myClose1 = shift(close, 1);
const myOpen1 = shift(open, 1);

const myBullishFVG = for_every(low, myHigh2, myClose1, myOpen1, (_l, _h2, _c1, _o1) => _h2 !== null && (_l > _h2) && (_c1 > _o1));
const myBearishFVG = for_every(high, myLow2, myClose1, myOpen1, (_h, _l2, _c1, _o1) => _l2 !== null && (_h < _l2) && (_c1 < _o1));

// --- Visual Layout Elements ---
const myInstBuyShape = for_every(myInstBuying, low, (_cond, _l) => (myShowShapes && _cond) ? 'INST BUY' : null);
const myInstSellShape = for_every(myInstSelling, high, (_cond, _h) => (myShowShapes && _cond) ? 'INST SELL' : null);
const myBullishFVGShape = for_every(myBullishFVG, low, (_cond, _l) => (myShowShapes && _cond) ? constants.icons.square : null);
const myBearishFVGShape = for_every(myBearishFVG, high, (_cond, _h) => (myShowShapes && _cond) ? constants.icons.square : null);

paint(myInstBuyShape, { name: 'InstBuyVolume', style: 'labels_below', color: 'green' });
paint(myInstSellShape, { name: 'InstSellVolume', style: 'labels_above', color: 'red' });
paint(myBullishFVGShape, { name: 'BullishFVG', style: 'labels_below', color: 'lime' });
paint(myBearishFVGShape, { name: 'BearishFVG', style: 'labels_above', color: 'maroon' });

// --- Signals for scanners, alerts, strategies ---
register_signal(myInstBuying, 'Institutional Buy Volume');
register_signal(myInstSelling, 'Institutional Sell Volume');
register_signal(myBullishFVG, 'Bullish Fair Value Gap');
register_signal(myBearishFVG, 'Bearish Fair Value Gap');
