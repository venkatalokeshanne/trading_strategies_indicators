describe_indicator('TradingFlow: Torque Flow Oscillator', 'lower', { decimals: 1 });

// -------------------------------------
// Inputs (mirrors Pine Script group layout)
// -------------------------------------

const myGeoTab = input.tab('Geometry and Mass');
const myAtrLen = myGeoTab.number('ATR Length (Normalization)', 14, { min: 5, max: 200 });
const myBodyWeight = myGeoTab.number('Body Force Weight', 1.0, { min: 0.1, max: 50, step: 0.1 });
const myWickWeight = myGeoTab.number('Wick Torque Weight', 1.3, { min: 0.1, max: 50, step: 0.1 });
const myVolLen = myGeoTab.number('Relative Volume Length', 20, { min: 5, max: 200 });

const myFlowTab = input.tab('Flow Dynamics');
const myMemLen = myFlowTab.number('Flow Memory Length', 12, { min: 3, max: 100 });
const mySigLen = myFlowTab.number('Signal Smoothing', 5, { min: 1, max: 50 });

const myLevelTab = input.tab('Dynamic Levels');
const myLevelLen = myLevelTab.number('Extreme Lookback', 80, { min: 30, max: 500 });
const myLevelPct = myLevelTab.number('Extreme Percentile', 90.0, { min: 70.0, max: 99.0, step: 1.0 });

// -------------------------------------
// Normalized Geometry (Dimensionless)
// -------------------------------------

const myAtrValue = atr(high, low, close, myAtrLen);
const myAtrBase = shift(myAtrValue, 1);

// A one-tick floor; we approximate the symbol's tick size using current.decimals,
// since syminfo.mintick is not exposed in this scripting API.
const myTickFloor = current.decimals ? Math.pow(10, -current.decimals) : 1e-10;

const myAtrSafe = for_every(myAtrBase, _a => (_a === null || _a === undefined || isNaN(_a)) ? null : Math.max(_a, myTickFloor));

// Rolling median of prior volume, used as the relative volume baseline
const myVolShifted = shift(volume, 1);
const myVolBase = sliding_window_function(myVolShifted, myVolLen, _vals => {
	if (_vals.some(_v => _v === null || _v === undefined || isNaN(_v))) {
		return null;
	}
	const mySorted = [..._vals].sort((_a, _b) => _a - _b);
	const myMid = Math.floor(mySorted.length / 2);
	return mySorted.length % 2 !== 0 ? mySorted[myMid] : (mySorted[myMid - 1] + mySorted[myMid]) / 2;
});

// Mass: falls back to constant 1.0 when the asset has no volume data at all
const myMassSeries = current.volumeDataAvailable
	? for_every(volume, myVolBase, (_v, _vb) => {
		if (_v === null || _v === undefined || isNaN(_v)) {
			return null;
		}
		if (_v > 0 && _vb !== null && _vb !== undefined && _vb > 0) {
			const myRelVol = Math.max(0.25, Math.min(_v / _vb, 4.0));
			return Math.sqrt(myRelVol);
		}
		else if (_v === 0) {
			return 0.0;
		}
		return null;
	})
	: series_of(1.0);

// -------------------------------------
// Net Torque
// -------------------------------------

const myRawTorque = for_every(open, close, high, low, myAtrSafe, myMassSeries, (_o, _c, _h, _l, _a, _m) => {
	if (_a === null || _a === undefined || isNaN(_a) || _m === null || _m === undefined || isNaN(_m)) {
		return null;
	}
	const myBody = (_c - _o) / _a;
	const myUpperWick = (_h - Math.max(_o, _c)) / _a;
	const myLowerWick = (Math.min(_o, _c) - _l) / _a;
	const myBodyForce = myBody * myBodyWeight * _m;
	const myWickTorque = (myLowerWick - myUpperWick) * myWickWeight * _m;
	return myBodyForce + myWickTorque;
});

// -------------------------------------
// Damped Flow (exponential decay, matches Pine's recursive flow[1])
// -------------------------------------

const myDamp = Math.exp(-1.0 / myMemLen);

const myFlow = for_every(myRawTorque, (_r, _prev) => {
	if (_r === null || _r === undefined || isNaN(_r)) {
		return _prev === undefined ? null : _prev;
	}
	if (_prev === null || _prev === undefined) {
		return _r;
	}
	return myDamp * _prev + (1.0 - myDamp) * _r;
});

const myTfo = ema(myFlow, 3);
const myTfoSig = ema(myTfo, mySigLen);

// -------------------------------------
// Dynamic Directional Extremes
// -------------------------------------

const myAbsTfoShifted = shift(for_every(myTfo, _t => (_t === null || _t === undefined || isNaN(_t)) ? null : Math.abs(_t)), 1);

const myExtremeLevel = sliding_window_function(myAbsTfoShifted, myLevelLen, _vals => {
	if (_vals.some(_v => _v === null || _v === undefined || isNaN(_v))) {
		return null;
	}
	const mySorted = [..._vals].sort((_a, _b) => _a - _b);
	const myRank = Math.ceil((myLevelPct / 100) * _vals.length);
	return mySorted[Math.max(0, myRank - 1)];
});

// -------------------------------------
// Display scaling (index points, matches Pine's *100)
// -------------------------------------

const myTfoIndex = mult(myTfo, 100.0);
const mySignalIndex = mult(myTfoSig, 100.0);
const myUpperIndex = mult(myExtremeLevel, 100.0);
const myLowerIndex = mult(myExtremeLevel, -100.0);

// -------------------------------------
// Colors
// -------------------------------------

const myBullStrong = '#32B8AD';
const myBullWeak = '#79C9C2';
const myBearStrong = '#E56773';
const myBearWeak = '#EBA2AA';
const myBullLine = '#248D84';
const myBearLine = '#C4515C';
const mySignalColor = '#F28A00';

const myPrevTfoIndex = shift(myTfoIndex, 1);
const myHistColors = for_every(myTfoIndex, myPrevTfoIndex, (_t, _pt) => {
	if (_t === null || _t === undefined || isNaN(_t)) {
		return null;
	}
	const myRising = (_pt !== null && _pt !== undefined && _t > _pt);
	if (_t >= 0) {
		return myRising ? myBullStrong : myBullWeak;
	}
	return myRising ? myBearWeak : myBearStrong;
});

// -------------------------------------
// Painting
// -------------------------------------

paint(myTfoIndex, { name: 'TFO Index', color: myHistColors, style: 'column' });
paint(mySignalIndex, { name: 'Signal', color: mySignalColor, thickness: 2 });
paint(myUpperIndex, { name: 'Positive Pressure Extreme', color: myBullLine, thickness: 1 });
paint(myLowerIndex, { name: 'Negative Pressure Extreme', color: myBearLine, thickness: 1 });

// -------------------------------------
// Signals for scanners, alerts and strategies
// -------------------------------------

register_signal(for_every(myTfoIndex, myPrevTfoIndex, (_t, _pt) => _t !== null && _pt !== null && _t > _pt), 'TFO Rising');
register_signal(for_every(myTfoIndex, myPrevTfoIndex, (_t, _pt) => _t !== null && _pt !== null && _t < _pt), 'TFO Falling');
register_signal(for_every(myTfoIndex, (_t) => _t !== null && _t > 0), 'TFO Bullish Zone');
register_signal(for_every(myTfoIndex, (_t) => _t !== null && _t < 0), 'TFO Bearish Zone');
register_signal(for_every(myTfoIndex, myUpperIndex, (_t, _u) => _t !== null && _u !== null && _t > _u), 'TFO Above Positive Extreme');
register_signal(for_every(myTfoIndex, myLowerIndex, (_t, _l) => _t !== null && _l !== null && _t < _l), 'TFO Below Negative Extreme');