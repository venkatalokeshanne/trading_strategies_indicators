describe_indicator('LUBE Friction Oscillator', 'lower', { decimals: 4 });

// ────────────────────────────────────────────────────────────────
// NOTE: This is a line-by-line translation of the original Pine
// Script. The strategy.entry/strategy.close/position sizing logic
// from Pine (which depends on live equity and leverage) can not be
// replicated inside a Custom JS indicator, since indicators do not
// manage a trading account. Instead, the three alertcondition()
// calls from the original script are mapped onto register_signal()
// outputs (LONG, SHORT, CLOSE TRADE), which is the closest possible
// equivalent usable in TrendSpider Scanners / Alerts / Strategy
// Tester.
// ────────────────────────────────────────────────────────────────

const myInputsTab1 = input.tab('Friction');
const myBarsBackRow = myInputsTab1.row();
const myBarsBack = myBarsBackRow.number('Bars Back (friction)', 500, { min: 10, max: 2000 });
const myRangeInput = myBarsBackRow.number('Bars Back (lowest/highest)', 100, { min: 2, max: 1000 });

const myLevelsRow = myInputsTab1.row();
const myFLevel = myLevelsRow.number('Friction Stop Level (0-100)', 50, { min: 0, max: 100 });
const myTLevel = myLevelsRow.number('Trade Trigger Level', -10, { min: -100, max: 100 });

const myInputsTab2 = input.tab('Trend / Trading');
const myPriceSource = myInputsTab2.select('Source', 'close', constants.price_source_options);
const myEnableShort = myInputsTab2.boolean('Enable Shorts?', true);
const myLeverageUnused = myInputsTab2.number('Leverage (informational only)', 2, { min: 0.5, max: 50 });

const myPrice = market[myPriceSource];

const myFl = myFLevel / 100;
const myTl = myTLevel / 100;

// ────────────────────────────────────────────────────────────────
// Friction computation: per-candle loop looking back up to
// myBarsBack candles, exactly reproducing the Pine `for` loop.
// This is plain arithmetic (no indicator function calls), so it is
// safe to run inside a loop.
// ────────────────────────────────────────────────────────────────
const myFriction = series_of(0);

for (let myIdx = 0; myIdx < close.length; myIdx += 1) {
	let myFrictionValue = 0;

	for (let myI = 1; myI <= myBarsBack; myI += 1) {
		const myRefIdx = myIdx - myI;

		if (myRefIdx < 0) {
			continue;
		}

		if (high[myRefIdx] >= close[myIdx] && low[myRefIdx] <= close[myIdx]) {
			myFrictionValue += (1 + myBarsBack) / (myI + myBarsBack);
		}
	}

	myFriction[myIdx] = myFrictionValue;
}

const myLowF = lowest(myFriction, myRangeInput);
const myHighF = highest(myFriction, myRangeInput);

const myMidF = for_every(myLowF, myHighF, (_l, _h) => _l * (1 - myFl) + _h * myFl);
const myLowF2 = for_every(myLowF, myHighF, (_l, _h) => _l * (1 - myTl) + _h * myTl);

// Pine's [5] offset means "look back 5 bars", which maps to
// shift(series, 5) in TrendSpider.
const myMidF5 = shift(myMidF, 5);
const myLowF25 = shift(myLowF2, 5);
const myHighF5 = shift(myHighF, 5);

// FIR filter, replicating nz() by treating missing shifted values as 0
const myPriceShift1 = for_every(shift(myPrice, 1), _v => _v === null ? 0 : _v);
const myPriceShift2 = for_every(shift(myPrice, 2), _v => _v === null ? 0 : _v);
const myPriceShift3 = for_every(shift(myPrice, 3), _v => _v === null ? 0 : _v);

const myFir = for_every(myPrice, myPriceShift1, myPriceShift2, myPriceShift3, (_p, _p1, _p2, _p3) => (4 * _p + 3 * _p1 + 2 * _p2 + _p3) / 10);
const myFirPrev = for_every(shift(myFir, 1), _v => _v === null ? 0 : _v);

const myTrend = for_every(myFir, myFirPrev, (_f, _fp) => _f > _fp ? 1 : -1);

const myLong = for_every(myFriction, myLowF25, myTrend, (_fr, _l25, _tr) => _fr < _l25 && _tr === 1);
const myShort = for_every(myFriction, myLowF25, myTrend, (_fr, _l25, _tr) => _fr < _l25 && _tr === -1);
const myEnd = for_every(myFriction, myMidF5, (_fr, _m5) => _fr > _m5);

const myKeepLong = for_every(myLong, myShort, myEnd, (_l, _s, _e, _prev) => (_s || _e) ? 0 : (_l ? 1 : (_prev || 0)));
const myKeepShort = for_every(myLong, myShort, myEnd, (_l, _s, _e, _prev) => (_l || _e) ? 0 : (_s ? 1 : (_prev || 0)));

// barcount: 1-based bar index, exactly as in Pine
const myBarCount = for_every(close, (_c, _prev, _idx) => _idx + 1);

const myLongEntry = for_every(myLong, myBarCount, (_l, _bc) => _l && _bc > 20);
const myShortEntry = for_every(myShort, myBarCount, (_s, _bc) => myEnableShort && _s && _bc > 20);

// alertcondition CLOSE TRADE: previous bar was in a position, this
// bar is flat
const myKeepLongPrev = for_every(shift(myKeepLong, 1), _v => _v || 0);
const myKeepShortPrev = for_every(shift(myKeepShort, 1), _v => _v || 0);
const myCloseTrade = for_every(myKeepLongPrev, myKeepShortPrev, myKeepLong, myKeepShort, (_klp, _ksp, _kl, _ks) => (_klp === 1 || _ksp === 1) && (_kl === 0 && _ks === 0));

const myLongAlert = for_every(myKeepLong, myKeepLongPrev, (_kl, _klp) => _kl === 1 && _klp === 0);
const myShortAlert = for_every(myKeepShort, myKeepShortPrev, (_ks, _ksp) => _ks === 1 && _ksp === 0);

register_signal(myLongAlert, 'LUBE Long Alert');
register_signal(myShortAlert, 'LUBE Short Alert');
register_signal(myCloseTrade, 'LUBE Close Trade Alert');
register_signal(myLongEntry, 'LUBE Long Entry');
register_signal(myShortEntry, 'LUBE Short Entry');
register_signal(myKeepLong, 'LUBE In Long Position');
register_signal(myKeepShort, 'LUBE In Short Position');

const myCandleColors = for_every(myKeepLong, myKeepShort, (_kl, _ks) => _kl === 1 ? 'lime' : (_ks === 1 ? 'red' : null));
color_candles(myCandleColors);

paint(myFriction, { name: 'Friction', color: 'gray', thickness: 1 });

const myMidLine = paint(myMidF5, { name: 'Mid Friction', color: 'red', thickness: 1 });
const myLowLine = paint(myLowF25, { name: 'Low Friction', color: 'silver', thickness: 1 });
const myHighLine = paint(myHighF5, { name: 'High Friction', color: 'silver', thickness: 1 });

fill(myLowLine, myHighLine, 'white', 0.15);