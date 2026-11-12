<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('EMA Stacked', 'lower');
//------------------------------------------------------------------------------
// Inputs
//------------------------------------------------------------------------------
const lookback = input.number('Lookback for EMA trend', 20, { min: 1, max: 50 });
// Allow user to customize EMA lengths
const ema1Length = input.number('EMA 1 Length', 8, { min: 1, max: 500 });
const ema2Length = input.number('EMA 2 Length', 21, { min: 1, max: 500 });
const ema3Length = input.number('EMA 3 Length', 34, { min: 1, max: 500 });
const ema4Length = input.number('EMA 4 Length', 55, { min: 1, max: 500 });
const ema5Length = input.number('EMA 5 Length', 89, { min: 1, max: 500 });
//------------------------------------------------------------------------------
// EMAs
//------------------------------------------------------------------------------
const e8 = ema(close, ema1Length);
const e21 = ema(close, ema2Length);
const e34 = ema(close, ema3Length);
const e55 = ema(close, ema4Length);
const e89 = ema(close, ema5Length);
//------------------------------------------------------------------------------
// Build dot value and color series, plus signal series
//------------------------------------------------------------------------------
const dotValues = series_of(0);
const dotColors = series_of(null);

// Signal series for each type
const signalStrongBullish = series_of(false);
const signalBullish = series_of(false);
const signalStrongBearish = series_of(false);
const signalBearish = series_of(false);
const signalNeutral = series_of(false);

for (let i = lookback; i < close.length; i++) {
  // Check if EMAs are positively stacked: e8 > e21 > e34 > e55 > e89
  const positivelyStacked = e8[i] > e21[i] && e21[i] > e34[i] && e34[i] > e55[i] && e55[i] > e89[i];
 
  // Check if EMAs are negatively stacked: e8 < e21 < e34 < e55 < e89
  const negativelyStacked = e8[i] < e21[i] && e21[i] < e34[i] && e34[i] < e55[i] && e55[i] < e89[i];

  // Check if each EMA is higher/lower than lookback bars ago
  const e8Rising = e8[i] > e8[i - lookback];
  const e21Rising = e21[i] > e21[i - lookback];
  const e34Rising = e34[i] > e34[i - lookback];
  const e55Rising = e55[i] > e55[i - lookback];
  const e89Rising = e89[i] > e89[i - lookback];

  const e8Falling = e8[i] < e8[i - lookback];
  const e21Falling = e21[i] < e21[i - lookback];
  const e34Falling = e34[i] < e34[i - lookback];
  const e55Falling = e55[i] < e55[i - lookback];
  const e89Falling = e89[i] < e89[i - lookback];
  
  // All EMAs rising or falling
  const allRising = e8Rising && e21Rising && e34Rising && e55Rising && e89Rising;
  const allFalling = e8Falling && e21Falling && e34Falling && e55Falling && e89Falling;
 
  if (positivelyStacked) {
    if (allRising) {
      // Dark Green: Positively stacked and all EMAs rising
      dotColors[i] = '#16a34a';
      signalStrongBullish[i] = true;
    } else {
      // Light Green: Positively stacked but at least one EMA not rising
      dotColors[i] = '#86efac';
      signalBullish[i] = true;
    }
  } else if (negativelyStacked) {
    if (allFalling) {
      // Dark Red: Negatively stacked and all EMAs falling
      dotColors[i] = '#dc2626';
      signalStrongBearish[i] = true;
    } else {
      // Light Red: Negatively stacked but at least one EMA not falling
      dotColors[i] = '#fca5a5';
      signalBearish[i] = true;
    }
  } else {
    // Gray: EMAs are not stacked
    dotColors[i] = '#6b7280';
    signalNeutral[i] = true;
  }
}
//------------------------------------------------------------------------------
// Paint
//------------------------------------------------------------------------------
paint(dotValues, {
  name: 'EMA Signal',
  color: dotColors,
  style: 'dotted',
  thickness: 4
});

//------------------------------------------------------------------------------
// Register signals for each type
//------------------------------------------------------------------------------
register_signal(signalStrongBullish, 'Strong Bullish (All EMAs Rising)');
register_signal(signalBullish, 'Bullish (Stacked Positive)');
register_signal(signalStrongBearish, 'Strong Bearish (All EMAs Falling)');
register_signal(signalBearish, 'Bearish (Stacked Negative)');
register_signal(signalNeutral, 'Neutral (Not Stacked)');</code>