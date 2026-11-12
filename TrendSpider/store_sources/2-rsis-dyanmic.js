<code x-ref="code" class="hljs" data-clipboard-text>// This indicator dynamically calculates RSIs for SPY and the chart's ticker symbol.
describe_indicator('2 RSIs Dynamic', 'lower');

// Input for the first symbol (default is SPY, but user can change it)
const symbol1 = input.symbol('Symbol1 (Custom)', 'SPY');

// The second RSI always uses the ticker on the chart
const symbol2 = current.ticker;

// Input for RSI length
const rsiLength = input.number('RSI Length', 14, { min: 1, max: 100 });

// Fetch historical data for the first symbol
const data1 = await request.history(symbol1, current.resolution);

// Fetch historical data for the second symbol (chart's ticker)
const data2 = await request.history(symbol2, current.resolution);

// Calculate and paint the RSI for the first symbol (customizable)
const rsi1 = rsi(data1.close, rsiLength);
paint(
    interpolate_sparse_series(land_points_onto_series(data1.time, rsi1, time), "constant"),
    { name: 'RSI1 (Custom)', color: 'red' }
);

// Calculate and paint the RSI for the second symbol (chart's ticker)
const rsi2 = rsi(data2.close, rsiLength);
paint(
    interpolate_sparse_series(land_points_onto_series(data2.time, rsi2, time), "constant"),
    { name: 'RSI2 (Chart Symbol)', color: 'blue' }
);
</code>