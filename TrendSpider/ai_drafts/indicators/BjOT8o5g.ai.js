describe_indicator('Erken Sinyal Kompozit (CDV + CRS)', 'lower');

// Experimental conversion from Pine Script v6. Logic is reproduced as
// closely as the Custom JS API allows. Cumulative CDV accumulates over
// the full available history on the chart (same as Pine's "var float"
// accumulator starting at bar 0), so results depend on how much history
// is loaded on the chart.
const myWarmupBuffer = input.number('Isinma Periyodu', 30, { min: 0, max: 2000 });
const myMatchWindow = input.number('Eslesme Penceresi', 3, { min: 1, max: 20 });
const myLookbackX = input.number('Son X Bar', 10, { min: 1, max: 500 });
const myPeriod = 200;

// ---- fetch XU100 close, aligned onto this chart's time series ----
// Fix: the previous error ("history: [object Object]") happened because
// request.history() itself can throw/reject (not only return an
// { error } object) when a ticker is unavailable on a given account/data
// feed. An uncaught rejection from the `await` call bubbles up to the
// engine as a raw object, producing an unreadable "[object Object]"
// error. We now wrap the call in try/catch so any throw is caught here,
// and we gracefully fall back to using the chart's own close series
// instead of XU100 (the indicator still runs, just without the
// relative-strength-to-XU100 component in that case).
let myXuData = null;
let myXuErrorText = null;

try {
	myXuData = await request.history('XU100', current.resolution);
	if (myXuData && myXuData.error) {
		myXuErrorText = typeof myXuData.error === 'string' ? myXuData.error : JSON.stringify(myXuData.error);
	}
}
catch (myCaughtError) {
	myXuErrorText = typeof myCaughtError === 'string' ? myCaughtError : (myCaughtError && myCaughtError.message) || 'Unknown error fetching XU100 data';
}

const myXuAvailable = !myXuErrorText && myXuData && Array.isArray(myXuData.time) && myXuData.time.length > 0;
const myXuClose = myXuAvailable
	? interpolate_sparse_series(land_points_onto_series(myXuData.time, myXuData.close, time, 'le'), 'constant')
	: close;

// ---- CDV calculation ----
const myTw = sub(high, max_of(open, close));
const myBw = sub(min_of(open, close), low);
const myBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));
const myTotalRange = add(myTw, myBw, myBody);
const myCondExtra = for_every(close, open, myBody, (_c, _o, _b) => _c >= _o ? 2 * _b : 0);
const myRate = for_every(myTotalRange, myTw, myBw, myCondExtra, (_tr, _tw, _bw, _ce) => _tr > 0 ? 0.5 * (_tw + _bw + _ce) / _tr : 0.5);
const myDeltaUp = mult(volume, myRate);
const myDeltaDown = mult(volume, sub(1, myRate));
const myAnlikDelta = for_every(close, open, myDeltaUp, myDeltaDown, (_c, _o, _du, _dd) => _c >= _o ? _du : -_dd);
const myCdv = for_every(myAnlikDelta, (_ad, _prev) => (_prev || 0) + _ad);

// ---- CRS ----
const myRatio = for_every(close, myXuClose, (_c, _x) => _x > 0 ? _c / _x : 0);

// ---- Normalization ----
const myHhCdv = highest(myCdv, myPeriod);
const myLlCdv = lowest(myCdv, myPeriod);
const myHhCrs = highest(myRatio, myPeriod);
const myLlCrs = lowest(myRatio, myPeriod);
const myCdvNorm = for_every(myCdv, myHhCdv, myLlCdv, (_cv, _hh, _ll) => _hh != _ll ? ((_cv - _ll) / (_hh - _ll)) * 50 : 0);
const myCrsNorm = for_every(myRatio, myHhCrs, myLlCrs, (_r, _hh, _ll) => _hh != _ll ? ((_r - _ll) / (_hh - _ll)) * 50 : 0);
const myKompozitVal = for_every(myCdvNorm, myCrsNorm, (_cn, _crn, _prev, _idx) => _idx < myPeriod ? 0 : _cn + _crn);
const myKompozitMa = ema(myKompozitVal, 5);

// ---- Signals ----
const myYeterliVeri = for_every(myKompozitMa, (_v, _prev, _idx) => _idx >= (myPeriod + myWarmupBuffer));

function myCrossoverSeries(_a, _b) {
	const myShiftedA = shift(_a, 1);
	const myShiftedB = shift(_b, 1);
	return for_every(_a, _b, myShiftedA, myShiftedB, (_ca, _cb, _pa, _pb) => _ca > _cb && _pa <= _pb);
}

const myLowestPrev20 = lowest(shift(myKompozitMa, 1), 20);
const myDipRaw = myCrossoverSeries(myKompozitMa, myLowestPrev20);
const myDipSinyal = for_every(myDipRaw, myYeterliVeri, (_d, _y) => _d && _y);

const myThresholdRaw = myCrossoverSeries(myKompozitMa, series_of(30));
const myThresholdSinyal = for_every(myThresholdRaw, myYeterliVeri, (_d, _y) => _d && _y);

const myMomentumEma = ema(myKompozitMa, 10);
const myMomentumRaw = myCrossoverSeries(myKompozitMa, myMomentumEma);
const myMomentumSinyal = for_every(myMomentumRaw, myYeterliVeri, (_d, _y) => _d && _y);

function myBarsSinceOf(_boolSeries) {
	return for_every(_boolSeries, (_b, _prev) => {
		if (_b) return 0;
		if (_prev === null || _prev === undefined) return null;
		return _prev + 1;
	});
}

const myBarsSinceDip = myBarsSinceOf(myDipSinyal);
const myBarsSinceThr = myBarsSinceOf(myThresholdSinyal);
const myBirlesikSinyal = for_every(
	myThresholdSinyal, myDipSinyal, myBarsSinceDip, myBarsSinceThr,
	(_th, _dip, _bd, _bt) => (_th && _bd != null && _bd <= myMatchWindow) || (_dip && _bt != null && _bt <= myMatchWindow)
);

// ---- Screener style outputs ----
const myBirlesikNum = for_every(myBirlesikSinyal, _b => _b ? 1 : 0);
const myHighestXBirlesik = highest(myBirlesikNum, myLookbackX);
const mySonXBardaBirlesik = for_every(myHighestXBirlesik, _h => _h == 1);
const myBarsSinceBirlesik = myBarsSinceOf(myBirlesikSinyal);

// ---- Register signals for scanners/alerts/strategies ----
register_signal(myDipSinyal, 'Dipten Donus');
register_signal(myThresholdSinyal, '30 Ustu');
register_signal(myMomentumSinyal, 'Momentum Artisi');
register_signal(myBirlesikSinyal, 'Birlesik Sinyal');
register_signal(mySonXBardaBirlesik, 'Son X Barda Birlesik Sinyal');
register_signal(myYeterliVeri, 'Yeterli Gecmis Veri Var');

// ---- Painting ----
paint(myKompozitMa, { name: 'Kompozit EMA', color: '#00bcd4', thickness: 2 });
paint(horizontal_line(50), { name: 'Orta Seviye', color: 'gray', style: 'dotted' });
paint(horizontal_line(30), { name: 'Dip Bolgesi', color: 'red', style: 'dotted' });

const myDipMark = for_every(myDipSinyal, _d => _d ? 31 : null);
const myThresholdMark = for_every(myThresholdSinyal, _d => _d ? 34 : null);
const myMomentumMark = for_every(myMomentumSinyal, _d => _d ? 37 : null);
const myBirlesikMark = for_every(myBirlesikSinyal, _d => _d ? 41 : null);

paint(myDipMark, { name: 'Dipten Donus Isareti', style: 'labels_above', color: 'green' });
paint(myThresholdMark, { name: '30 Ustu Isareti', style: 'labels_above', color: 'yellow' });
paint(myMomentumMark, { name: 'Momentum Artisi Isareti', style: 'labels_above', color: 'blue' });
paint(myBirlesikMark, { name: 'Birlesik Sinyal Isareti', style: 'labels_above', color: 'orange' });