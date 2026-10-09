describe_indicator('News Event Price Bands', 'price');

// Lets the user pick which macro event preset defines the band width
const myEventPreset = input.select('Event preset', 'Core CPI (High Probability)', [
	'Core CPI (High Probability)',
	'NFP (Medium Probability)'
]);

const myLineWidth = input.number('Line width', 1, { min: 1, max: 4 });
const myLabelOffset = input.number('Label offset bars', 3, { min: 0, max: 100 });

// Spread (points) applied symmetrically around the latest close
const mySpreadPoints = myEventPreset === 'Core CPI (High Probability)' ? 40 : 30;

// Pine's barstate.islast logic only updates the lines/labels on the most
// recent bar, using the *current* close. Since TrendSpider series are
// computed for every candle, we reproduce the "always track latest close"
// behavior by using the last available close for the whole band, which
// is the equivalent of what the Pine script visually shows at any moment.
const myLastClose = close[close.length - 1];
const myUpperPrice = myLastClose + mySpreadPoints;
const myLowerPrice = myLastClose - mySpreadPoints;

const myUpperSeries = horizontal_line(myUpperPrice);
const myLowerSeries = horizontal_line(myLowerPrice);

const myUpperLinePainted = paint(myUpperSeries, { name: 'UpperBand', color: '#4CAF50', thickness: myLineWidth, style: 'dotted' });
const myLowerLinePainted = paint(myLowerSeries, { name: 'LowerBand', color: '#F44336', thickness: myLineWidth, style: 'dotted' });

// Labels placed near the end of the chart (offset is informational only,
// since TrendSpider does not support placing labels beyond the last candle)
const myLabelIndex = Math.min(close.length - 1, close.length - 1 + myLabelOffset);
paint_label_at_line(myUpperLinePainted, close.length - 1, 'Buy stops here', { color: '#4CAF50' });
paint_label_at_line(myLowerLinePainted, close.length - 1, 'Sell stops here', { color: '#F44336' });

// Signals for scanning/alerts/backtesting: price touching either band
const myUpperTouchSignal = for_every(high, myUpperSeries, (_h, _u) => _h >= _u);
const myLowerTouchSignal = for_every(low, myLowerSeries, (_l, _lo) => _l <= _lo);

register_signal(myUpperTouchSignal, 'Price Touched Upper Band');
register_signal(myLowerTouchSignal, 'Price Touched Lower Band');