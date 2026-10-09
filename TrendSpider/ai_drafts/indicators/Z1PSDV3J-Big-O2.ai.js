describe_indicator('My Script', 'price');

// The Pine source only plots "close", with no other logic,
// so there are no scan/strategy signals to map beyond this line.
const myCloseLine = paint(close, { name: 'Close', color: '#2962FF', thickness: 2 });

// Registering a signal so this indicator can still be referenced
// in Scanners, Alerts and Strategy Tester, even though the original
// Pine script has no actual buy/sell conditions.
register_signal(series_of(true), 'Always True');