describe_indicator('New Paradigm Master Scalper', 'price');

// NOTE: TrendSpider Custom JS does not support a true backtesting
// "strategy" engine (entries/exits with TP/SL ticks) inside custom
// indicators. We reproduce the Pine Script's entry logic exactly
// (same bars will trigger), and expose Long/Short conditions as
// signals usable in Scanner/Alerts/Strategy Tester. The TP/SL tick
// exit logic from Pine (`strategy.exit`) cannot be expressed here;
// see errors_and_warnings_flagged.

const myMoment = library('moment-timezone');

const myTab = input.tab('Settings');
const myAssetType = myTab.select('Asset Class', 'Gold', ['NQ', 'ES', 'Gold']);
const myVolMultiplier = myTab.number('Global Vol Multiplier', 1.0, { min: 0.1, max: 10, step: 0.1 });

const myRow1 = myTab.row();
const myTpTicks = myRow1.number('Take Profit (Ticks)', 100, { min: 10, max: 10000, step: 10 });
const mySlTicks = myRow1.number('Stop Loss (Ticks)', 100, { min: 10, max: 10000, step: 10 });

const myRow2 = myTab.row();
const myUseTrendFilter = myRow2.boolean('Use 200 EMA Trend Filter', true);
const myUseSession = myRow2.boolean('Restrict to NY Session (08:00-15:00 EST)', true);

// --- base IV per asset class ---
const myBaseIv = myAssetType === 'NQ' ? 9.0 : (myAssetType === 'ES' ? 7.5 : 5.0);
const myFinalIv = myBaseIv * myVolMultiplier;

// --- Day-anchored VWAP (resets daily, like ta.vwap in Pine) ---
// We cannot call vwap() inside a loop (rule), so we build it manually
// using plain arithmetic, resetting cumulative sums at each new session.
const myTypicalPrice = hlc3;
const myVwapValues = series_of(null);

let myCumPV = 0;
let myCumVol = 0;
let myPrevDay = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myDayId = bar_at(time[myIndex]).session;

	if (myDayId !== myPrevDay) {
		myCumPV = 0;
		myCumVol = 0;
		myPrevDay = myDayId;
	}

	myCumPV += myTypicalPrice[myIndex] * volume[myIndex];
	myCumVol += volume[myIndex];

	myVwapValues[myIndex] = myCumVol !== 0 ? (myCumPV / myCumVol) : myTypicalPrice[myIndex];
}

const myLowerTarget = sub(myVwapValues, myFinalIv * 2);
const myUpperTarget = add(myVwapValues, myFinalIv * 2);

// --- Volume spike & trend filter ---
const myVolSma20 = sma(volume, 20);
const myIsVolSpike = for_every(volume, myVolSma20, (_v, _vsma) => _v > _vsma * 1.5);
const myEma200 = ema(close, 200);

const myTrendLong = myUseTrendFilter ? for_every(close, myEma200, (_c, _e) => _c > _e) : for_every(close, _c => true);
const myTrendShort = myUseTrendFilter ? for_every(close, myEma200, (_c, _e) => _c < _e) : for_every(close, _c => true);

// --- NY session check (08:00-15:00 America/New_York), using moment-timezone ---
// Pine's time() with session string returns na outside the window;
// we approximate the same window using NY local hour/minute.
const myInSession = time.map(_t => {
	if (!myUseSession) {
		return true;
	}

	const myNYTime = myMoment(_t * 1000).tz('America/New_York');
	const myMinutesOfDay = myNYTime.hours() * 60 + myNYTime.minutes();

	return myMinutesOfDay >= (8 * 60) && myMinutesOfDay < (15 * 60);
});

// --- Entry conditions (exact Pine logic) ---
const myBullFade = for_every(
	low, open, close, myLowerTarget, myIsVolSpike, myTrendLong,
	(_low, _open, _close, _lowerTarget, _volSpike, _trendLong, _prev, _index) => {
		const mySessionOk = myInSession[_index];
		return (_low <= _lowerTarget * 1.001) && (_close > _open) && _volSpike && _trendLong && mySessionOk;
	}
);

const myBearFade = for_every(
	high, open, close, myUpperTarget, myIsVolSpike, myTrendShort,
	(_high, _open, _close, _upperTarget, _volSpike, _trendShort, _prev, _index) => {
		const mySessionOk = myInSession[_index];
		return (_high >= _upperTarget * 0.999) && (_close < _open) && _volSpike && _trendShort && mySessionOk;
	}
);

// --- Visuals ---
paint(myVwapValues, { name: 'VWAP', color: 'gray', thickness: 1 });
paint(myLowerTarget, { name: 'Green Wall', color: '#2ca599', thickness: 2 });
paint(myUpperTarget, { name: 'Red Wall', color: '#ee5451', thickness: 2 });
paint(myUseTrendFilter ? myEma200 : series_of(null), { name: 'EMA 200 Trend', color: '#3179f5', thickness: 1 });

// --- Entry marks ---
const myBullMarks = for_every(myBullFade, low, (_fade, _low) => _fade ? _low : null);
const myBearMarks = for_every(myBearFade, high, (_fade, _high) => _fade ? _high : null);

paint(myBullMarks, { name: 'Fade Long', style: 'labels_below', color: '#2ca599', thickness: 3 });
paint(myBearMarks, { name: 'Fade Short', style: 'labels_above', color: '#ee5451', thickness: 3 });

// --- Signals for Scanner / Alerts / Strategy Tester ---
register_signal(myBullFade, 'Fade Long Entry');
register_signal(myBearFade, 'Fade Short Entry');