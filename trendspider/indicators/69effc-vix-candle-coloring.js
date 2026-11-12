<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('VIX Candle Coloring');

// Fetch VIX data on the same timeframe as the current chart
const vixData = await request.history('$VIX', current.resolution);
assert(!vixData.error, `Error fetching VIX data: ${vixData.error}`);

// Land VIX close values onto the current chart's time series
const vixLanded = land_points_onto_series(vixData.time, vixData.close, time, 'ge');

// Interpolate to fill gaps (use constant to avoid repainting)
const vixInterpolated = interpolate_sparse_series(vixLanded, 'constant');

// Define candle colors based on VIX level
const candleColors = vixInterpolated.map(vixValue => {
  if (vixValue === null) {
    return null;
  }
  if (vixValue >= 50) {
    return '#FF3B30';
  }
  if (vixValue >= 30) {
    return '#FF6A00';
  }
  if (vixValue >= 25) {
    return '#FFB020';
  }
  if (vixValue >= 20) {
    return '#00C2FF';
  }
  return '#00C853';
});

// Apply colors to chart candles
color_candles(candleColors);
</code>