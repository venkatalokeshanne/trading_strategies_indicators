// This indicator reproduces a Pine Script strategy that buys at the
// open of every bar and sells at the close of the same bar. Since this
// happens on every single bar, both the "Buy" and "Sell" conditions
// are simply always true for every historical bar. There is no
// persistent position carried between bars (buy and sell occur within
// the same bar), so the signals below fire on every candle.
describe_indicator('Buy At Open Sell At Close Every Bar', 'lower');

// Always true, buy signal fires at the open of every bar
const myBuySignal = series_of(true);

// Always true, sell signal fires at the close of every bar
const mySellSignal = series_of(true);

// Visual reference line, since this is a lower indicator with
// no numeric value of its own, we just show a constant marker
paint(series_of(1), { name: 'Always Active', style: 'line', color: '#4DA3FF' });

// Register signals so this can be used in Scanners, Alerts and
// the Strategy Tester
register_signal(myBuySignal, 'Buy At Open');
register_signal(mySellSignal, 'Sell At Close');