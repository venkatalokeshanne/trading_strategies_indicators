describe_indicator('SMA Sandwich Cluster Strategy', 'price');

// --- Inputs ---
const myLen13 = input.number('Fast SMA Length', 13, { min: 1, max: 500 });
const myLen26 = input.number('Base SMA Length', 26, { min: 1, max: 500 });
const myLen100 = input.number('Slow SMA Length', 100, { min: 1, max: 1000 });
const myLen200 = input.number('Long SMA Length', 200, { min: 1, max: 1000 });
const myClusterThreshold = input.number('13/26 Cluster Threshold (%)', 0.3, { min: 0.01, max: 10, step: 0.05 });

// --- Core SMA calculations (never call indicator functions inside loops) ---
const mySma13 = sma(close, myLen13);
const mySma26 = sma(close, myLen26);
const mySma100 = sma(close, myLen100);
const mySma200 = sma(close, myLen200);

// Spread % between SMA13 and SMA26, relative to SMA13
const myShortSpread = mult(div(for_every(mySma13, mySma26, (_s13, _s26) => Math.abs(_s13 - _s26)), mySma13), 100);
const myIsClustered = for_every(myShortSpread, _spread => _spread <= myClusterThreshold);

// Sandwich arrangement conditions (long/short), including cluster requirement
const myLongCondition = for_every(mySma200, mySma100, close, mySma13, mySma26, myIsClustered,
	(_s200, _s100, _c, _s13, _s26, _clustered) => (_s200 > _s100) && (_s100 > _c) && (_c > _s13) && (_s13 > _s26) && _clustered);
const myShortCondition = for_every(mySma200, mySma100, close, mySma13, mySma26, myIsClustered,
	(_s200, _s100, _c, _s13, _s26, _clustered) => (_s200 < _s100) && (_s100 < _c) && (_c < _s13) && (_s13 < _s26) && _clustered);

// --- Stateful loop to replicate strategy.entry/strategy.close bar-by-bar logic ---
// Position: 0 = flat, 1 = long, -1 = short.
// We detect "edge" entries (condition true now, false on previous bar),
// and exits based on SMA13 gap-away rule.
const myLongEntry = series_of(false);
const myShortEntry = series_of(false);
const myLongExit = series_of(false);
const myShortExit = series_of(false);
let myPosition = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevLongCond = myIndex > 0 ? myLongCondition[myIndex - 1] : false;
	const myPrevShortCond = myIndex > 0 ? myShortCondition[myIndex - 1] : false;
	const myLongEdge = myLongCondition[myIndex] && !myPrevLongCond;
	const myShortEdge = myShortCondition[myIndex] && !myPrevShortCond;

	// Entries
	if (myLongEdge) {
		myLongEntry[myIndex] = true;
		myPosition = 1;
	}
	if (myShortEdge) {
		myShortEntry[myIndex] = true;
		myPosition = -1;
	}

	// Exits based on SMA13 gap rule
	const myLongExitNow = myPosition > 0 && high[myIndex] < mySma13[myIndex];
	const myShortExitNow = myPosition < 0 && low[myIndex] > mySma13[myIndex];

	if (myLongExitNow) {
		myLongExit[myIndex] = true;
		myPosition = 0;
	}
	if (myShortExitNow) {
		myShortExit[myIndex] = true;
		myPosition = 0;
	}
}

// --- Visualization ---
paint(mySma13, { name: 'SMA 13', color: '#00BCD4', thickness: 1 });
paint(mySma26, { name: 'SMA 26', color: '#FF9800', thickness: 1 });
paint(mySma100, { name: 'SMA 100', color: '#FAFAFA', thickness: 2 });
paint(mySma200, { name: 'SMA 200', color: '#EF5350', thickness: 2 });

// Entry labels (approximate Pine's plotshape labelup/labeldown with text).
// Note: these line/series names were renamed (e.g. "Long Entry Marker") so
// they no longer collide with the register_signal() names below, since
// paint() and register_signal() output names must be unique per indicator.
const myLongLabelSeries = for_every(myLongEntry, _flag => _flag ? constants.icons.triangle_up : null);
const myShortLabelSeries = for_every(myShortEntry, _flag => _flag ? constants.icons.triangle_down : null);
paint(myLongLabelSeries, { name: 'Long Entry Marker', style: 'labels_below', color: '#FFEB3B' });
paint(myShortLabelSeries, { name: 'Short Entry Marker', style: 'labels_above', color: '#FFEB3B' });

// Approximation of Pine's bgcolor cluster highlight: colors candles light blue
// when the 13/26 cluster condition is true (candle coloring used as a proxy
// for the chart background shading, since custom scripts cannot paint a
// full-chart translucent background).
const myClusterCandleColors = for_every(myIsClustered, _clustered => _clustered ? 'rgba(33,150,243,0.25)' : null);
color_candles(myClusterCandleColors);

// --- Signals for scanner/alerts/backtests ---
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myLongExit, 'Long Exit');
register_signal(myShortExit, 'Short Exit');
register_signal(myIsClustered, 'SMA13 26 Clustered');