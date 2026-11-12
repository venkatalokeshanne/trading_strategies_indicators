/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : ATH and Near ATH Marker
 * Author       : danimin
 * Source URL   : https://www.tradingview.com/script/cS6HOwZz-ATH-and-Near-ATH-Marker
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : ATH and Near ATH Marker_TV
 *
 * The Pine original, in words: blue X on a new all-time high (of the loaded history), yellow X when the high is
 *   within N % of it.
 *
 * Deviations from the original: none.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('ATH and Near ATH Marker_TV', 'price');

// Inputs matching the Pine script
const myThresholdPct = input.number('Proximity Threshold %', 2.0, { min: 0.1, max: 100, step: 0.1 });
const myShowBlueX = input.boolean('Show Blue X (New ATH)', true);
const myShowYellowX = input.boolean('Show Yellow X (Near ATH)', true);

// Running All-Time-High, computed candle by candle (like Pine's var float ath)
const myAthSeries = for_every(high, (_high, _prevAth, _index) => {
	return Math.max(_prevAth || 0, _high);
});

// The ATH value "before" the current candle update, since Pine checks
// "high > ath" using the value of ath as it was prior to this bar's update
const myPrevAth = shift(myAthSeries, 1);

// New ATH condition: high breaks above the prior ATH, and not the first bar
const myIsNewAth = for_every(high, myPrevAth, (_high, _prevAth, _prev, _index) => {
	return _high > (_prevAth || 0) && _index > 0;
});

// Near ATH threshold level, based on prior ATH
const myNearThreshold = mult(myPrevAth, (1 - myThresholdPct / 100));

// Near ATH condition: high is within threshold of prior ATH, not a new ATH, and ATH exists
const myIsNearAth = for_every(high, myNearThreshold, myIsNewAth, myPrevAth, (_high, _nearThreshold, _isNewAth, _prevAth) => {
	return _nearThreshold !== null && _high >= _nearThreshold && !_isNewAth && (_prevAth || 0) > 0;
});

// Build marker series for plotting (null when condition is false)
const myBlueXMarkers = for_every(myIsNewAth, high, (_isNewAth, _high) => {
	return (myShowBlueX && _isNewAth) ? 'X' : null;
});

const myYellowXMarkers = for_every(myIsNearAth, high, (_isNearAth, _high) => {
	return (myShowYellowX && _isNearAth) ? 'X' : null;
});

paint(myBlueXMarkers, { name: 'NewATH', style: 'labels_above', color: 'blue' });
paint(myYellowXMarkers, { name: 'NearATH', style: 'labels_above', color: 'yellow' });

// Signals for scanners, alerts and strategies
register_signal(myIsNewAth, 'New ATH');
register_signal(myIsNearAth, 'Near ATH');
