describe_indicator('Kumo VMI (Ichimoku Volatility and Momentum Index)', 'lower', { decimals: 2 });

// --- Inputs ---
const myMaLength = input.number('Moving Average Length', 9, { min: 1, max: 500 });
const myMaType = input.select('Moving Average Type', 'SMA', ['SMA', 'EMA', 'WMA', 'RMA']);

const myUseAtr = input.boolean('Enable ATR Indicator', true);
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 500 });

// --- Ichimoku calculations ---
const myTenkanSen = div(add(highest(high, 9), lowest(low, 9)), 2);
const myKijunSen = div(add(highest(high, 26), lowest(low, 26)), 2);
const mySpanA = div(add(myTenkanSen, myKijunSen), 2);
const mySpanB = div(add(highest(high, 52), lowest(low, 52)), 2);

// Cloudwidth Index (Cloud Volatility)
const myCwi = for_every(mySpanA, mySpanB, (_a, _b) => Math.abs(_a - _b));

// TK Distance (Momentum/Divergence)
const myTkDist = for_every(myTenkanSen, myKijunSen, (_t, _k) => Math.abs(_t - _k));

// --- ATR (Wilder's RMA based True Range), matches ta.rma(ta.tr, length) ---
const myRawAtr = atr(high, low, close, myAtrLength);

// --- Dynamic MA over CWI, based on user selection ---
// RMA (Wilders) corresponds to wildma() in this engine
let myMa;
if (myMaType === 'SMA') {
	myMa = sma(myCwi, myMaLength);
}
else if (myMaType === 'EMA') {
	myMa = ema(myCwi, myMaLength);
}
else if (myMaType === 'WMA') {
	myMa = wma(myCwi, myMaLength);
}
else {
	myMa = wildma(myCwi, myMaLength);
}

// --- Plotting ---
paint(myCwi, { name: 'Cloudwidth Index', color: '#FF00FF', thickness: 2 });
paint(myMa, { name: 'CWI Moving Average', color: 'yellow', thickness: 1 });
paint(myTkDist, { name: 'TK Distance', color: 'white', thickness: 2 });

// ATR is conditionally plotted; when disabled we paint a null series
// with the same name/parameters, to keep paint() calls constant.
paint(myUseAtr ? myRawAtr : series_of(null), { name: 'ATR', color: '#00FFFF', thickness: 2 });

// --- Scanning and strategy signals ---
// CWI crossing above/below its Moving Average (volatility expansion/contraction)
const myCwiAboveMa = for_every(myCwi, myMa, (_c, _m) => _c > _m);
const myCwiCrossUp = for_every(myCwi, myMa, (_c, _m, _p, _i) => _i > 0 && _c > _m && myCwi[_i - 1] <= myMa[_i - 1]);
const myCwiCrossDown = for_every(myCwi, myMa, (_c, _m, _p, _i) => _i > 0 && _c < _m && myCwi[_i - 1] >= myMa[_i - 1]);

register_signal(myCwiAboveMa, 'CWI Above Moving Average');
register_signal(myCwiCrossUp, 'CWI Crosses Above Moving Average');
register_signal(myCwiCrossDown, 'CWI Crosses Below Moving Average');

// TK Distance rising, indicating increasing momentum/divergence
const myTkDistRising = for_every(myTkDist, (_t, _p, _i) => _i > 0 && _t > myTkDist[_i - 1]);
register_signal(myTkDistRising, 'TK Distance Rising');