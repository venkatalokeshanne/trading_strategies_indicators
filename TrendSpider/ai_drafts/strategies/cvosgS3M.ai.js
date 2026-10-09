describe_indicator('CryptoRSI', 'lower');

// Preset selection, mirrors the Pine Script "Original" / "Agressif" presets
const myPreset = input.select('Preset', 'Original', ['Original', 'Agressif']);
const myIsAgressif = myPreset == 'Agressif';
const myRsiPeriod = myIsAgressif ? 7 : 20;
const myBuyThreshold = myIsAgressif ? 80 : 60;
const mySellThreshold = myIsAgressif ? 70 : 50;
const myUseWmaExit = !myIsAgressif;
const mySmoothRsiEnabled = !myIsAgressif;
const myMarketFilterEnabled = true;
const myWmaLength = 50;
const mySmoothRsiPeriod = 10;
const myMarketFilterTicker = 'BITSTAMP:BTCUSD';
const myMarketFilterEmaPeriod = 50;

// RSI and smoothed RSI
const myRsi = rsi(close, myRsiPeriod);
const mySmoothRsi = sma(myRsi, mySmoothRsiPeriod);
const myFinalRsi = mySmoothRsiEnabled ? mySmoothRsi : myRsi;

// WMA used for exit
const myWmaExit = wma(close, myWmaLength);

// Market filter data fetched from the daily chart of the reference ticker
const myMarketHistory = await request.history(myMarketFilterTicker, 'D');
assert(!myMarketHistory.error, 'Error fetching market filter data: ' + myMarketHistory.error);

const myMarketEma = ema(myMarketHistory.close, myMarketFilterEmaPeriod);

// Land both market close and market EMA onto the current chart's time axis
const myMarketCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myMarketHistory.time, myMarketHistory.close, time, 'le'),
	'constant'
);
const myMarketEmaLanded = interpolate_sparse_series(
	land_points_onto_series(myMarketHistory.time, myMarketEma, time, 'le'),
	'constant'
);

const myMarketAboveEma = for_every(myMarketCloseLanded, myMarketEmaLanded, (_c, _e) => (_c != null && _e != null) ? _c > _e : false);

// Crossunder of close below WMA exit line, used only when myUseWmaExit is true
const myCrossUnder = for_every(close, myWmaExit, (_c, _w, _prev, _i) => {
	if (_i < 1) return false;
	return (close[_i - 1] >= myWmaExit[_i - 1]) && (_c < _w);
});

// Buy / Sell conditions, matching the Pine Script logic exactly
const myBuyCondition = for_every(myFinalRsi, myMarketAboveEma, (_rsi, _marketOk) => {
	const myFilterOk = (!myMarketFilterEnabled) || _marketOk;
	return myFilterOk && (_rsi > myBuyThreshold);
});

const mySellCondition = myUseWmaExit
	? myCrossUnder
	: for_every(myFinalRsi, _rsi => _rsi < mySellThreshold);

// Plots for debugging, mirroring the Pine Script plot() and hline() calls
paint(myFinalRsi, { name: 'RSI', color: '#2962FF', thickness: 2 });
paint(horizontal_line(myBuyThreshold), { name: 'Buy Threshold', color: 'green', style: 'dotted' });
paint(horizontal_line(mySellThreshold), { name: 'Sell Threshold', color: 'red', style: 'dotted' });

// Signals usable in Scanners, Alerts and Strategy Tester
register_signal(myBuyCondition, 'Buy Signal');
register_signal(mySellCondition, 'Sell Signal');

// Fixed: register_signal() needs a full series, not a single scalar value.
// Built a proper per-candle series: true whenever the market filter is
// enabled and the market close is below its EMA on that candle.
const myMarketFilterActiveSeries = for_every(myMarketAboveEma, _aboveEma => myMarketFilterEnabled && !_aboveEma);
register_signal(myMarketFilterActiveSeries, 'Market Filter Active (Below EMA)');