// This indicator approximates the Pine Script "real time higher
// timeframe candle" concept. TrendSpider Custom JS API has no
// box.new() / drawing primitives, so individual wick/body boxes with
// custom pixel widths cannot be reproduced. Instead this version
// reconstructs the higher timeframe (6h/8h/12h) OHLC values using
// request.history() and paints them as Open/High/Low/Close reference
// lines on the price axis, plus colors the underlying candles
// according to the higher timeframe candle direction. Bullish/Bearish
// signals are also registered so they are usable in Scanners,
// Alerts and the Strategy Tester.
describe_indicator('Velas H6 H8 H12 Real Time Aderaldo', 'price');

const myTimeframeChoice = input.select('Timeframe', '12h', ['6h', '8h', '12h']);
const myShowIndicator = input.boolean('Exibir Indicador', true);

const myResolutionMap = { '6h': '360', '8h': '480', '12h': '720' };
const myResolution = myResolutionMap[myTimeframeChoice];

const myHigherTFData = await request.history(current.ticker, myResolution);
assert(!myHigherTFData.error, 'Error fetching higher timeframe data: ' + myHigherTFData.error);

// Land the higher timeframe open/high/low/close onto the current chart's
// timestamps (constant interpolation keeps this non-repainting/backtestable).
const myOpenLanded = interpolate_sparse_series(
	land_points_onto_series(myHigherTFData.time, myHigherTFData.open, time, 'le'),
	'constant'
);
const myHighLanded = interpolate_sparse_series(
	land_points_onto_series(myHigherTFData.time, myHigherTFData.high, time, 'le'),
	'constant'
);
const myLowLanded = interpolate_sparse_series(
	land_points_onto_series(myHigherTFData.time, myHigherTFData.low, time, 'le'),
	'constant'
);
const myCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myHigherTFData.time, myHigherTFData.close, time, 'le'),
	'constant'
);

const myIsBullish = for_every(myOpenLanded, myCloseLanded, (_myOpen, _myClose) => _myClose >= _myOpen);

// Color the actual chart candles according to the current higher
// timeframe candle direction (proxy for the "live box" coloring).
const myCandleColors = for_every(myIsBullish, _myBull => _myBull ? '#3CB371' : '#FF6347');
color_candles(myCandleColors);

const myWickColor = for_every(myIsBullish, _myBull => _myBull ? '#3CB371' : '#FF6347');

if (!myShowIndicator) {
	// Nothing to paint; still paint constant null lines below with
	// identical names/params, as required by the engine.
}

const myShowFlag = myShowIndicator;

paint(myShowFlag ? myOpenLanded : constants.empty_series, { name: 'Open', color: '#999999', style: 'ladder', thickness: 1 });
paint(myShowFlag ? myHighLanded : constants.empty_series, { name: 'High', color: myWickColor, style: 'ladder', thickness: 1 });
paint(myShowFlag ? myLowLanded : constants.empty_series, { name: 'Low', color: myWickColor, style: 'ladder', thickness: 1 });
paint(myShowFlag ? myCloseLanded : constants.empty_series, { name: 'Close', color: for_every(myIsBullish, _myBull => _myBull ? '#3CB371' : '#FF6347'), style: 'ladder', thickness: 2 });

// Signals for scanning / alerts / strategy tester.
register_signal(myIsBullish, 'Higher Timeframe Candle Bullish');
register_signal(for_every(myIsBullish, _myBull => !_myBull), 'Higher Timeframe Candle Bearish');