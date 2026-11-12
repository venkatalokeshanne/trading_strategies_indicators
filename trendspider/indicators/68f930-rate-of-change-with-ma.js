<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Rate of Change with MA', 'lower', { shortname: 'RoC with MA'});
// Input parameters
const rocLength = input.number('ROC Length', 14, { min: 1 });
const maLength = input.number('MA Length', 14, { min: 1 });
// Not all MAs support the (price, length) parameters. We remove these.
const priceLengthMAs = constants.ma_types.filter(item => !['kama', 'alma', 'twap'].includes(item));
const maType = input.select('MA Type', 'sma', priceLengthMAs);
// Calculate Rate of Change
const myRoc = roc(close, rocLength);
// Calculate Moving Average of ROC
const computeMA = indicators[maType];
const myRocMA = computeMA(myRoc, maLength);
// Paint the indicators
paint(myRoc, { name: 'ROC', color: 'green' });
paint(myRocMA, { name: 'ROC MA', color: 'red' });
// Add a zero line for reference
paint(series_of(0), { name: 'Zero Line', color: 'gray', style: 'dotted' });</code>