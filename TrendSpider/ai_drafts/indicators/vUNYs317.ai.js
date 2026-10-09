describe_indicator('MHIDa Volume-Dry Pullback', 'price');

// Trend gate (bull) inputs
const trendTab = input.group('Trend gate');
const myEmaGateLen = trendTab.number('EMA gate len', 50, { min: 2, max: 500 });
const myEmaMeanLen = trendTab.number('EMA mean len', 20, { min: 2, max: 500 });

// Volume dried up inputs
const volTab = input.group('Volume dry');
const myVolMaLen = volTab.number('Vol avg len', 20, { min: 2, max: 500 });
const myVolDryMult = volTab.number('Vol dry mult', 0.7, { min: 0.1, max: 1.0, step: 0.05 });

// Dip read inputs
const dipTab = input.group('Dip read');
const myRsiLen = dipTab.number('RSI len', 14, { min: 2, max: 100 });
const myRsiDipLevel = dipTab.number('RSI dip level', 45, { min: 1, max: 99 });
const myUseRsiTurn = dipTab.boolean('Require turn up', true);

// Core calculations, mapped 1:1 from the Pine logic
const myEmaGate = ema(close, myEmaGateLen);
const myEmaMean = ema(close, myEmaMeanLen);
const myRsiV = rsi(close, myRsiLen);
const myVolMa = sma(volume, myVolMaLen);

// 1) we are inside a bull: price above the EMA-gate
const myInToro = for_every(close, myEmaGate, (_close, _emaGate) => _close > _emaGate);

// 2) it is a dip/pullback: price below the mean reference and RSI below the threshold
const myIsPullback = for_every(close, myEmaMean, myRsiV, (_close, _emaMean, _rsiV) => (_close < _emaMean) && (_rsiV !== null && !isNaN(_rsiV) && _rsiV < myRsiDipLevel));

// 3) volume has dried up: current volume below a fraction of its average
const myVolDry = for_every(volume, myVolMa, (_vol, _volMa) => (_volMa !== null && !isNaN(_volMa)) && _vol < _volMa * myVolDryMult);

// 4) (optional) price turns up on the current bar
const myCloseShifted = shift(close, 1);
const myTurnUp = for_every(close, myCloseShifted, (_close, _prevClose, _p, _index) => (!myUseRsiTurn) || (_index === 0 ? false : _close > _prevClose));

// Full highlight: all conditions true
const myFlag = for_every(myInToro, myIsPullback, myVolDry, myTurnUp, (_inToro, _isPullback, _volDry, _turnUp) => _inToro && _isPullback && _volDry && _turnUp);

// Gray dip bars (dip + dry volume, even without full flag)
const myDryDip = for_every(myIsPullback, myVolDry, (_isPullback, _volDry) => _isPullback && _volDry);
const myCandleColors = for_every(myDryDip, _dryDip => _dryDip ? 'rgba(128,128,128,0.7)' : null);
color_candles(myCandleColors);

// Markers for dry-volume pullback (triangle up, below bar)
const myMarkerSeries = for_every(myFlag, low, (_flag, _low) => _flag ? _low : null);
paint(myMarkerSeries, { style: 'labels_below', color: 'lime', name: 'Dry Volume Pullback' });

// Trend lines
paint(myEmaGate, { color: 'teal', thickness: 2, name: 'EMA Gate' });
paint(myEmaMean, { color: 'orange', thickness: 1, name: 'EMA Mean' });

// Signal for scanner/alert/strategy usage
// Renamed to avoid name collision with the paint() line above,
// since paint() and register_signal() share the same name space.
register_signal(myFlag, 'Dry Volume Pullback Signal');
register_signal(myInToro, 'Bull Context');