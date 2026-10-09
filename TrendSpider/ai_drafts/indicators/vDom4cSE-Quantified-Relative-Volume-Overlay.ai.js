describe_indicator('Quantified Relative Volume Overlay', 'price');

// NOTE: TradingView's ta.relativeVolume(10, "1D", true) computes an
// intraday-accumulated volume comparison against the average volume
// accumulated up to the same time of day, over the past 10 daily
// sessions. The Custom JS API has no equivalent intraday accumulation
// primitive, so this indicator approximates RVol as:
// (current daily volume) / (SMA of the previous 10 daily volumes).
// This is a reasonable proxy but will not produce identical values or
// identical signal bars intraday, only on daily (or higher) charts
// where volume accumulation nuance does not apply.

const myVolumeRatio = input.number('Volume Ratio', 3.0, { min: 0.1, max: 50 });

const myShowBarcolor = input.boolean('Color Signal Candles', true);
const myLongColor = input.color('Long Signal Color', '#00FF00');
const myShortColor = input.color('Short Signal Color', '#FF0000');

const myShowArrows = input.boolean('Show Arrows', false);
const myLongArrowColor = input.color('Long Arrow Color', '#00FF00');
const myShortArrowColor = input.color('Short Arrow Color', '#FF0000');

const myShowLong = input.boolean('Show Long Signals', true);
const myShowShort = input.boolean('Show Short Signals', false);

// Fetch daily data to build the Relative Volume proxy
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, 'Error fetching daily data: ' + myDailyData.error);

// Past volume average = SMA(10) of daily volume, shifted back 1 bar
// so "past" never includes the current day's volume
const myDailyPastVolAvg = shift(sma(myDailyData.volume, 10), 1);

const myDailyRvol = for_every(myDailyData.volume, myDailyPastVolAvg, (_myVol, _myPastAvg) => {
	if (_myPastAvg === null || _myPastAvg === undefined || _myPastAvg <= 0) {
		return null;
	}
	return _myVol / _myPastAvg;
});

// Land the daily Rvol values onto the current chart's resolution
const myRvolLanded = land_points_onto_series(myDailyData.time, myDailyRvol, time, 'le');
const myRvol = interpolate_sparse_series(myRvolLanded, 'constant');

const myIsHighRvol = for_every(myRvol, _myR => _myR !== null && _myR > myVolumeRatio);

const myIsLongCandle = for_every(close, open, (_myClose, _myOpen) => _myClose > _myOpen);
const myIsShortCandle = for_every(close, open, (_myClose, _myOpen) => _myClose < _myOpen);

// Excluded markets: forex and CFD assets. "cfd" asset type is not
// available in the Custom JS API asset type list, so only "fx" is
// excluded here.
const myIsExcludedMarket = current.assetType === 'fx';

const myIsLongSignal = for_every(myIsHighRvol, myIsLongCandle, (_myHighRvol, _myLongCandle) => _myHighRvol && _myLongCandle && !myIsExcludedMarket);
const myIsShortSignal = for_every(myIsHighRvol, myIsShortCandle, (_myHighRvol, _myShortCandle) => _myHighRvol && _myShortCandle && !myIsExcludedMarket);

// Bar coloring
const myBarColors = for_every(myIsLongSignal, myIsShortSignal, (_myLong, _myShort) => {
	if (myShowLong && myShowBarcolor && _myLong) {
		return myLongColor;
	}
	if (myShowShort && myShowBarcolor && _myShort) {
		return myShortColor;
	}
	return null;
});
color_candles(myBarColors);

// Arrow markers (below/above bar)
const myLongArrowSeries = for_every(myIsLongSignal, low, (_myLong, _myLow) => (myShowLong && myShowArrows && _myLong) ? _myLow : null);
const myShortArrowSeries = for_every(myIsShortSignal, high, (_myShort, _myHigh) => (myShowShort && myShowArrows && _myShort) ? _myHigh : null);

paint(myLongArrowSeries, { name: 'LongSignal', style: 'labels_below', color: myLongArrowColor });
paint(myShortArrowSeries, { name: 'ShortSignal', style: 'labels_above', color: myShortArrowColor });

// Signals for scanners, alerts and strategies
register_signal(myIsLongSignal, 'QRVOL Long Signal');
register_signal(myIsShortSignal, 'QRVOL Short Signal');