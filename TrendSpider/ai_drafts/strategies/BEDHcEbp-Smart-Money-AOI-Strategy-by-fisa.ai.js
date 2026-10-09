// NOTE: TradingView boxes, bgcolor() backgrounds tied to arbitrary bars, and
// label.new/line.new called conditionally per-bar are not expressible 1:1 in
// this engine (no box primitive, no per-bar dynamic bgcolor, paint()/labels
// must be unconditional calls). This is translated as closely as possible:
// FVG/HTF "boxes" become filled zones, kill-zone bgcolor becomes candle
// coloring, and all markers use labels_above/labels_below instead of
// label.new/line.new. Signal values (BOS/CHoCH/Long/Short) are exact
// translations of the Pine math.
describe_indicator('Smart Money AOI Strategy', 'price');

const myTab = input.tab('Structure');
const myShowHTF = myTab.boolean('Show Higher Timeframe AOI', true);
const myHtfTF = myTab.select('HTF', '60', constants.time_frames);
const myBosLen = myTab.number('Structure Length', 10, { min: 2, max: 200 });

const myNewsTab = input.tab('News Marker');
const myNewsHour = myNewsTab.number('News Hour (Manual)', 14, { min: 0, max: 23 });
const myNewsMinute = myNewsTab.number('News Minute', 30, { min: 0, max: 59 });

// === STRUCTURE (BOS & CHoCH) ===
const myHH = highest(high, myBosLen);
const myLL = lowest(low, myBosLen);

const myHHShift1 = shift(myHH, 1);
const myLLShift1 = shift(myLL, 1);
const myHHShift2 = shift(myHH, 2);
const myLLShift2 = shift(myLL, 2);
const myCloseShift1 = shift(close, 1);

const myBullBOS = for_every(close, myHHShift1, (_c, _h) => _c > _h);
const myBearBOS = for_every(close, myLLShift1, (_c, _l) => _c < _l);

const myChochBull = for_every(myBullBOS, myCloseShift1, myLLShift2, (_bb, _c1, _ll2) => _bb && _c1 < _ll2);
const myChochBear = for_every(myBearBOS, myCloseShift1, myHHShift2, (_be, _c1, _hh2) => _be && _c1 > _hh2);

// === FAIR VALUE GAP ===
const myHighShift2 = shift(high, 2);
const myLowShift2 = shift(low, 2);

const myBullFVG = for_every(low, myHighShift2, (_l, _h2) => _l > _h2);
const myBearFVG = for_every(high, myLowShift2, (_h, _l2) => _h < _l2);

// FVG zone top/bottom series (null when no gap on that candle)
const myFvgTop = for_every(myBullFVG, myBearFVG, high, myHighShift2, (_bull, _bear, _h, _h2) => _bull ? _h2 : (_bear ? _h : null));
const myFvgBottom = for_every(myBullFVG, myBearFVG, low, myLowShift2, (_bull, _bear, _l, _l2) => _bull ? _l : (_bear ? _l2 : null));

// === SUPPLY / DEMAND ===
const myDemand = for_every(low, myLL, (_l, _ll) => _l === _ll);
const mySupply = for_every(high, myHH, (_h, _hh) => _h === _hh);

// === EQUAL HIGHS / LOWS (Liquidity) ===
// Assumes mintick is approximated as 10^-decimals of the current symbol.
const myMinTick = Math.pow(10, -current.decimals);
const myHighShift1 = shift(high, 1);
const myLowShift1 = shift(low, 1);
const myEqHigh = for_every(high, myHighShift1, (_h, _hs1) => Math.abs(_h - _hs1) < myMinTick * 5);
const myEqLow = for_every(low, myLowShift1, (_l, _ls1) => Math.abs(_l - _ls1) < myMinTick * 5);

// === HTF AREA OF INTEREST ===
const myHtfData = await request.history(current.ticker, myHtfTF);
assert(!myHtfData.error, 'Error fetching HTF data: ' + myHtfData.error);

const myHtfHighLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfData.high, time, 'le'),
	'constant'
);
const myHtfLowLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfData.low, time, 'le'),
	'constant'
);

const myHtfHighToPaint = myShowHTF ? myHtfHighLanded : series_of(null);
const myHtfLowToPaint = myShowHTF ? myHtfLowLanded : series_of(null);

// === ENTRY LOGIC ===
const myLongCond = for_every(myBullBOS, close, myHtfLowLanded, myBullFVG, (_bb, _c, _hl, _bf) => _bb && _c > _hl && _bf);
const myShortCond = for_every(myBearBOS, close, myHtfHighLanded, myBearFVG, (_be, _c, _hh, _bf) => _be && _c < _hh && _bf);

// === KILL ZONES ===
const myHourSeries = time.map(_t => time_of(_t).hours);
const myMinuteSeries = time.map(_t => time_of(_t).minutes);

const myLondonKill = myHourSeries.map(_h => _h === 8);
const myNyKill = myHourSeries.map(_h => _h === 13);
const myCandleColors = myHourSeries.map((_h, _i) => myLondonKill[_i] ? 'rgba(255,165,0,0.15)' : (myNyKill[_i] ? 'rgba(0,128,0,0.15)' : null));
color_candles(myCandleColors);

// === MANUAL NEWS MARKER ===
const myIsNewsTime = for_every(
	series_of(0),
	series_of(0),
	(..._args) => false
); // placeholder, replaced below for correctness

const myNewsFlags = myHourSeries.map((_h, _i) => _h === myNewsHour && myMinuteSeries[_i] === myNewsMinute);
const myNewsLabels = myNewsFlags.map((_f, _i) => _f ? high[_i] : null);

// === PAINTING ===
paint(for_every(myBullBOS, (_v) => _v ? low[close.length - 1] * 0 + null : null), { name: 'Placeholder', style: 'line', hidden: true });

// BOS markers
paint(myBullBOS.map((_v, _i) => _v ? low[_i] : null), { name: 'BullBOS', style: 'labels_below', color: 'green' });
paint(myBearBOS.map((_v, _i) => _v ? high[_i] : null), { name: 'BearBOS', style: 'labels_above', color: 'red' });

// CHoCH (shift) markers
paint(myChochBull.map((_v, _i) => _v ? low[_i] : null), { name: 'ShiftBull', style: 'labels_below', color: 'lime' });
paint(myChochBear.map((_v, _i) => _v ? high[_i] : null), { name: 'ShiftBear', style: 'labels_above', color: 'orange' });

// Supply / Demand markers
paint(myDemand.map((_v, _i) => _v ? low[_i] : null), { name: 'Buyers', style: 'labels_below', color: 'green' });
paint(mySupply.map((_v, _i) => _v ? high[_i] : null), { name: 'Sellers', style: 'labels_above', color: 'red' });

// Equal highs / lows markers
paint(myEqHigh.map((_v, _i) => _v ? high[_i] : null), { name: 'EqualHigh', style: 'labels_above', color: 'yellow' });
paint(myEqLow.map((_v, _i) => _v ? low[_i] : null), { name: 'EqualLow', style: 'labels_below', color: 'yellow' });

// FVG zone fill (acts as the "box")
fill(
	paint(myFvgTop, { name: 'FVGTop', style: 'line', hidden: true }),
	paint(myFvgBottom, { name: 'FVGBottom', style: 'line', hidden: true }),
	'green',
	0.15
);

// HTF AOI zone fill (acts as the "box")
fill(
	paint(myHtfHighToPaint, { name: 'HTFHigh', style: 'ladder', color: 'blue', thickness: 1 }),
	paint(myHtfLowToPaint, { name: 'HTFLow', style: 'ladder', color: 'blue', thickness: 1 }),
	'blue',
	0.08
);

// Entry markers
paint(myLongCond.map((_v, _i) => _v ? low[_i] : null), { name: 'BuySignal', style: 'labels_below', color: 'green' });
paint(myShortCond.map((_v, _i) => _v ? high[_i] : null), { name: 'SellSignal', style: 'labels_above', color: 'red' });

// News marker
paint(myNewsLabels, { name: 'NewsMarker', style: 'labels_above', color: 'red' });

// === SIGNALS FOR SCANNER / ALERTS / STRATEGY ===
register_signal(myBullBOS, 'Bullish BOS');
register_signal(myBearBOS, 'Bearish BOS');
register_signal(myChochBull, 'Bullish CHoCH');
register_signal(myChochBear, 'Bearish CHoCH');
register_signal(myBullFVG, 'Bullish FVG');
register_signal(myBearFVG, 'Bearish FVG');
register_signal(myDemand, 'Demand Zone');
register_signal(mySupply, 'Supply Zone');
register_signal(myEqHigh, 'Equal Highs');
register_signal(myEqLow, 'Equal Lows');
register_signal(myLongCond, 'Long Entry');
register_signal(myShortCond, 'Short Entry');