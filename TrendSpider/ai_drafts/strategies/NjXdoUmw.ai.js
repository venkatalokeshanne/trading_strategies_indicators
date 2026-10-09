describe_indicator('Market Leader PRO (Supertrend + Structure + Volume)', 'price');

// ===== Inputs =====
const atrTab = input.tab('Core');
const atrPeriod = atrTab.number('ATR Length', 10, { min: 1, max: 100 });
const factor = atrTab.number('Supertrend Factor', 3, { min: 0.1, max: 20, step: 0.1 });

const trendRow = atrTab.row();
const emaLen = trendRow.number('EMA Trend', 200, { min: 1, max: 1000 });
const rsiLen = trendRow.number('RSI Length', 14, { min: 1, max: 200 });
const rsiLevel = trendRow.number('RSI Threshold', 50, { min: 1, max: 99 });

const volGroup = atrTab.group('Volume / Structure');
const volLen = volGroup.number('Volume SMA Length', 20, { min: 1, max: 500 });
const lookback = volGroup.number('Breakout Lookback', 20, { min: 1, max: 500 });

const riskGroup = atrTab.group('Risk (informational only)');
const tpPercent = riskGroup.number('TP (%)', 1.2, { min: 0.01, max: 100, step: 0.01 });
const slPercent = riskGroup.number('SL (%)', 0.6, { min: 0.01, max: 100, step: 0.01 });

// ===== Core indicators =====
// NOTE: the Custom JS API's supertrend() only documents returning the Supertrend
// line itself (via `supertrend(length, multiplier, useWicks)`), not an explicit
// "direction" series like Pine's ta.supertrend(). We reconstruct direction by
// comparing close to the Supertrend line: direction < 0 (up-trend) when
// close is above the Supertrend line, direction > 0 (down-trend) otherwise.
// This is mathematically equivalent to Pine's ta.supertrend direction output.
const myStLine = supertrend(atrPeriod, factor, false);
const myDirection = for_every(close, myStLine, (_c, _st) => (_c > _st ? -1 : 1));

const myEma200 = ema(close, emaLen);
const myRsi = rsi(close, rsiLen);

const myVolMA = sma(volume, volLen);
const myHighVol = for_every(volume, myVolMA, (_v, _vma) => _v > _vma);

const myHighestHigh = highest(high, lookback);
const myLowestLow = lowest(low, lookback);

// Pine's ta.change(direction) compares current vs previous bar's value
const myPrevDirection = shift(myDirection, 1);
const myDirectionChange = for_every(myDirection, myPrevDirection, (_d, _pd) => _d - _pd);

const myPrevHighestHigh = shift(myHighestHigh, 1);
const myPrevLowestLow = shift(myLowestLow, 1);

// ===== Conditions =====
const myTrendUp = for_every(close, myEma200, (_c, _e) => _c > _e);
const myTrendDown = for_every(close, myEma200, (_c, _e) => _c < _e);

const myMomentumUp = for_every(myRsi, _r => _r > rsiLevel);
const myMomentumDown = for_every(myRsi, _r => _r < rsiLevel);

const myStUp = for_every(myDirectionChange, _dc => _dc < 0);
const myStDown = for_every(myDirectionChange, _dc => _dc > 0);

const myBreakoutUp = for_every(close, myPrevHighestHigh, (_c, _hh) => _c > _hh);
const myBreakoutDown = for_every(close, myPrevLowestLow, (_c, _ll) => _c < _ll);

const myLongSignal = for_every(
	myTrendUp, myMomentumUp, myStUp, myBreakoutUp, myHighVol,
	(_tu, _mu, _su, _bu, _hv) => _tu && _mu && _su && _bu && _hv
);

const myShortSignal = for_every(
	myTrendDown, myMomentumDown, myStDown, myBreakoutDown, myHighVol,
	(_td, _md, _sd, _bd, _hv) => _td && _md && _sd && _bd && _hv
);

// Exit on trend change (as per Pine logic, direction change against position)
const myExitLong = for_every(myDirectionChange, _dc => _dc > 0);
const myExitShort = for_every(myDirectionChange, _dc => _dc < 0);

// ===== Visual =====
const myStColor = for_every(myDirection, _d => (_d < 0 ? '#26A69A' : '#EF5350'));

paint(myEma200, { name: 'EMA200', color: '#FFD54F', thickness: 1 });
paint(myStLine, { name: 'Supertrend', color: myStColor, thickness: 2 });
paint(myHighestHigh, { name: 'Resistance', color: '#EF5350', style: 'dotted' });
paint(myLowestLow, { name: 'Support', color: '#26A69A', style: 'dotted' });

// Candle coloring to mimic bgcolor() long/short zones
const myCandleColors = for_every(
	myLongSignal, myShortSignal,
	(_l, _s) => (_l ? 'rgba(38,166,154,0.3)' : (_s ? 'rgba(239,83,80,0.3)' : null))
);
color_candles(myCandleColors);

// ===== Signals for Scanner / Alerts / Strategy =====
register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');
register_signal(myExitLong, 'Exit Long Signal');
register_signal(myExitShort, 'Exit Short Signal');
register_signal(myTrendUp, 'Trend Up');
register_signal(myTrendDown, 'Trend Down');
register_signal(myHighVol, 'High Volume');