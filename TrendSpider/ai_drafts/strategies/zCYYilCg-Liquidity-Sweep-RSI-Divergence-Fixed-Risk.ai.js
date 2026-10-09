describe_indicator('Liquidity Sweep and RSI Divergence', 'price');

// Inputs
const myRiskPerTrade = input.number('Risk Per Trade ($)', 50.0, { min: 0 });
const myRRRatio = input.number('Risk Reward Ratio', 2.5, { min: 0.1 });
const myBodyPercent = input.number('Max Body Percent of Range', 10.0, { min: 0, max: 100 });
const myWickPercent = input.number('Min Wick Percent of Range', 70.0, { min: 0, max: 100 });
const myLiquidityLookback = input.number('Liquidity Lookback', 50, { min: 1, max: 500 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });

// RSI
const myRsiValue = rsi(close, myRsiLength);

// Candlestick geometry
const myCandleRange = sub(high, low);
const myBodySize = for_every(open, close, (_o, _c) => Math.abs(_o - _c));
const myUpperWick = for_every(high, open, close, (_h, _o, _c) => _h - Math.max(_o, _c));
const myLowerWick = for_every(open, close, low, (_o, _c, _l) => Math.min(_o, _c) - _l);

const myIsDoji = for_every(myCandleRange, myBodySize, (_r, _b) => _r > 0 && _b <= (_r * (myBodyPercent / 100)));

const myIsDragonfly = for_every(myIsDoji, myLowerWick, myCandleRange, myUpperWick, (_doji, _lw, _r, _uw) =>
	_doji && _lw >= (_r * (myWickPercent / 100)) && _uw <= (_r * 0.1)
);

const myIsGravestone = for_every(myIsDoji, myUpperWick, myCandleRange, myLowerWick, (_doji, _uw, _r, _lw) =>
	_doji && _uw >= (_r * (myWickPercent / 100)) && _lw <= (_r * 0.1)
);

// Liquidity sweep & divergence
// prevLowLevel = lowest(low[1], lookback) -> lowest of "low shifted by 1" over lookback window
const myShiftedLow = shift(low, 1);
const myPrevLowLevel = lowest(myShiftedLow, myLiquidityLookback);
const myLongSweep = for_every(low, myPrevLowLevel, (_l, _plv) => _l < _plv);

const myShiftedRsi = shift(myRsiValue, 1);
const myPrevRsiLow = lowest(myShiftedRsi, myLiquidityLookback);
const myBullDivergence = for_every(myRsiValue, myPrevRsiLow, (_rsi, _prl) => _rsi > _prl);

const myShiftedHigh = shift(high, 1);
const myPrevHighLevel = highest(myShiftedHigh, myLiquidityLookback);
const myShortSweep = for_every(high, myPrevHighLevel, (_h, _phv) => _h > _phv);

const myPrevRsiHigh = highest(myShiftedRsi, myLiquidityLookback);
const myBearDivergence = for_every(myRsiValue, myPrevRsiHigh, (_rsi, _prh) => _rsi < _prh);

// Entry conditions (position state tracking from Pine's strategy.position_size
// is not reproducible here, since this engine has no order/strategy state;
// signals below fire every time conditions are true, regardless of an
// existing open position)
const myLongEntrySignal = for_every(myIsDragonfly, myLongSweep, myBullDivergence, (_d, _s, _b) => _d && _s && _b);
const myShortEntrySignal = for_every(myIsGravestone, myShortSweep, myBearDivergence, (_g, _s, _b) => _g && _s && _b);

// Stop loss, take profit and position size, computed only where entry fires
const myLongSL = low;
const myLongRiskPerShare = for_every(close, myLongSL, (_c, _sl) => Math.abs(_c - _sl));
const myLongQty = for_every(myLongRiskPerShare, _r => _r > 0 ? (myRiskPerTrade / _r) : 0);
const myLongTP = for_every(close, myLongSL, (_c, _sl) => _c + (Math.abs(_c - _sl) * myRRRatio));

const myShortSL = high;
const myShortRiskPerShare = for_every(close, myShortSL, (_c, _sl) => Math.abs(_sl - _c));
const myShortQty = for_every(myShortRiskPerShare, _r => _r > 0 ? (myRiskPerTrade / _r) : 0);
const myShortTP = for_every(close, myShortSL, (_c, _sl) => _c - (Math.abs(_sl - _c) * myRRRatio));

// Final valid entries require qty > 0
const myLongEntryValid = for_every(myLongEntrySignal, myLongQty, (_sig, _q) => _sig && _q > 0);
const myShortEntryValid = for_every(myShortEntrySignal, myShortQty, (_sig, _q) => _sig && _q > 0);

// Visuals: liquidity levels
paint(myPrevLowLevel, { name: 'Liquidity Low', color: '#4DA3FF', style: 'line' });
paint(myPrevHighLevel, { name: 'Liquidity High', color: '#EF5350', style: 'line' });

// Entry markers
const myLongMarker = for_every(myLongEntryValid, _v => _v ? constants.icons.triangle_up : null);
const myShortMarker = for_every(myShortEntryValid, _v => _v ? constants.icons.triangle_down : null);

paint(myLongMarker, { name: 'Long Entry', style: 'labels_below', color: 'green' });
paint(myShortMarker, { name: 'Short Entry', style: 'labels_above', color: 'red' });

// Signals for scanners, alerts and strategy testing
register_signal(myLongEntryValid, 'Long Entry Signal');
register_signal(myShortEntryValid, 'Short Entry Signal');
register_signal(myIsDragonfly, 'Dragonfly Doji');
register_signal(myIsGravestone, 'Gravestone Doji');
register_signal(myLongSweep, 'Long Liquidity Sweep');
register_signal(myShortSweep, 'Short Liquidity Sweep');
register_signal(myBullDivergence, 'Bull RSI Divergence');
register_signal(myBearDivergence, 'Bear RSI Divergence');