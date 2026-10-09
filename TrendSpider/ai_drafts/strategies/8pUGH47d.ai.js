describe_indicator('Spike EA Signals', 'price');

// NOTE: This is a signal indicator reproducing the Pine Script's spike
// detection and entry logic. TrendSpider Custom JS indicators cannot
// place actual broker orders or manage strategy position state (no
// equivalent of strategy.entry/exit, stop/limit orders, or
// pyramiding). The exit logic (fixed stop/take distances from
// position average price) cannot be reproduced here. Use the
// Strategy Tester module separately if you need backtesting of
// entries/exits; this script only reproduces the signal generation.

const myTab = input.tab('Spike Settings');

const mySpikeThreshold = myTab.number('Spike Threshold', 0.5, { min: 0.0, max: 1000, step: 0.1 });
const mySpikeBar = myTab.number('Spike Bar', 1, { min: 0, max: 50 });
const myPriceUnit = myTab.number('Price Unit for Threshold', 1.0, { min: 0.00001, max: 1000, step: 0.1 });

const myShowBg = myTab.boolean('Show Signal Background', true);
const myShowSignals = myTab.boolean('Show Additional Signals', false);

// Shift the spike bar series back by "mySpikeBar" candles,
// equivalent to Pine's high[spikeBar], low[spikeBar], etc.
const mySpikeHigh = shift(high, mySpikeBar);
const mySpikeLow = shift(low, mySpikeBar);
const mySpikeOpen = shift(open, mySpikeBar);
const mySpikeClose = shift(close, mySpikeBar);

const mySpikeRange = sub(mySpikeHigh, mySpikeLow);
const myThreshold = mySpikeThreshold * myPriceUnit;

const myIsSpike = for_every(mySpikeRange, _r => _r >= myThreshold);

const myBuySignal = for_every(myIsSpike, mySpikeClose, mySpikeOpen, (_s, _c, _o) => Boolean(_s) && _c > _o);
const mySellSignal = for_every(myIsSpike, mySpikeClose, mySpikeOpen, (_s, _c, _o) => Boolean(_s) && _c <= _o);

// Background approximation: color candles blue/red on signal bars.
// Pine's bgcolor paints the chart background (not candles); Custom
// JS API has no background-paint function, so candle coloring is
// used as the closest visual proxy, only when "Show Signal
// Background" is enabled.
const myCandleColors = for_every(myBuySignal, mySellSignal, (_b, _s) => {
	if (!myShowBg) return null;
	if (_b) return '#0078ff';
	if (_s) return '#ff465a';
	return null;
});
color_candles(myCandleColors);

// Optional triangle markers, mirroring plotshape with showSignals
const myBuyMarks = for_every(myBuySignal, _b => (myShowSignals && _b) ? constants.icons.triangle_up : null);
const mySellMarks = for_every(mySellSignal, _s => (myShowSignals && _s) ? constants.icons.triangle_down : null);

paint(myBuyMarks, { style: 'labels_below', color: '#00ffaa', name: 'BuySignal' });
paint(mySellMarks, { style: 'labels_above', color: '#ff5a78', name: 'SellSignal' });

// Threshold line reference (hidden by default behavior, data only)
paint(series_of(myThreshold), { style: 'line', color: 'gray', name: 'SpikeThreshold' });

register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');