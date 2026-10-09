describe_indicator('VASA EMA Ribbon', 'price');

// ---------- Inputs ----------
const ribbonTab = input.tab('Ribbon');
const mySrcName = ribbonTab.select('Source', 'close', constants.price_source_options);
const myBaseLen = ribbonTab.number('Base length', 8, { min: 1, max: 500 });
const myEmaStep = ribbonTab.number('EMA step', 8, { min: 1, max: 500 });
const myCount = ribbonTab.number('EMA count', 6, { min: 2, max: 8 });

const styleTab = input.tab('Style');
const myShadeComp = styleTab.boolean('Shade compression', true);
const myCompPct = styleTab.number('Compression %', 0.5, { min: 0.01, max: 100, step: 0.05 });

const mySrc = market[mySrcName];

// ---------- EMAs (fixed 8, shown up to myCount) ----------
const myLen1 = myBaseLen;
const myLen2 = myBaseLen + myEmaStep;
const myLen3 = myBaseLen + myEmaStep * 2;
const myLen4 = myBaseLen + myEmaStep * 3;
const myLen5 = myBaseLen + myEmaStep * 4;
const myLen6 = myBaseLen + myEmaStep * 5;
const myLen7 = myBaseLen + myEmaStep * 6;
const myLen8 = myBaseLen + myEmaStep * 7;

const myE1 = ema(mySrc, myLen1);
const myE2 = ema(mySrc, myLen2);
const myE3 = ema(mySrc, myLen3);
const myE4 = ema(mySrc, myLen4);
const myE5 = ema(mySrc, myLen5);
const myE6 = ema(mySrc, myLen6);
const myE7 = ema(mySrc, myLen7);
const myE8 = ema(mySrc, myLen8);

// Slowest active EMA depends on myCount.
const mySlowLen = myBaseLen + myEmaStep * (myCount - 1);
const myESlow = ema(mySrc, mySlowLen);

// trend up when fastest EMA is above the active slowest EMA
const myTrendUp = for_every(myE1, myESlow, (_e1, _eSlow) => _e1 > _eSlow);

// Compression: spread of ribbon (e1 to eSlow) relative to price.
const mySpreadPct = for_every(myE1, myESlow, close, (_e1, _eSlow, _c) => _c !== 0 ? Math.abs(_e1 - _eSlow) / _c * 100.0 : null);
const myCompressed = for_every(mySpreadPct, _s => _s !== null && _s < myCompPct);

// ---------- Plots (each EMA shown only if within myCount) ----------
paint(myCount >= 1 ? myE1 : constants.empty_series, { name: 'EMA1', color: '#15803d' });
paint(myCount >= 2 ? myE2 : constants.empty_series, { name: 'EMA2', color: '#15803d' });
paint(myCount >= 3 ? myE3 : constants.empty_series, { name: 'EMA3', color: '#15803d' });
paint(myCount >= 4 ? myE4 : constants.empty_series, { name: 'EMA4', color: '#15803d' });
paint(myCount >= 5 ? myE5 : constants.empty_series, { name: 'EMA5', color: '#15803d' });
paint(myCount >= 6 ? myE6 : constants.empty_series, { name: 'EMA6', color: '#15803d' });
paint(myCount >= 7 ? myE7 : constants.empty_series, { name: 'EMA7', color: '#15803d' });
paint(myCount >= 8 ? myE8 : constants.empty_series, { name: 'EMA8', color: '#15803d' });

// Ribbon fill between fastest EMA and the active slowest EMA.
// Note: fill() only supports a single static color per call, so the
// original dynamic fill (amber on compression, green/red on trend)
// cannot be reproduced exactly. We approximate using color_cloud,
// which colors the fill green when e1 is above eSlow (bull) and red
// when below (bear). The amber "compression" tint is not reproducible
// this way; instead compression is exposed as a scan/alert signal below.
color_cloud(myE1, myESlow, '#15803d', '#b91c1c', 'Bull Fill', 'Bear Fill', 0.08);

// ---------- Signals (confirmed, non-repainting) ----------
const myTurnedUp = for_every(myTrendUp, (_t, _prev, _i) => _i > 0 && _t && !myTrendUp[_i - 1]);
const myTurnedDn = for_every(myTrendUp, (_t, _prev, _i) => _i > 0 && !_t && myTrendUp[_i - 1]);
const myCompressedNew = for_every(myCompressed, (_c, _prev, _i) => _i > 0 && _c && !myCompressed[_i - 1]);

register_signal(myTurnedUp, 'Ribbon Turned Up');
register_signal(myTurnedDn, 'Ribbon Turned Down');
register_signal(myCompressedNew, 'Ribbon Compressed');