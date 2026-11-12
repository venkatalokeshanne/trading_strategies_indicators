<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Relative Performance Candle Coloring');

// Allow user to select performance type
const performanceType = input.select('Performance Type', 'yearly', ['yearly', 'quarterly', 'techrank']);

// Input for custom color thresholds
const strongThreshold = input.number('Strong Performance Threshold', 85, { min: 0, max: 100 });
const goodThreshold = input.number('Good Performance Threshold', 70, { min: 0, max: 100 });
const weakThreshold = input.number('Weak Performance Threshold', 30, { min: 0, max: 100 });

// Input for custom colors
const strongColor = input.color('Strong Performance Color', 'green');
const goodColor = input.color('Good Performance Color', 'orange');
const weakColor = input.color('Weak Performance Color', 'red');
const neutralColor = input.color('Neutral Performance Color', 'gray');

// Fetch relative performance data
const relativePerformanceData = await request.relative_performance(current.ticker, performanceType, 'spx500');
assert(!relativePerformanceData.error, "Error fetching relative performance data: " + relativePerformanceData.error);

// Extract values from the relative performance data
const myRelativePerformance = relativePerformanceData.map(_dataPoint => _dataPoint[1]);

// Interpolate the sparse relative performance data onto our current time series
const myInterpolatedRelativePerformance = interpolate_sparse_series(
    land_points_onto_series(
        relativePerformanceData.map(_dataPoint => _dataPoint[0]),
        myRelativePerformance,
        time,
        'le'
    ),
    'constant'
);

// Define color based on relative performance
const myColors = for_every(myInterpolatedRelativePerformance, _rp => {
    if (_rp > strongThreshold) return strongColor;
    if (_rp > goodThreshold) return goodColor;
    if (_rp < weakThreshold) return weakColor;
    return neutralColor;
});

// Color the candles
color_candles(myColors);

// Register signals for scanner
if (performanceType === 'techrank') {
    register_signal(for_every(myInterpolatedRelativePerformance, _rp => _rp > strongThreshold), "Strong Technical Performance");
    register_signal(for_every(myInterpolatedRelativePerformance, _rp => _rp > goodThreshold && _rp <= strongThreshold), "Good Technical Performance");
    register_signal(for_every(myInterpolatedRelativePerformance, _rp => _rp < weakThreshold), "Weak Technical Performance");
} else {
    register_signal(for_every(myInterpolatedRelativePerformance, _rp => _rp > strongThreshold), "Strong Outperformer");
    register_signal(for_every(myInterpolatedRelativePerformance, _rp => _rp > goodThreshold && _rp <= strongThreshold), "Outperformer");
    register_signal(for_every(myInterpolatedRelativePerformance, _rp => _rp < weakThreshold), "Underperformer");
}</code>