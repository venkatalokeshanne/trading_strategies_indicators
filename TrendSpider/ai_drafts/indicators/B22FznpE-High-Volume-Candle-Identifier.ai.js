describe_indicator('High Volume Candle Identifier', 'price');

const volGroup = input.group('Volume Settings');
const myVolumeSMALength = volGroup.number('Volume SMA Length', 20, { min: 1, max: 500 });
const myVolumePercentage = volGroup.number('Volume Pct Above SMA', 50, { min: 0, max: 1000 });

const displayGroup = input.group('Display Options');
const myUseBackground = displayGroup.boolean('Use Background Highlight', false);
const myShowVolumeSMA = displayGroup.boolean('Show Volume SMA Line', false);
const myShowVolumeThreshold = displayGroup.boolean('Show Volume Threshold Line', false);

// Volume SMA and threshold
const myVolumeSMA = sma(volume, myVolumeSMALength);
const myVolumeThreshold = mult(myVolumeSMA, 1 + myVolumePercentage / 100);

// High volume flag
const myIsHighVolume = for_every(volume, myVolumeThreshold, (_v, _t) => _v >= _t);

// Candle direction
const myIsBullish = for_every(close, open, (_c, _o) => _c > _o);
const myIsBearish = for_every(close, open, (_c, _o) => _c < _o);

// Candle coloring: white for high volume candles, null (default) otherwise
const myCandleColors = for_every(myIsHighVolume, _h => _h ? 'white' : null);
color_candles(myCandleColors);

// Background highlight approximation: faint green fill behind price using fill() with high/low band,
// since bgcolor() has no direct equivalent in this API.
const myBackgroundHigh = for_every(myIsHighVolume, myIsBullish, high, (_h, _b, _hi) => (myUseBackground && _h) ? _hi : null);
const myBackgroundLow = for_every(myIsHighVolume, myIsBullish, low, (_h, _b, _lo) => (myUseBackground && _h) ? _lo : null);

fill(
	paint(myBackgroundHigh, { name: 'BackgroundHigh', hidden: true }),
	paint(myBackgroundLow, { name: 'BackgroundLow', hidden: true }),
	'green',
	0.15
);

// High volume bullish/bearish markers, using triangle shapes
const myBullMarkers = for_every(myIsHighVolume, myIsBullish, (_h, _b) => (_h && _b) ? constants.icons.triangle_up : null);
const myBearMarkers = for_every(myIsHighVolume, myIsBearish, (_h, _b) => (_h && _b) ? constants.icons.triangle_down : null);

paint(myBullMarkers, { style: 'labels_below', color: 'green', name: 'High Volume Bullish' });
paint(myBearMarkers, { style: 'labels_above', color: 'red', name: 'High Volume Bearish' });

// Optional reference lines
paint(myShowVolumeSMA ? myVolumeSMA : constants.empty_series, { color: 'blue', name: 'Volume SMA', forceUsePriceAxis: true });
paint(myShowVolumeThreshold ? myVolumeThreshold : constants.empty_series, { color: 'orange', name: 'Volume Threshold', forceUsePriceAxis: true });

// Signals for scanning / alerts / strategy testing
// Renamed to avoid name collision with the paint() lines above
// (every paint()/register_signal() output must have a unique name)
const mySignalBullish = for_every(myIsHighVolume, myIsBullish, (_h, _b) => _h && _b);
const mySignalBearish = for_every(myIsHighVolume, myIsBearish, (_h, _b) => _h && _b);
register_signal(mySignalBullish, 'High Volume Bullish Signal');
register_signal(mySignalBearish, 'High Volume Bearish Signal');