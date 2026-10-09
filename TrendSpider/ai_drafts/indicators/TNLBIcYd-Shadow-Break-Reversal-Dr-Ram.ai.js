describe_indicator('Shadow Break Reversal - Dr-Ram', 'price');

// Bearish shadow break: current high breaks previous high (upper
// shadow rejection), but closes below previous low (strong reversal down)
const myBearishShadowBreak = for_every(high, low, close,
	(_h, _l, _c, _p, _i) => _i > 0 && _h > high[_i - 1] && _c < low[_i - 1]);

// Bullish shadow break: current low breaks previous low (lower
// shadow rejection), but closes above previous high (strong reversal up)
const myBullishShadowBreak = for_every(high, low, close,
	(_h, _l, _c, _p, _i) => _i > 0 && _l < low[_i - 1] && _c > high[_i - 1]);

// Color candles: orange for bearish shadow break, cyan for bullish
const myCandleColors = for_every(myBearishShadowBreak, myBullishShadowBreak,
	(_bear, _bull) => _bear ? '#FF6D00' : (_bull ? '#00E5FF' : null));
color_candles(myCandleColors);

// Arrow markers above/below bars
const myBearishMarks = for_every(myBearishShadowBreak, _bear => _bear ? constants.icons.triangle_down : null);
const myBullishMarks = for_every(myBullishShadowBreak, _bull => _bull ? constants.icons.triangle_up : null);

paint(myBearishMarks, { style: 'labels_above', color: '#FF6D00', name: 'Bearish Shadow Break' });
paint(myBullishMarks, { style: 'labels_below', color: '#00E5FF', name: 'Bullish Shadow Break' });

// Signals for scanners, alerts and strategy testing
// (each signal is only registered once, with a unique name)
register_signal(myBearishShadowBreak, 'Bearish Shadow Break Signal');
register_signal(myBullishShadowBreak, 'Bullish Shadow Break Signal');