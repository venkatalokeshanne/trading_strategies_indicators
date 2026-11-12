<code x-ref="code" class="hljs" data-clipboard-text>
describe_indicator('Normalized Range Crossover', 'lower');
 
const twoWeekPeriod = input.number('Trading Days in Period', 10, { min: 1, max: 100 });
const highestHigh = highest(high, twoWeekPeriod);
const lowestLow = lowest(low, twoWeekPeriod);
const range = sub(highestHigh, lowestLow);
 
// Normalize the range against the bar's close price
const normalizedRange = div(range, close);
 
// Convert to percentage for easier interpretation
const normalizedRangePercentage = mult(normalizedRange, 100);
 
// Add SMA of normalizedRangePercentage
const smaPeriod = input.number('SMA Period', 14, { min: 1, max: 100 });
const normalizedRangeSMA = sma(normalizedRangePercentage, smaPeriod);
 
paint(normalizedRangePercentage, { name: 'Normalized Range %', color: 'cyan', style: 'dotted' });
paint(normalizedRangeSMA, { name: 'SMA of Normalized Range %', color: 'magenta' });
</code>