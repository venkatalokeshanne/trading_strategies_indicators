// ====================================================================
// NNFX BTC SSL+QQE strategy, converted from Pine Script v6.
//
// IMPORTANT CONVERSION NOTES (see errors_and_warnings_flagged too):
// - TrendSpider Custom JS has no strategy engine (no strategy.entry,
//   strategy.exit, position sizing, commission or intrabar stop/limit
//   fills). We can only reproduce the underlying signal logic and
//   expose it via register_signal() for scanners/alerts/backtests,
//   plus plot the visual lines. Position tracking (long/flat/short)
//   is approximated here with a simple sequential simulation so the
//   baseline/QQE flip exits make sense, but ATR based stop-loss /
//   take-profit intrabar fills are NOT simulated (that needs a real
//   order engine) - they are only exposed as reference values.
// ====================================================================

describe_indicator('NNFX BTC SSL QQE SignalForge', 'price');

const settingsTab = input.tab('Settings');
const i_priceSource = settingsTab.select('Price Source', 'close', constants.price_source_options);
const i_invertSig = settingsTab.boolean('Invert Signals', false);

const baselineGrp = input.group('Baseline');
const i_sslLen = baselineGrp.number('SSL Baseline EMA Length', 20, { min: 1, max: 500 });

const keltnerGrp = input.group('Keltner');
const keltnerRow = keltnerGrp.row();
const i_kcLen = keltnerRow.number('Keltner EMA Length', 20, { min: 1, max: 500 });
const i_kcMult = keltnerRow.number('Keltner ATR Mult', 1.5, { min: 0.1, max: 10, step: 0.1 });

const qqeGrp = input.group('QQE');
const qqeRow = qqeGrp.row();
const i_qqeRsiLen = qqeRow.number('QQE RSI Period', 6, { min: 1, max: 100 });
const i_qqeSmooth = qqeRow.number('QQE Smoothing', 5, { min: 1, max: 100 });

const riskGrp = input.group('Risk');
const riskRow = riskGrp.row();
const i_atrLen = riskRow.number('ATR Length', 14, { min: 1, max: 100 });
const i_stopMult = riskRow.number('Stop x ATR', 1.5, { min: 0.1, max: 20, step: 0.1 });
const i_tpMult = riskRow.number('Target x ATR', 3.0, { min: 0.1, max: 20, step: 0.1 });

const backtestGrp = input.group('Backtest');
const backtestRow = backtestGrp.row();
const i_startDate = backtestRow.text('Backtest Start (YYYY-MM-DD)', '2020-01-01');
const i_endDate = backtestRow.text('Backtest End (YYYY-MM-DD)', '2030-12-31');

const mySrc = market[i_priceSource];

// -------------------------------------------------------------------
// Core calculations
// -------------------------------------------------------------------
const mySslLine = ema(mySrc, i_sslLen);
const mySslBull = for_every(mySrc, mySslLine, (_s, _l) => _s > _l);

const myKcAtr = atr(high, low, close, i_kcLen);
const myKcMid = ema(mySrc, i_kcLen);
const myKcUpper = add(myKcMid, mult(myKcAtr, i_kcMult));
const myKcLower = sub(myKcMid, mult(myKcAtr, i_kcMult));

const myQqeRsi = rsi(mySrc, i_qqeRsiLen);
const myQqeFast = ema(myQqeRsi, i_qqeSmooth);
const myQqeSlow = ema(myQqeFast, i_qqeSmooth);
const myQqeHist = sub(myQqeFast, myQqeSlow);
const myQqeBull = for_every(myQqeHist, _h => _h > 0);

const myInsideKC = for_every(mySrc, myKcLower, myKcUpper, (_s, _lo, _up) => _s >= _lo && _s <= _up);

// Date filter (assumption: dates parsed as UTC midnight)
const myStartTs = Date.parse(i_startDate + 'T00:00:00Z') / 1000;
const myEndTs = Date.parse(i_endDate + 'T00:00:00Z') / 1000;
assert(!isNaN(myStartTs) && !isNaN(myEndTs), 'Invalid backtest start/end date format, use YYYY-MM-DD');
const myInDate = for_every(time, _t => _t >= myStartTs && _t <= myEndTs);

// Crossover / crossunder of src vs sslLine
const myPrevSrc = shift(mySrc, 1);
const myPrevSsl = shift(mySslLine, 1);
const myCrossOver = for_every(mySrc, mySslLine, myPrevSrc, myPrevSsl, (_s, _l, _ps, _pl) => _s > _l && _ps <= _pl);
const myCrossUnder = for_every(mySrc, mySslLine, myPrevSrc, myPrevSsl, (_s, _l, _ps, _pl) => _s < _l && _ps >= _pl);

const myLongRaw = for_every(myCrossOver, myQqeBull, myInsideKC, myInDate, (_co, _qb, _ik, _id) => _co && _qb && _ik && _id);
const myShortRaw = for_every(myCrossUnder, myQqeBull, myInsideKC, myInDate, (_cu, _qb, _ik, _id) => _cu && !_qb && _ik && _id);
const myLongInv = for_every(myCrossUnder, myQqeBull, myInsideKC, myInDate, (_cu, _qb, _ik, _id) => _cu && !_qb && _ik && _id);
const myShortInv = for_every(myCrossOver, myQqeBull, myInsideKC, myInDate, (_co, _qb, _ik, _id) => _co && _qb && _ik && _id);

const myLongEntry = i_invertSig ? myLongInv : myLongRaw;
const myShortEntry = i_invertSig ? myShortInv : myShortRaw;

// -------------------------------------------------------------------
// Position state simulation (flip-based exits only, no stop/target
// intrabar simulation - see notes above)
// -------------------------------------------------------------------
const myExitLong = series_of(false);
const myExitShort = series_of(false);
let myPosition = 0; // 1 long, -1 short, 0 flat

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myQb = myQqeBull[myIndex];
	const mySb = mySslBull[myIndex];

	let myDoExitLong = myPosition > 0 && (i_invertSig ? (myQb || mySb) : (!myQb || !mySb));
	let myDoExitShort = myPosition < 0 && (i_invertSig ? (!myQb || !mySb) : (myQb || mySb));

	myExitLong[myIndex] = myDoExitLong;
	myExitShort[myIndex] = myDoExitShort;

	if (myDoExitLong) { myPosition = 0; }
	if (myDoExitShort) { myPosition = 0; }

	if (myPosition === 0 && myLongEntry[myIndex]) { myPosition = 1; }
	else if (myPosition === 0 && myShortEntry[myIndex]) { myPosition = -1; }
}

// Reference ATR based stop/target distances (informational only,
// not actually simulated as intrabar order fills)
const myAtrVal = atr(high, low, close, i_atrLen);
const myStopDist = mult(myAtrVal, i_stopMult);
const myTargetDist = mult(myAtrVal, i_tpMult);

// -------------------------------------------------------------------
// Plots
// -------------------------------------------------------------------
const mySslColor = for_every(mySslBull, _b => _b ? '#2962FF' : '#EF5350');
paint(mySslLine, { name: 'SSL Baseline', color: mySslColor, thickness: 2 });
paint(myKcMid, { name: 'Keltner Mid', color: '#9E9E9E' });
paint(myKcUpper, { name: 'Keltner Upper', color: '#B0BEC5', style: 'dotted' });
paint(myKcLower, { name: 'Keltner Lower', color: '#B0BEC5', style: 'dotted' });

// -------------------------------------------------------------------
// Signals for scanners / alerts / backtests
// -------------------------------------------------------------------
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myExitLong, 'Exit Long');
register_signal(myExitShort, 'Exit Short');
register_signal(myQqeBull, 'QQE Bull');
register_signal(mySslBull, 'SSL Bull');
register_signal(myInsideKC, 'Inside Keltner');