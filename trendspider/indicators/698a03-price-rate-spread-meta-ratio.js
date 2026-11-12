<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Price/Rate-Spread Meta-Ratio', 'lower');

// Allow the user to customize the three indexes
const symbol1 = input.symbol('Equity Index', '$SPX');
const symbol2 = input.symbol('Rate Index 1 (Numerator)', '$TYX');
const symbol3 = input.symbol('Rate Index 2 (Denominator)', '$FVX');

// Fetch data for the three customizable symbols
const data1 = await request.history(symbol1, current.resolution);
assert(!data1.error, 'Error fetching ' + symbol1 + ' data: ' + data1.error);

const data2 = await request.history(symbol2, current.resolution);
assert(!data2.error, 'Error fetching ' + symbol2 + ' data: ' + data2.error);

const data3 = await request.history(symbol3, current.resolution);
assert(!data3.error, 'Error fetching ' + symbol3 + ' data: ' + data3.error);

// Land all the data points onto the current chart's timeline
const landed1 = land_points_onto_series(data1.time, data1.close, time, 'ge');
const landed2 = land_points_onto_series(data2.time, data2.close, time, 'ge');
const landed3 = land_points_onto_series(data3.time, data3.close, time, 'ge');

// Interpolate to fill gaps
const interpolated1 = interpolate_sparse_series(landed1, 'constant');
const interpolated2 = interpolate_sparse_series(landed2, 'constant');
const interpolated3 = interpolate_sparse_series(landed3, 'constant');

// Calculate the meta-ratio: Index1 ÷ (Index2 / Index3)
const yieldRatio = div(interpolated2, interpolated3);
const myCrashRisk = div(interpolated1, yieldRatio);

// Calculate RSI on the Market Crash Risk indicator
const rsiLength = input.number('RSI Length', 14, { min: 1, max: 300 });
const myRsi = rsi(myCrashRisk, rsiLength);

// Input parameters for horizontal levels
const overboughtLevel = input.number('Overbought Level', 70, { min: 1, max: 99 });
const oversoldLevel = input.number('Oversold Level', 30, { min: 1, max: 99 });
const neutralLevel = input.number('Neutral Level', 50, { min: 1, max: 99 });

// Create dynamic colors for the RSI line based on its position
const myRsiColor = for_every(myRsi, (_rsi) => {
  if (_rsi >= overboughtLevel) return 'red';
  if (_rsi <= oversoldLevel) return 'green';
  return 'white';
});

// Create sparse series for overbought and oversold regions
const overboughtRegion = for_every(myRsi, (_rsi) => _rsi >= overboughtLevel ? _rsi : null);
const oversoldRegion = for_every(myRsi, (_rsi) => _rsi <= oversoldLevel ? _rsi : null);

// Paint the RSI line with dynamic colors
const myRsiLine = paint(myRsi, { name: 'RSI', color: myRsiColor });

// Paint horizontal levels in grey
const overboughtLine = paint(horizontal_line(overboughtLevel), { name: 'Overbought', color: 'grey', style: 'dotted' });
const oversoldLine = paint(horizontal_line(oversoldLevel), { name: 'Oversold', color: 'grey', style: 'dotted' });
paint(horizontal_line(neutralLevel), { name: 'Neutral', color: 'grey', style: 'dotted' });

// Fill the overbought region with red
fill(
  paint(overboughtRegion, { style: 'line', hidden: true }),
  overboughtLine,
  'red',
  0.2
);

// Fill the oversold region with green
fill(
  oversoldLine,
  paint(oversoldRegion, { style: 'line', hidden: true }),
  'green',
  0.2
);
</code>