describe_indicator('Keynes Trend Strategy (Reconstructed)', 'price');

// ─── NOTE ───
// Pine's strategy.entry/strategy.close (actual order execution,
// backtest equity, commission) cannot be reproduced in Custom JS API.
// This script reproduces the signal logic (keynes oscillator, HMA
// direction, HTF trend filter, crossover/crossunder) and exposes
// Long Entry / Long Exit as register_signal() outputs usable in
// Scanner / Alerts / Strategy Tester.
// The oscillator formula "keynes = 1.12*EMA5(devPct) - 0.48" is a
// best-effort reconstruction stated by the original author (fit on
// historical data, r≈0.97), not an exact published formula.

const mySignalTab = input.tab('Signal');
const myEmaLen = mySignalTab.number('EMA Length', 20, { min: 1, max: 500 });
const mySmaMidLen = mySignalTab.number('Short SMA Length', 60, { min: 1, max: 500 });
const mySmaLngLen = mySignalTab.number('Long SMA Length', 240, { min: 1, max: 1000 });
const myHmaLen = mySignalTab.number('HMA Length', 217, { min: 1, max: 1000 });
const myPriceSource = mySignalTab.select('Price Source', 'close', constants.price_source_options);
const myLongThr = mySignalTab.number('Long Trigger Threshold', 0, { min: -100, max: 100 });

const myFilterTab = input.tab('Filter');
const myUseHTF = myFilterTab.boolean('Enable HTF Trend Filter', true);
const myHtfRes = myFilterTab.select('HTF Resolution', 'D', constants.time_frames);

const myPrice = market[myPriceSource];

// ─── Keynes crowd psychology oscillator (reconstructed) ───
const myEmaV = ema(myPrice, myEmaLen);
const mySmaMid = sma(myPrice, mySmaMidLen);
const mySmaLng = sma(myPrice, mySmaLngLen);

const myDevPct = mult(div(sub(myPrice, mySmaLng), mySmaLng), 100);
const myKeynes = sub(mult(ema(myDevPct, 5), 1.12), 0.48);

// ─── HMA direction ───
const myHma = hullma(myPrice, myHmaLen);
const myHmaUp = for_every(myHma, shift(myHma, 1), (_h, _p) => _h !== null && _p !== null && _h > _p);

// ─── HTF trend filter ───
const myHtfData = await request.history(current.ticker, myHtfRes);
assert(!myHtfData.error, 'Error fetching HTF data: ' + myHtfData.error);

const myHtfSma = sma(myHtfData.close, mySmaMidLen);
const myHtfCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfData.close, time, 'le'),
	'constant'
);
const myHtfSmaLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfSma, time, 'le'),
	'constant'
);

const myHtfUp = for_every(myHtfCloseLanded, myHtfSmaLanded, (_c, _s) => {
	if (!myUseHTF) {
		return true;
	}
	return _c !== null && _s !== null && _c > _s;
});

// ─── Crossover / Crossunder of Keynes vs threshold ───
const myKeynesPrev = shift(myKeynes, 1);

const myCrossover = for_every(myKeynes, myKeynesPrev, (_k, _p) => _k !== null && _p !== null && _k > myLongThr && _p <= myLongThr);
const myCrossunder = for_every(myKeynes, myKeynesPrev, (_k, _p) => _k !== null && _p !== null && _k < myLongThr && _p >= myLongThr);

const myLongSignal = for_every(myCrossover, myHmaUp, myHtfUp, (_co, _hu, _tu) => Boolean(_co) && Boolean(_hu) && Boolean(_tu));
const myExitSignal = myCrossunder;

register_signal(myLongSignal, 'Long Entry');
register_signal(myExitSignal, 'Long Exit');

// ─── Visual helpers ───
paint(myEmaV, { name: 'EMA', color: 'orange', thickness: 1 });
paint(mySmaMid, { name: 'SMA Mid', color: '#4DA3FF', thickness: 1 });
paint(mySmaLng, { name: 'SMA Long', color: 'gray', thickness: 1 });

const myBuyMarks = for_every(myLongSignal, low, (_s, _l) => _s ? _l : null);
const mySellMarks = for_every(myExitSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'Long Entry Marker', style: 'labels_below', color: 'green', thickness: 3 });
paint(mySellMarks, { name: 'Long Exit Marker', style: 'labels_above', color: 'red', thickness: 3 });