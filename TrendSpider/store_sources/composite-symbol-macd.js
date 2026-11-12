<code x-ref="code" class="hljs" data-clipboard-text>// This indicator code was potentially generated using AI. It was not checked by Quality Assurance
// and did not pass any quality assurance processes used at TrendSpider
// As a result, I can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only.

//This indicator allows you to create a MACD based on a composite symbol.  For example, if you are viewing ticker symbol AAPL on your price chart, and the indicator is using XLK, then you will get the MACD of the composite symbol =AAPL/XLK.  

// Declare the indicator with a user-friendly name and type
describe_indicator('Composite Symbol MACD', 'lower', { decimals: 4 });

// Input parameter for the comparison symbol
const comparisonSymbol = input.symbol('Comparison Symbol', 'XLK');

// Fetch the historical data for the selected comparison symbol
const compositeHistory = await request.history(`=${current.ticker}/${comparisonSymbol}`, current.resolution, { land_onto_current_candles: true });
const compositeClose = compositeHistory.close;

// Input parameters for MACD calculation
const shortLength = input.number('Short Length', 12);
const longLength = input.number('Long Length', 26);
const signalLength = input.number('Signal Length', 9);

// Calculate MACD
const short = ema(compositeClose, shortLength);
const long = ema(compositeClose, longLength);
const macd = sub(short, long);
const signal = sma(macd, signalLength);
const histogram = sub(macd, signal);

// Paint histogram
paint(histogram, { title: 'MACD Histogram', style: 'histogram', color: histogram.map(value => value > 0 ? 'green' : 'red') });

// Paint MACD line
paint(macd, { name: 'MACD', color: 'blue', thickness: 2 });

// Paint Signal line
paint(signal, { name: 'Signal', color: 'purple', thickness: 2 });</code>