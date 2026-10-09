describe_indicator('1H BB 2.0 and 3.0 Levels', 'price');

// Length for the 1 hour Bollinger Bands
const myLength = input.number('BB Length', 20, { min: 1, max: 500 });

// Fetch 1 hour data (used as the source for the Bollinger Bands,
// just like request.security(syminfo.tickerid, "60", ...) in Pine)
const my1HData = await request.history(current.ticker, '60');
assert(!my1HData.error, 'Error fetching 1H data: ' + my1HData.error);

const myBasis1H = sma(my1HData.close, myLength);
const myStdev1H = stdev(my1HData.close, myLength);

const myUpper2_1H = add(myBasis1H, mult(myStdev1H, 2.0));
const myLower2_1H = sub(myBasis1H, mult(myStdev1H, 2.0));
const myUpper3_1H = add(myBasis1H, mult(myStdev1H, 3.0));
const myLower3_1H = sub(myBasis1H, mult(myStdev1H, 3.0));

// Land the 1H values onto the current chart's time axis.
// Pine's request.security repaints the current forming 1H bar value onto
// every lower timeframe bar within it, which is equivalent to landing with
// 'ge' (first target timestamp >= source timestamp) and constant
// (stepline-like) interpolation - this avoids look-ahead / repainting.
const myUpper2Landed = interpolate_sparse_series(
	land_points_onto_series(my1HData.time, myUpper2_1H, time, 'ge'),
	'constant'
);
const myLower2Landed = interpolate_sparse_series(
	land_points_onto_series(my1HData.time, myLower2_1H, time, 'ge'),
	'constant'
);
const myUpper3Landed = interpolate_sparse_series(
	land_points_onto_series(my1HData.time, myUpper3_1H, time, 'ge'),
	'constant'
);
const myLower3Landed = interpolate_sparse_series(
	land_points_onto_series(my1HData.time, myLower3_1H, time, 'ge'),
	'constant'
);

paint(myUpper2Landed, { name: 'Upper2Sigma', color: '#4DA3FF', thickness: 2, style: 'ladder' });
paint(myLower2Landed, { name: 'Lower2Sigma', color: '#4DA3FF', thickness: 2, style: 'ladder' });
paint(myUpper3Landed, { name: 'Upper3Sigma', color: '#EF5350', thickness: 2, style: 'ladder' });
paint(myLower3Landed, { name: 'Lower3Sigma', color: '#EF5350', thickness: 2, style: 'ladder' });

// Scanning / strategy signals: cross events of close vs the bands
const myCrossAboveUpper2 = for_every(close, myUpper2Landed, shift(close, 1), shift(myUpper2Landed, 1),
	(_c, _u2, _pc, _pu2) => _pc !== null && _pu2 !== null && _pc <= _pu2 && _c > _u2
);
const myCrossBelowLower2 = for_every(close, myLower2Landed, shift(close, 1), shift(myLower2Landed, 1),
	(_c, _l2, _pc, _pl2) => _pc !== null && _pl2 !== null && _pc >= _pl2 && _c < _l2
);
const myCrossAboveUpper3 = for_every(close, myUpper3Landed, shift(close, 1), shift(myUpper3Landed, 1),
	(_c, _u3, _pc, _pu3) => _pc !== null && _pu3 !== null && _pc <= _pu3 && _c > _u3
);
const myCrossBelowLower3 = for_every(close, myLower3Landed, shift(close, 1), shift(myLower3Landed, 1),
	(_c, _l3, _pc, _pl3) => _pc !== null && _pl3 !== null && _pc >= _pl3 && _c < _l3
);

register_signal(myCrossAboveUpper2, 'Cross Above Upper 2 Sigma');
register_signal(myCrossBelowLower2, 'Cross Below Lower 2 Sigma');
register_signal(myCrossAboveUpper3, 'Cross Above Upper 3 Sigma');
register_signal(myCrossBelowLower3, 'Cross Below Lower 3 Sigma');