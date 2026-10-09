describe_indicator('BTC Scalper T3 Volume Filter', 'price');

// T3 settings
const myT3Tab = input.tab('T3 Settings');
const myT3Length = myT3Tab.number('T3 Length', 8, { min: 1, max: 100 });
const myT3Factor = myT3Tab.number('Volume Factor', 0.7, { min: 0, max: 1, step: 0.1 });

// Filters
const myFiltersTab = input.tab('Filters');
const myUseVolumeFilter = myFiltersTab.boolean('Use Volume Confirmation', true);
const myVolumeMaLength = myFiltersTab.number('Volume MA Length', 20, { min: 1, max: 300 });

// Risk management inputs are kept for reference only: TP/SL based order
// execution (strategy.entry/strategy.exit) is not expressible in this
// Custom JS API, which only supports indicators (signals), not strategies.
const myRiskTab = input.tab('Risk Management');
const myTakeProfitPct = myRiskTab.number('Take Profit Percent', 0.8, { min: 0, step: 0.1 });
const myStopLossPct = myRiskTab.number('Stop Loss Percent', 0.5, { min: 0, step: 0.1 });

// T3 calculation: 6x cascaded EMA combined with Tillson coefficients
const myE1 = ema(close, myT3Length);
const myE2 = ema(myE1, myT3Length);
const myE3 = ema(myE2, myT3Length);
const myE4 = ema(myE3, myT3Length);
const myE5 = ema(myE4, myT3Length);
const myE6 = ema(myE5, myT3Length);

const myC1 = -myT3Factor * myT3Factor * myT3Factor;
const myC2 = 3 * myT3Factor * myT3Factor + 3 * myT3Factor * myT3Factor * myT3Factor;
const myC3 = -6 * myT3Factor * myT3Factor - 3 * myT3Factor - 3 * myT3Factor * myT3Factor * myT3Factor;
const myC4 = 1 + 3 * myT3Factor + myT3Factor * myT3Factor * myT3Factor + 3 * myT3Factor * myT3Factor;

const myT3Line = for_every(myE6, myE5, myE4, myE3, (_e6, _e5, _e4, _e3) =>
	myC1 * _e6 + myC2 * _e5 + myC3 * _e4 + myC4 * _e3);

// Volume filter
const myVolMa = sma(volume, myVolumeMaLength);
const myVolumeCondition = for_every(volume, myVolMa, (_v, _vma) => _v > _vma);

// Crossover / crossunder of close vs T3 line
const myCloseShifted = shift(close, 1);
const myT3Shifted = shift(myT3Line, 1);

const myLongCondition = for_every(close, myT3Line, myCloseShifted, myT3Shifted,
	(_c, _t3, _pc, _pt3) => _pc !== null && _pt3 !== null && _c > _t3 && _pc <= _pt3);

const myShortCondition = for_every(close, myT3Line, myCloseShifted, myT3Shifted,
	(_c, _t3, _pc, _pt3) => _pc !== null && _pt3 !== null && _c < _t3 && _pc >= _pt3);

// Apply optional volume filter
const myFinalLong = for_every(myLongCondition, myVolumeCondition,
	(_long, _volOk) => myUseVolumeFilter ? (_long && _volOk) : _long);

const myFinalShort = for_every(myShortCondition, myVolumeCondition,
	(_short, _volOk) => myUseVolumeFilter ? (_short && _volOk) : _short);

// Register signals so this can be used in scanners/alerts/strategy tester
// Note: signal names must be unique among all paint()/register_signal() output
// series, so these are suffixed with "Signal Series" to avoid clashing with
// the painted marker series below which share a similar concept.
register_signal(myFinalLong, 'Buy Signal Series');
register_signal(myFinalShort, 'Sell Signal Series');
register_signal(myUseVolumeFilter ? myVolumeCondition : constants.empty_series, 'Volume Confirmed');

// Paint T3 line
paint(myT3Line, { name: 'T3 Fast Line', color: '#00E5FF', thickness: 2 });

// Background tint approximation when volume condition is active and filter is on
const myBackgroundColor = for_every(myVolumeCondition, _volOk =>
	(myUseVolumeFilter && _volOk) ? 'rgba(0,200,0,0.1)' : null);
color_candles(myBackgroundColor);

// Buy/Sell arrow markers
const myBuyMarks = for_every(myFinalLong, _b => _b ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myFinalShort, _s => _s ? constants.icons.triangle_down : null);

paint(myBuyMarks, { style: 'labels_below', color: 'green', name: 'Buy Marker' });
paint(mySellMarks, { style: 'labels_above', color: 'red', name: 'Sell Marker' });