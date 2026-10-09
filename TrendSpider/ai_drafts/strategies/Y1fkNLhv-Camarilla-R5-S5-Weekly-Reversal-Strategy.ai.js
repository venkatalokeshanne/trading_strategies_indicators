describe_indicator('Camarilla R5 S5 Extreme Reversal (Weekly)', 'price');

// This indicator reproduces the Pine Script logic using the previous
// completed weekly candle's High/Low/Close to compute Camarilla R4/R5/S4/S5
// levels. The Pine script uses request.security with lookahead_on, which is
// a repainting/forward-looking mode not natively available here. We
// approximate this by landing each weekly value onto the first chart candle
// of the corresponding week (constant interpolation), which gives the same
// values as Pine's lookahead_on for all candles within that week.

const myWeeklyData = await request.history(current.ticker, 'W');
assert(!myWeeklyData.error, 'Error fetching weekly data: ' + myWeeklyData.error);

// Shift weekly H/L/C by 1 to get "previous week" values, as in Pine's high[1], low[1], close[1]
const myPrevHigh = shift(myWeeklyData.high, 1);
const myPrevLow = shift(myWeeklyData.low, 1);
const myPrevClose = shift(myWeeklyData.close, 1);

const myPivotRange = sub(myPrevHigh, myPrevLow);

const myR4Weekly = add(myPrevClose, mult(myPivotRange, 1.1 / 2));
const myR5Weekly = mult(div(myPrevHigh, myPrevLow), myPrevClose);
const myS4Weekly = sub(myPrevClose, mult(myPivotRange, 1.1 / 2));
const myS5Weekly = sub(myPrevClose, sub(myR5Weekly, myPrevClose));

// Land weekly values onto the current chart's candles (using 'le' to mimic
// lookahead_on, where the current week's bar can "see" its own prev-week
// derived levels as soon as the week starts), then hold constant.
const myR4Landed = interpolate_sparse_series(land_points_onto_series(myWeeklyData.time, myR4Weekly, time, 'le'), 'constant');
const myR5Landed = interpolate_sparse_series(land_points_onto_series(myWeeklyData.time, myR5Weekly, time, 'le'), 'constant');
const myS4Landed = interpolate_sparse_series(land_points_onto_series(myWeeklyData.time, myS4Weekly, time, 'le'), 'constant');
const myS5Landed = interpolate_sparse_series(land_points_onto_series(myWeeklyData.time, myS5Weekly, time, 'le'), 'constant');

paint(myR5Landed, { name: 'R5', color: 'orange', thickness: 2 });
paint(myR4Landed, { name: 'R4', color: 'red', thickness: 2 });
paint(myS5Landed, { name: 'S5', color: 'orange', thickness: 2 });
paint(myS4Landed, { name: 'S4', color: 'green', thickness: 2 });

// Entry conditions, matching Pine logic exactly
const mySellSignal = for_every(high, close, myR5Landed, (_high, _close, _r5) => _high >= _r5 && _close < _r5);
const myBuySignal = for_every(low, close, myS5Landed, (_low, _close, _s5) => _low <= _s5 && _close > _s5);

register_signal(mySellSignal, 'Sell Signal R5');
register_signal(myBuySignal, 'Buy Signal S5');