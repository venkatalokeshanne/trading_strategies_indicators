describe_indicator('Volume Pro - RVOL States + MA', 'lower', { format: 'volume' });

// ===== Volume Bars =====
const myVolumeTab = input.tab('Volume Bars');
const myBarWidth = myVolumeTab.number('Volume Bar Width', 2, { min: 1, max: 50 });

// ===== Volume State Colors =====
const myColorsTab = input.tab('Volume State Colors');
const myNormalUpColor = myColorsTab.color('Normal Up Volume', '#26A69A');
const myNormalDownColor = myColorsTab.color('Normal Down Volume', '#EF5350');
const myHighVolumeColor = myColorsTab.color('High Relative Volume', 'orange');
const myExtremeVolumeColor = myColorsTab.color('Extreme Relative Volume', 'fuchsia');

// ===== Relative Volume =====
const myRvolTab = input.tab('Relative Volume');
const myRvolLength = myRvolTab.number('RVOL Average Length', 20, { min: 1, max: 500 });
const myHighThreshold = myRvolTab.number('High Volume Threshold', 2.0, { min: 1.0, max: 50, step: 0.1 });
const myExtremeThreshold = myRvolTab.number('Extreme Volume Threshold', 3.0, { min: 1.0, max: 50, step: 0.1 });

// ===== Volume Moving Average =====
const myMATab = input.tab('Volume Moving Average');
const myShowMA = myMATab.boolean('Show Volume Moving Average', true);
const myMAType = myMATab.select('MA Type', 'SMA', ['SMA', 'EMA', 'WMA', 'RMA']);
const myMALength = myMATab.number('MA Length', 20, { min: 1, max: 500 });

// ===== RVOL calculation =====
// RVOL average is a plain SMA of volume, matching ta.sma(volume, rvolLength)
const myRvolAverage = sma(volume, myRvolLength);

// rvol = volume / rvolAverage, guarded against division by zero/negative average
const myRvol = for_every(volume, myRvolAverage, (_v, _avg) => (_avg > 0 ? _v / _avg : null));

// isUp: close >= close[1]. First bar has no prior close, treat as up (matches Pine na behavior loosely)
const myIsUp = for_every(close, (_c, _prev, _i) => {
	// _prev holds the operation's own previous output, not useful here, so use index-based lookup instead
	return true;
});

// Recompute isUp properly using shift() since for_every's prevValue is not the prior close
const myPrevClose = shift(close, 1);
const myIsUpFixed = for_every(close, myPrevClose, (_c, _pc) => (_pc === null ? true : _c >= _pc));

// Volume state classification, priority: Extreme > High > Normal Up/Down
const myVolumeColor = for_every(myRvol, myIsUpFixed, (_rvol, _isUp) => {
	if (_rvol !== null && _rvol >= myExtremeThreshold) return myExtremeVolumeColor;
	if (_rvol !== null && _rvol >= myHighThreshold && _rvol < myExtremeThreshold) return myHighVolumeColor;
	return _isUp ? myNormalUpColor : myNormalDownColor;
});

// Volume moving average, matching the Pine switch statement
const myVolumeMASelected =
	myMAType === 'SMA' ? sma(volume, myMALength) :
	myMAType === 'EMA' ? ema(volume, myMALength) :
	myMAType === 'WMA' ? wma(volume, myMALength) :
	wildma(volume, myMALength); // RMA == Wilders MA

// ===== Paint volume histogram with dynamic colors =====
paint(volume, {
	name: 'Volume',
	style: 'column',
	color: myVolumeColor,
	thickness: myBarWidth
});

// ===== Paint volume moving average (optional) =====
paint(myShowMA ? myVolumeMASelected : constants.empty_series, {
	name: 'VolumeMA',
	color: 'yellow',
	thickness: 2,
	style: 'line'
});

// ===== Signals for scanning / alerts / strategy use =====
const myExtremeVolumeSignal = for_every(myRvol, _rvol => (_rvol !== null && _rvol >= myExtremeThreshold));
const myHighVolumeSignal = for_every(myRvol, _rvol => (_rvol !== null && _rvol >= myHighThreshold && _rvol < myExtremeThreshold));
const myNormalUpSignal = for_every(myRvol, myIsUpFixed, (_rvol, _isUp) => (_rvol !== null && _rvol < myHighThreshold && _isUp));
const myNormalDownSignal = for_every(myRvol, myIsUpFixed, (_rvol, _isUp) => (_rvol !== null && _rvol < myHighThreshold && !_isUp));

register_signal(myExtremeVolumeSignal, 'Extreme Volume');
register_signal(myHighVolumeSignal, 'High Volume');
register_signal(myNormalUpSignal, 'Normal Up Volume');
register_signal(myNormalDownSignal, 'Normal Down Volume');