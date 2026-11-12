/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Reversal Strategy - MA + ATR Counter
 * Author       : nencio69
 * Source URL   : https://www.tradingview.com/script/DtoxsMQk
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Reversal Strategy - MA + ATR Counter_TV
 *
 * The Pine original, in words: MA(120) with an ATR(14) band; counts bars since price last touched the band and
 *   labels FAIR when the count reaches 100.
 *
 * Deviations from the original: input titles shortened (Italian kept).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Reversal Strategy - MA + ATR Counter_TV', 'price');

// Inputs grouped like the original Pine script groups
const maGroup = input.tab('Media Mobile');
const myMaType = maGroup.select('Tipo MA', 'EMA', ['EMA', 'SMA', 'WMA', 'RMA', 'VWMA']);
const myMaPeriod = maGroup.number('Periodo MA', 120, { min: 1 });

const myCountGroup = input.tab('Strategia Conteggio');
const myTargetBars = myCountGroup.number('Candele FAIR', 100, { min: 1 });

const myAtrGroup = input.tab('Banda ATR');
const myAtrPeriod = myAtrGroup.number('Periodo ATR', 14, { min: 1 });
// Shortened title to satisfy the platform's input name length limit
const myAtrMult = myAtrGroup.number('Mult ATR (0=off)', 1.0, { min: 0.0 });

// Moving average computation, mapping Pine ta.* functions to TrendSpider equivalents
// RMA in Pine corresponds to wildma (Wilders MA / SMMA) here
function myCalcMA(_source, _length, _type) {
	if (_type === 'EMA') return ema(_source, _length);
	if (_type === 'SMA') return sma(_source, _length);
	if (_type === 'WMA') return wma(_source, _length);
	if (_type === 'RMA') return wildma(_source, _length);
	if (_type === 'VWMA') return vwma(_source, _length);
	return ema(_source, _length);
}

const myMaValue = myCalcMA(close, myMaPeriod, myMaType);
const myAtrValue = atr(high, low, close, myAtrPeriod);
const myUpperBand = add(myMaValue, mult(myAtrValue, myAtrMult));
const myLowerBand = sub(myMaValue, mult(myAtrValue, myAtrMult));

// When atrMult is 0 the bands collapse to the MA itself (Pine shows na, we show null instead)
const myUpperBandToPlot = myAtrMult > 0 ? myUpperBand : series_of(null);
const myLowerBandToPlot = myAtrMult > 0 ? myLowerBand : series_of(null);

const myMaLinePainted = paint(myMaValue, { name: 'Media Mobile', color: 'orange', thickness: 2 });
const myUpperLinePainted = paint(myUpperBandToPlot, { name: 'Banda Superiore ATR', color: 'gray' });
const myLowerLinePainted = paint(myLowerBandToPlot, { name: 'Banda Inferiore ATR', color: 'gray' });

fill(myUpperLinePainted, myLowerLinePainted, 'orange', 0.1);

// touchesZone: candle's low/high range overlaps the ATR band
const myTouchesZone = for_every(low, high, myUpperBand, myLowerBand, (_low, _high, _upper, _lower) => _upper !== null && _lower !== null && (_low <= _upper) && (_high >= _lower));

// barCount: resets to 0 whenever touchesZone is true, otherwise increments
const myBarCount = for_every(myTouchesZone, (_touches, _prev, _index) => {
	if (_index === 0) return _touches ? 0 : 1;
	const myPrevCount = _prev === null || _prev === undefined ? 0 : _prev;
	return _touches ? 0 : myPrevCount + 1;
});

// FAIR trigger: fires exactly when barCount reaches the target
const myFairTrigger = for_every(myBarCount, _count => _count === myTargetBars);

// Label markers painted above the candle high, only where the FAIR trigger fires
const myFairLabelSeries = for_every(myFairTrigger, high, (_trigger, _high) => _trigger ? 'FAIR' : null);
paint(myFairLabelSeries, { name: 'FAIR label', style: 'labels_above', color: 'blue' });

// Signals for use in Scanners, Alerts, Strategy Tester
register_signal(myTouchesZone, 'Touches ATR Zone');
register_signal(myFairTrigger, 'FAIR Signal');
