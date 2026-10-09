describe_indicator('200MA Uptrend Screener', 'lower');

// Lookback period (in bars) to compare the 200 SMA against
const myLookback = input.number('Lookback Days', 20, { min: 1, max: 500 });

// 200-period SMA, same as ta.sma(close, 200) in Pine
const my200MA = sma(close, 200);

// Compare current 200MA to its value "lookback" bars ago
const myMA200Up = for_every(my200MA, shift(my200MA, myLookback), (_cur, _prev) => _cur > _prev);

// Scanner output: 1 if uptrend, 0 otherwise
const myScanner = for_every(myMA200Up, _up => _up ? 1 : 0);

paint(myScanner, { name: 'Scanner', color: '#2E86DE', style: 'line', thickness: 2 });

// Expose as a usable signal in scanners/alerts/backtests
register_signal(myMA200Up, 'MA200 Uptrend');