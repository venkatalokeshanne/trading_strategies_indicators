<code x-ref="code" class="hljs" data-clipboard-text>// This indicator code was generated using AI. It was not checked by Quality Assurance
// and did not pass any quality assurance processes that we normally would use at TrendSpider
// As a result, we can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only

// Describe the indicator
describe_indicator('RSI with SMA', 'lower');

// Input parameters
const oversold = input('Oversold', 30, { min: 20, max: 100 });
const overbought = input('Overbought', 70, { min: 20, max: 100 });
const mid = input('Mid', 50, { min: 20, max: 100 });
const rsiLength = input('RSI Length', 14, { min: 1, max: 100 });
const smaLength = input('SMA Length', 8, { min: 1, max: 100 });

// Calculate RSI
const rsiValues = rsi(close, rsiLength);

// Calculate SMA of RSI
const smaValues = sma(rsiValues, smaLength);

// Paint horizontal lines and fill the area
paint(horizontal_line(mid), 'Mid', 'gray');
fill(
    paint(horizontal_line(overbought), 'Overbought', 'gray'),
    paint(horizontal_line(oversold), 'Oversold', 'gray'),
    '#cfe2f3', 0.2
);

// Paint RSI and SMA
paint(rsiValues, 'RSI', 'black');
paint(smaValues, 'RSI SMA', 'blue');
</code>