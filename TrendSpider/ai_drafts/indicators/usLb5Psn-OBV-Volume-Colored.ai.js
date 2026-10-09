describe_indicator('OBV - Volume Colored', 'lower');

// Inputs matching the Pine script's inputs
const myVolMaLength = input.number('Volume MA Length', 10, { min: 1, max: 500 });
const myObvMaLength = input.number('OBV MA Length', 20, { min: 1, max: 500 });
const myObvMaType = input.select('OBV MA Type', 'SMA', ['SMA', 'EMA']);

// OBV: cumulative sum of sign(change(close)) * volume.
// ta.change(close) on the first bar is "na" in Pine, so math.sign(na) is na,
// and ta.cum() treats na as 0 contribution on that bar.
const myObv = for_every(close, volume, (_close, _volume, _prevObv, _index) => {
	if (_index === 0) {
		return 0;
	}
	const myPrevClose = close[_index - 1];
	const myChange = _close - myPrevClose;
	const mySign = myChange > 0 ? 1 : (myChange < 0 ? -1 : 0);
	return (_prevObv || 0) + mySign * _volume;
});

// OBV Moving Average, type selectable
const myObvMa = myObvMaType === 'SMA' ? sma(myObv, myObvMaLength) : ema(myObv, myObvMaLength);

// Volume MA for relative volume coloring
const myVolMa = sma(volume, myVolMaLength);

// Color logic: green if volume > volMA, red if volume < volMA, yellow if equal
const myObvColor = for_every(volume, myVolMa, (_volume, _volMa) => {
	if (_volume > _volMa) {
		return 'green';
	}
	else if (_volume < _volMa) {
		return 'red';
	}
	else {
		return 'yellow';
	}
});

const myObvLine = paint(myObv, { name: 'OBV', color: myObvColor, thickness: 2 });
paint(myObvMa, { name: 'OBVMA', color: 'blue', thickness: 1 });

// Signals for scanners, alerts and strategies
const mySignalObvAboveMa = for_every(myObv, myObvMa, (_obv, _ma) => _obv > _ma);
const mySignalObvBelowMa = for_every(myObv, myObvMa, (_obv, _ma) => _obv < _ma);
const mySignalObvCrossUp = for_every(myObv, myObvMa, (_obv, _ma, _prev, _index) => {
	if (_index === 0) {
		return false;
	}
	return myObv[_index - 1] <= myObvMa[_index - 1] && _obv > _ma;
});
const mySignalObvCrossDown = for_every(myObv, myObvMa, (_obv, _ma, _prev, _index) => {
	if (_index === 0) {
		return false;
	}
	return myObv[_index - 1] >= myObvMa[_index - 1] && _obv < _ma;
});
const mySignalHighRelativeVolume = for_every(volume, myVolMa, (_volume, _volMa) => _volume > _volMa);
const mySignalLowRelativeVolume = for_every(volume, myVolMa, (_volume, _volMa) => _volume < _volMa);

register_signal(mySignalObvAboveMa, 'OBV Above MA');
register_signal(mySignalObvBelowMa, 'OBV Below MA');
register_signal(mySignalObvCrossUp, 'OBV Crosses Above MA');
register_signal(mySignalObvCrossDown, 'OBV Crosses Below MA');
register_signal(mySignalHighRelativeVolume, 'High Relative Volume');
register_signal(mySignalLowRelativeVolume, 'Low Relative Volume');