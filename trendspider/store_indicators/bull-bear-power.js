<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Bull Bear Power', 'lower');

const lengthInput = input('Length', 13, {min: 2, max: 50});
const highPrices = high;
const lowPrices = low;
const closePrices = close;

// Calculate Exponential Moving Average (EMA) of the close prices
const closeEMA = ema(closePrices, lengthInput);

// Calculate Bull Power and Bear Power
const bullPower = for_every(highPrices, closeEMA, (high, emaClose) => high - emaClose);
const bearPower = for_every(lowPrices, closeEMA, (low, emaClose) => low - emaClose);

// Calculate BBP by adding Bull Power and Bear Power
const bbp = for_every(bullPower, bearPower, (bull, bear) => bull + bear);

// Paint BBPower using histogram style with dynamic coloring
paint(bbp, "BBPower", for_every(bbp, (value) => value >= 0 ? "green" : "red"), "histogram");





</code>