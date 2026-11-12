<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Relative Performance with MA', 'lower');

// Input parameters
const performanceType = input.select('Performance Type', 'yearly', ['yearly', 'quarterly', 'techrank']);
const universe = input.select('Universe', 'spx500', ['spx500', 'russell2000', 'same_sector', 'same_mktcap', 'same_sector_mktcap']);
const maType = input.select('MA Type', 'sma', constants.ma_types);
const maPeriod = input.number('MA Period', 20, { min: 1 });
const maColor = input.color('MA Color', 'red');

// Fetch relative performance data
const myPerfData = await request.relative_performance(current.ticker, performanceType, universe);
assert(!myPerfData.error, "Error fetching relative performance data: " + myPerfData.error);

// Extract timestamps and values
const myTimestamps = myPerfData.map(d => d[0]);
const myValues = myPerfData.map(d => d[1]);

// Interpolate the sparse data onto our chart's time series
const myRelativePerformance = interpolate_sparse_series(
    land_points_onto_series(myTimestamps, myValues, time, 'le'),
    'constant'
);

// Calculate the moving average
const myMaFunction = indicators[maType];
assert(typeof myMaFunction === 'function', `Invalid MA type: ${maType}`);
const myMovingAverage = myMaFunction(myRelativePerformance, maPeriod);

// Paint the relative performance line
const myPerfLine = paint(myRelativePerformance, { color: 'white', name: 'Relative Performance' });

// Paint the moving average line
paint(myMovingAverage, { color: maColor, name: `${maType.toUpperCase()}(${maPeriod})` });

// Paint horizontal lines
paint(horizontal_line(80), { color: 'grey', name: '80 Level' });
paint(horizontal_line(50), { color: 'grey', style: 'dotted', name: '50 Level' });
paint(horizontal_line(15), { color: 'grey', name: '15 Level' });

// Shade areas
const myAbove80 = for_every(myRelativePerformance, rp => rp > 80 ? 80 : null);
const myBelow15 = for_every(myRelativePerformance, rp => rp < 15 ? 15 : null);
fill(myPerfLine, paint(myAbove80, { hidden: true }), 'green', 0.3, 'Above 80');
fill(paint(myBelow15, { hidden: true }), myPerfLine, 'red', 0.3, 'Below 15');</code>