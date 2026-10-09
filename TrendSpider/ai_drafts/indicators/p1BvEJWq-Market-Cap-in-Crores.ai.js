describe_indicator('Market Cap in Crores', 'lower', { decimals: 0 });

// NOTE: the metric name "common_shares_outstanding" does not exist
// in the Fundamentals data set (confirmed by the runtime error).
// We switch to "shares_outstanding", which is the metric name used
// by TrendSpider's Fundamentals Knowledge Base for share count data.
// If this metric is also unavailable for a given ticker, the
// computation will fail and the indicator will show an error
// instead of a value.
const myFundamentalData = await request.fundamental(current.ticker, ['shares_outstanding'], 1);
assert(!myFundamentalData.error, "Error fetching fundamental data: " + myFundamentalData.error);

const myTsoRecords = myFundamentalData.shares_outstanding;
assert(myTsoRecords && myTsoRecords.length > 0, "No shares outstanding data available");

const myTso = myTsoRecords[0].value;

// Raw market cap = shares outstanding * close, converted to Crores (1 Crore = 10,000,000)
const myMarketCap = mult(close, myTso);
const myMcCrores = div(myMarketCap, 10000000);

// This value is meant mostly for the status line / labels, not as a
// visible chart line. We paint a hidden line (so the value is still
// computable/backtestable) and surface a label with the latest value,
// plus a signal for use in scanners/alerts.
const myLinePainted = paint(myMcCrores, { name: 'MarketCapCrores', style: 'line', hidden: true });
paint_label_at_line(myLinePainted, close.length - 1, 'Mcap (cr)');

// Register the raw value as a signal so it can be used in Scanners,
// Alerts and the Strategy Tester (register_signal requires a truthy/
// falsy signal, so we expose the market cap value itself here, which
// will be treated as "truthy" whenever it's a non-zero number).
register_signal(myMcCrores, "Market Cap (Crores)");