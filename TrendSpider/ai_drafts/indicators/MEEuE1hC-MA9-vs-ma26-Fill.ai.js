describe_indicator('MA9 vs MA26 Fill', 'price');

// Replicates Pine Script: ma9 = sma(close,9), ma26 = sma(close,26)
// fill color is green when ma9 > ma26, red otherwise (semi-transparent)
const myMA9 = sma(close, 9);
const myMA26 = sma(close, 26);

const myLine1 = paint(myMA9, { name: 'MA9', color: 'blue', thickness: 2 });
const myLine2 = paint(myMA26, { name: 'MA26', color: 'black', thickness: 2 });

// color_cloud fills area between the two lines with different colors
// depending on which one is above, mimicking Pine's conditional fill color
color_cloud(myMA9, myMA26, '#2ca599', '#ee5451', 'MA9AboveMA26', 'MA26AboveMA9', 0.2);

// Signals for scanner/strategy use: bullish when MA9 above MA26, bearish otherwise
const myBullishSignal = for_every(myMA9, myMA26, (_m9, _m26) => _m9 > _m26);
const myBearishSignal = for_every(myMA9, myMA26, (_m9, _m26) => _m9 < _m26);

register_signal(myBullishSignal, 'MA9 Above MA26');
register_signal(myBearishSignal, 'MA9 Below MA26');