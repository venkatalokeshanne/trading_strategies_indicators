describe_indicator('ALT RADAR Altseason Score', 'lower');

// NOTE: This is a best-effort port of the Pine Script. Pine's
// request.security() aligns multiple symbols internally by trading
// time; here we approximate that alignment by landing all auxiliary
// series onto the time axis of the first fetched series (BTC
// Dominance) using a "last known value" (le) match, then
// interpolating with 'constant' mode (no forward-looking data). This
// may cause tiny differences vs TradingView around symbol gaps/holidays.
//
// IMPORTANT: tickers like "BTC.D" and "TOTAL3" are TradingView-only
// synthetic symbols (CRYPTOCAP:BTC.D, CRYPTOCAP:TOTAL3). This
// platform's request.history() does not support them. Previously this
// caused an uncaught Promise rejection ("history: [object Object]")
// because request.history() can reject the promise entirely (instead
// of resolving to { error }) for unsupported tickers. We now wrap each
// request in a .catch() so a failing ticker is turned into a
// resolved { error } object instead of crashing the whole indicator;
// that score component is then excluded (counted as 0).
const myResolution = current.resolution;
const myTickers = ['BTC.D', 'ETHUSDT', 'BTCUSDT', 'TOTAL3', 'BTCUSD', 'AVAXUSDT'];

const myRequests = await Promise.all(
	myTickers.map(_t =>
		request.history(_t, myResolution).catch(_err => ({ error: String(_err && _err.message ? _err.message : _err) }))
	)
);

const [myBtcDData, myEthData, myBtcData, myTotal3Data, myBtcCapData, myAvaxData] = myRequests;

// instead of asserting (which throws and kills the whole indicator),
// we flag each failed request and simply skip that component later.
const myDataOk = myRequests.map(_d => !_d.error);

// base time axis = chart's own time axis, used as a safe fallback
// in case the BTC Dominance series itself fails to load.
const myBaseTime = myDataOk[0] ? myBtcDData.time : time;
const myBtcD = myDataOk[0] ? myBtcDData.close : series_of(null);

function myLandOrNull(_ok, _data) {
	if (!_ok) {
		return series_of(null);
	}
	return interpolate_sparse_series(
		land_points_onto_series(_data.time, _data.close, myBaseTime, 'le'),
		'constant'
	);
}

const myEthLanded = myLandOrNull(myDataOk[1], myEthData);
const myBtcLanded = myLandOrNull(myDataOk[2], myBtcData);
const myTotal3Landed = myLandOrNull(myDataOk[3], myTotal3Data);
const myBtcCapLanded = myLandOrNull(myDataOk[4], myBtcCapData);
const myAvaxLanded = myLandOrNull(myDataOk[5], myAvaxData);

// ratios (will be null-filled if either side failed to load, since
// div() with a null operand yields null for that candle)
const myEthBtc = div(myEthLanded, myBtcLanded);
const myTotal3Btc = div(myTotal3Landed, myBtcCapLanded);
const myAvaxEth = div(myAvaxLanded, myEthLanded);

// EMAs
const myBtcDEma20 = ema(myBtcD, 20);
const myBtcDEma50 = ema(myBtcD, 50);
const myEthBtcEma20 = ema(myEthBtc, 20);
const myEthBtcEma50 = ema(myEthBtc, 50);
const myTotal3Ema20 = ema(myTotal3Landed, 20);
const myTotal3Ema50 = ema(myTotal3Landed, 50);
const myTotal3BtcEma20 = ema(myTotal3Btc, 20);
const myTotal3BtcEma50 = ema(myTotal3Btc, 50);
const myAvaxEthEma20 = ema(myAvaxEth, 20);
const myAvaxEthEma50 = ema(myAvaxEth, 50);

// RSI
const myBtcDRsi = rsi(myBtcD, 14);
const myEthBtcRsi = rsi(myEthBtc, 14);
const myTotal3Rsi = rsi(myTotal3Landed, 14);
const myTotal3BtcRsi = rsi(myTotal3Btc, 14);
const myAvaxEthRsi = rsi(myAvaxEth, 14);

// previous values (shifted)
const myBtcDPrev = shift(myBtcD, 1);
const myEthBtcPrev = shift(myEthBtc, 1);
const myTotal3Prev = shift(myTotal3Landed, 1);
const myTotal3BtcPrev = shift(myTotal3Btc, 1);
const myAvaxEthPrev = shift(myAvaxEth, 1);

// score 1 - BTC Dominance (lower is better for alts)
const myScoreBTC = for_every(
	myBtcD, myBtcDEma20, myBtcDEma50, myBtcDRsi, myBtcDPrev,
	(_d, _e20, _e50, _r, _prev) => {
		if (_d === null || _e20 === null || _e50 === null || _r === null || _prev === null) {
			return 0;
		}
		const myStrong = _d < _e20 && _d < _prev && _r < 50;
		const myBull = _d < _e20 && _e20 < _e50;
		return myStrong ? 2 : (myBull ? 1 : 0);
	});

// score 2 - ETH/BTC
const myScoreETH = for_every(
	myEthBtc, myEthBtcEma20, myEthBtcEma50, myEthBtcRsi, myEthBtcPrev,
	(_v, _e20, _e50, _r, _prev) => {
		if (_v === null || _e20 === null || _e50 === null || _r === null || _prev === null) {
			return 0;
		}
		const myBull = _v > _e20 && _e20 > _e50;
		const myStrong = myBull && _r > 55 && _v > _prev;
		return myStrong ? 2 : (myBull ? 1 : 0);
	});

// score 3 - TOTAL3
const myScoreTOTAL3 = for_every(
	myTotal3Landed, myTotal3Ema20, myTotal3Ema50, myTotal3Rsi, myTotal3Prev,
	(_v, _e20, _e50, _r, _prev) => {
		if (_v === null || _e20 === null || _e50 === null || _r === null || _prev === null) {
			return 0;
		}
		const myBull = _v > _e20 && _e20 > _e50;
		const myStrong = myBull && _r > 55 && _v > _prev;
		return myStrong ? 2 : (myBull ? 1 : 0);
	});

// score 4 - TOTAL3/BTC
const myScoreTOTAL3BTC = for_every(
	myTotal3Btc, myTotal3BtcEma20, myTotal3BtcEma50, myTotal3BtcRsi, myTotal3BtcPrev,
	(_v, _e20, _e50, _r, _prev) => {
		if (_v === null || _e20 === null || _e50 === null || _r === null || _prev === null) {
			return 0;
		}
		const myBull = _v > _e20 && _e20 > _e50;
		const myStrong = myBull && _r > 55 && _v > _prev;
		return myStrong ? 2 : (myBull ? 1 : 0);
	});

// score 5 - AVAX/ETH
const myScoreAVAX = for_every(
	myAvaxEth, myAvaxEthEma20, myAvaxEthEma50, myAvaxEthRsi, myAvaxEthPrev,
	(_v, _e20, _e50, _r, _prev) => {
		if (_v === null || _e20 === null || _e50 === null || _r === null || _prev === null) {
			return 0;
		}
		const myBull = _v > _e20 && _e20 > _e50;
		const myStrong = myBull && _r > 55 && _v > _prev;
		return myStrong ? 2 : (myBull ? 1 : 0);
	});

// total score on base time axis
const myTotalScoreBase = for_every(
	myScoreBTC, myScoreETH, myScoreTOTAL3, myScoreTOTAL3BTC, myScoreAVAX,
	(_s1, _s2, _s3, _s4, _s5) => _s1 + _s2 + _s3 + _s4 + _s5);

// land total score onto the current chart's time axis (constant, no lookahead)
const myTotalScore = interpolate_sparse_series(
	land_points_onto_series(myBaseTime, myTotalScoreBase, time, 'le'),
	'constant');

const myTotalScorePrev = shift(myTotalScore, 1);

// dynamic coloring of the score line, approximating Pine's bgcolor zones
const myScoreColor = for_every(myTotalScore, _s => {
	if (_s === null) return 'gray';
	if (_s >= 8) return '#2ecc71';
	if (_s >= 6) return '#9ccc65';
	if (_s >= 4) return '#ffb74d';
	return '#ef5350';
});

paint(myTotalScore, { name: 'AltseasonScore', color: myScoreColor, thickness: 4, style: 'line' });
paint(horizontal_line(2), { name: 'Level2', color: 'gray', style: 'dotted', thickness: 1 });
paint(horizontal_line(4), { name: 'Level4', color: 'gray', style: 'dotted', thickness: 1 });
paint(horizontal_line(6), { name: 'Level6', color: 'gray', style: 'dotted', thickness: 1 });
paint(horizontal_line(8), { name: 'Level8', color: 'gray', style: 'dotted', thickness: 1 });
paint(horizontal_line(10), { name: 'Level10', color: 'silver', style: 'line', thickness: 1 });

// alert / scanner signals
const myAltseasonStart = for_every(
	myTotalScore, myTotalScorePrev,
	(_s, _prev) => _s !== null && _prev !== null && _s >= 8 && _prev < 8);

const myAltseasonWarning = for_every(
	myTotalScore, myTotalScorePrev,
	(_s, _prev) => _s !== null && _prev !== null && _s <= 3 && _prev > 3);

register_signal(myAltseasonStart, 'Altseason Starting');
register_signal(myAltseasonWarning, 'Altseason Weakening');