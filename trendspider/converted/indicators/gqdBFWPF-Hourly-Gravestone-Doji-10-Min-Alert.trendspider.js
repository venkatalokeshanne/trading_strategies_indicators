/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Hourly Gravestone Doji - 10 Min Alert
 * Author       : cman35
 * Source URL   : https://www.tradingview.com/script/gqdBFWPF-Hourly-Gravestone-Doji-10-Min-Alert
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Hourly Gravestone Doji - 10 Min Alert_TV
 *
 * The Pine original, in words: on a 60-minute chart, marks a forming gravestone doji (small body, long upper wick,
 *   tiny lower wick) in the last 10 minutes of the hour.
 *
 * Deviations from the original: only meaningful on the live bar, as in the Pine; 'Gravestone Doji Pattern' signal
 *   added for completed bars.
 * Not carried over: alertcondition — use the signals.
 * ────────────────────────────────────────────────────────────────────────
 */
// This indicator reproduces a Pine Script "Hourly Gravestone Doji - 10 Min
// Alert". Note: Pine's "timenow" is wall-clock real time, which only makes
// sense on the currently forming (last) candle. We approximate this by
// using current.now versus the close time of each hourly candle
// (candle open time + 3600 seconds). This part of the logic is inherently
// a "live chart" concept, so it will only be meaningfully true on the last,
// still-forming candle.
describe_indicator('Hourly Gravestone Doji - 10 Min Alert_TV', 'price');

const myBodyMax = input.number('Max Body Percent of Range', 0.20, { min: 0.01, max: 0.50 });
const myWickRatio = input.number('Upper Wick to Body Ratio', 2.0, { min: 1.0, max: 20 });
const myLowerMax = input.number('Max Lower Wick Percent', 0.10, { min: 0.0, max: 0.50 });

// Only valid on a 60 minute (hourly) chart, matching Pine's
// "timeframe.isminutes and timeframe.multiplier == 60"
const myIsHourly = current.resolution === '60';

const myRange = sub(high, low);
const myBody = for_every(close, open, (_close, _open) => Math.abs(_close - _open));
const myUpperWick = for_every(high, open, close, (_high, _open, _close) => _high - Math.max(_open, _close));
const myLowerWick = for_every(open, close, low, (_open, _close, _low) => Math.min(_open, _close) - _low);

const myBodyPct = for_every(myBody, myRange, (_body, _range) => _range > 0 ? _body / _range : 0.0);
const myLowerPct = for_every(myLowerWick, myRange, (_lowerWick, _range) => _range > 0 ? _lowerWick / _range : 0.0);

const mySmallBody = for_every(myBodyPct, _bodyPct => _bodyPct <= myBodyMax);
const myLargeUpperWick = for_every(myBody, myUpperWick, (_body, _upperWick) => _body > 0 ? _upperWick >= _body * myWickRatio : _upperWick > 0);
const mySmallLowerWick = for_every(myLowerPct, _lowerPct => _lowerPct <= myLowerMax);

const myGravestone = for_every(
	myRange, mySmallBody, myLargeUpperWick, mySmallLowerWick,
	(_range, _smallBody, _largeUpperWick, _smallLowerWick) => myIsHourly && _range > 0 && _smallBody && _largeUpperWick && _smallLowerWick
);

// Approximate "time_close" of an hourly candle as its open time + 3600s.
// "minutesLeft" and "finalTenMinutes" only make sense for the live,
// currently forming candle, since current.now is the real server time.
const myFinalTenMinutes = for_every(time, _time => {
	const myTimeClose = _time + 3600;
	const myMinutesLeft = (myTimeClose - Date.now() / 1000) / 60.0;
	return myMinutesLeft <= 10 && myMinutesLeft > 0;
});

const mySignal = for_every(myGravestone, myFinalTenMinutes, (_grave, _final) => _grave && _final);

const myMarkerSeries = for_every(mySignal, high, (_signal, _high) => _signal ? 'GRAVE' : null);

paint(myMarkerSeries, { style: 'labels_above', color: 'orange', name: 'Gravestone Doji' });

register_signal(mySignal, 'Hourly Gravestone Doji 10 Min Alert');
register_signal(myGravestone, 'Hourly Gravestone Doji Pattern');
