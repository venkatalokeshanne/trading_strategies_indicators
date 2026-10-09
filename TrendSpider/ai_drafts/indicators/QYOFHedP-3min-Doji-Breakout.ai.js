describe_indicator('Doji Breakout 3m', 'price');

// === INPUTS ===
const myWickMult = input.number('Body < X * Total Wicks', 0.2, { min: 0.01, max: 2, step: 0.05 });
const myTimeframe = input.text('Timeframe', '3');

// === FETCH LOWER TIMEFRAME DATA ===
const myData3m = await request.history(current.ticker, myTimeframe);
assert(!myData3m.error, `Error fetching ${myTimeframe} data: ${myData3m.error}`);

// === DOJI CALCULATION ON THE REQUESTED TIMEFRAME ===
const myBody = for_every(myData3m.close, myData3m.open, (_c, _o) => Math.abs(_c - _o));
const myUpperWick = for_every(myData3m.high, myData3m.open, myData3m.close, (_h, _o, _c) => _h - Math.max(_o, _c));
const myLowerWick = for_every(myData3m.open, myData3m.close, myData3m.low, (_o, _c, _l) => Math.min(_o, _c) - _l);
const myTotalWicks = for_every(myUpperWick, myLowerWick, (_u, _l) => _u + _l);
const myIsDoji = for_every(myBody, myTotalWicks, (_b, _t) => _t > 0 ? (_b < _t * myWickMult) : false);

// Pine's request.security(tf, x[1]) reads the PREVIOUS completed bar of the
// lower timeframe, as seen from the current bar. We replicate that by
// shifting the lower timeframe series by 1 before landing them onto the chart.
const myDojiHighShifted = shift(myData3m.high, 1);
const myDojiLowShifted = shift(myData3m.low, 1);
const myDojiCheckShifted = for_every(shift(myData3m.high, 1), (_x) => _x); // placeholder, replaced below
const myIsDojiShifted = shift(myIsDoji, 1);

// Land the shifted lower timeframe values onto the current chart's candles.
// Method 'le' means "most recent lower timeframe bar whose time is <= this
// chart's candle time", which mirrors Pine's non-repainting security() lookup.
const myDojiHighLanded = interpolate_sparse_series(
	land_points_onto_series(myData3m.time, myDojiHighShifted, time, 'le'),
	'constant'
);
const myDojiLowLanded = interpolate_sparse_series(
	land_points_onto_series(myData3m.time, myDojiLowShifted, time, 'le'),
	'constant'
);
const myDojiCheckLanded = interpolate_sparse_series(
	land_points_onto_series(myData3m.time, myIsDojiShifted, time, 'le'),
	'constant'
);

// === SIGNALS (on the current chart's close) ===
const myBuySignal = for_every(myDojiCheckLanded, myDojiHighLanded, close, (_chk, _h, _c) => Boolean(_chk) && _c > _h);
const mySellSignal = for_every(myDojiCheckLanded, myDojiLowLanded, close, (_chk, _l, _c) => Boolean(_chk) && _c < _l);

// === TRACK LAST DOJI HIGH/LOW (persists until a new Doji appears) ===
const myLastDojiHigh = for_every(myDojiCheckLanded, myDojiHighLanded, (_chk, _h, _prev, _i) => Boolean(_chk) ? _h : (_prev === undefined ? null : _prev));
const myLastDojiLow = for_every(myDojiCheckLanded, myDojiLowLanded, (_chk, _l, _prev, _i) => Boolean(_chk) ? _l : (_prev === undefined ? null : _prev));

// === VISUALS ===
const myDojiHighLine = paint(myLastDojiHigh, { name: 'DojiHigh', color: '#FFD600', style: 'ladder', thickness: 2 });
const myDojiLowLine = paint(myLastDojiLow, { name: 'DojiLow', color: '#FFD600', style: 'ladder', thickness: 2 });

// Mark doji candles with a label above the candle
const myDojiMark = for_every(myDojiCheckLanded, (_chk) => Boolean(_chk) ? constants.icons.circle : null);
paint(myDojiMark, { name: 'DojiMark', style: 'labels_above', color: 'yellow' });

// Buy/Sell markers as labels on candles
const myBuyMark = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMark = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);
paint(myBuyMark, { name: 'BuySignal', style: 'labels_below', color: '#00C853' });
paint(mySellMark, { name: 'SellSignal', style: 'labels_above', color: '#D50000' });

// Label the doji levels line with current status (last point only)
paint_label_at_line(myDojiHighLine, close.length - 1, 'Doji High');
paint_label_at_line(myDojiLowLine, close.length - 1, 'Doji Low');

// === REGISTER SIGNALS FOR SCANNERS, ALERTS, STRATEGY TESTER ===
register_signal(myBuySignal, '3m Buy Breakout');
register_signal(mySellSignal, '3m Sell Breakout');
register_signal(myDojiCheckLanded, 'Doji Detected');