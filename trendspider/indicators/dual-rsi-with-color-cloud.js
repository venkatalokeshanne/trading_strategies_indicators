<code x-ref="code" class="hljs" data-clipboard-text>// This indicator was generated using AI and did not pass any formal QA process at TrendSpider.
// Use it for informational purposes only.

describe_indicator('Dual RSI with Color Cloud', 'lower');

// Input for RSI periods
const rsiLength14 = input('RSI Length (14)', 14, { min: 1, max: 100 });
const rsiLength50 = input('RSI Length (50)', 50, { min: 1, max: 100 });

// Calculate RSI values
const rsi14 = rsi(close, rsiLength14);
const rsi50 = rsi(close, rsiLength50);

// Paint the 14-period RSI and 50-period RSI
const paintedRsi14 = paint(rsi14, { style: 'line', color: 'blue', name: 'RSI (14)' });
const paintedRsi50 = paint(rsi50, { style: 'line', color: 'black', name: 'RSI (50)' });

// Use color cloud to fill the areas where RSI(14) > RSI(50) or RSI(14) < RSI(50)
color_cloud(rsi14, rsi50, 'green', 'red');
</code>