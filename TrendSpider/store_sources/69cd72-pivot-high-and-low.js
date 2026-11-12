<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Pivot High and Low');

// Input parameters for pivot detection
const leftBars = input.number('Left Bars', 5, { min: 1, max: 50 });
const rightBars = input.number('Right Bars', 5, { min: 1, max: 50 });

// Calculate pivot highs and pivot lows
// Pivot high: a high point that is higher than leftBars bars before it and rightBars bars after it
const pivotHighs = pivot_high(high, leftBars, rightBars);

// Pivot low: a low point that is lower than leftBars bars before it and rightBars bars after it
const pivotLows = pivot_low(low, leftBars, rightBars);

// Paint the pivot highs with green triangles above the points
paint(pivotHighs, { 
  style: 'labels_above', 
  color: '#2ca599', 
  name: 'Pivot High',
  thickness: 10
});

// Paint the pivot lows with red triangles below the points
paint(pivotLows, { 
  style: 'labels_below', 
  color: '#ee5451', 
  name: 'Pivot Low',
  thickness: 10
});
</code>