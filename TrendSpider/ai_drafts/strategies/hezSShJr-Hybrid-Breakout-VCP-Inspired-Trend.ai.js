describe_indicator('Hybrid Breakout', 'price');
// NOTE: TrendSpider Custom JS indicators cannot execute broker-style
// orders (strategy.entry / strategy.exit) and cannot track an open
// position. We reproduce the Pine Script's TREND, SQUEEZE, VOLUME and
// ENTRY SIGNAL logic exactly (same bars will trigger), and expose the
// entry condition as a register_signal() so it can be used in
// Scanners/Alerts/Strategy Tester. Stop/Take-Profit tiers from the
// Pine script are a position-management feature of strategy.exit()
// and have no equivalent in a stateless indicator script, so they
// are not reproduced here.

const myTrendTab = input.tab('Trend Filter');
const myPriceSource = myTrendTab.select('MA Source', 'close', constants.price_source_options);
const myLen50 = myTrendTab.number('Fast MA Length', 50, { min: 1, max: 500 });
const myLen150 = myTrendTab.number('Mid MA Length', 150, { min: 1, max: 500 });
const myLen200 = myTrendTab.number('Slow MA Length', 200, { min: 1, max: 500 });
// Shortened title (was too long for the input() name limit)
const myMaUpLookback = myTrendTab.number('Slow MA Rising Bars', 20, { min: 1, max: 500 });

const myVolaTab = input.tab('Volatility / Pivot Filter');
const myAtrLen = myVolaTab.number('Range Length', 3, { min: 1, max: 100 });
const myLookback = myVolaTab.number('Percentile Lookback', 150, { min: 2, max: 1000 });
// Shortened title (was too long for the input() name limit)
const myPercentileMax = myVolaTab.number('Max Range Pct', 40, { min: 1, max: 100 });
// Shortened title (was too long for the input() name limit)
const myCloseRangeMax = myVolaTab.number('Max Close Range Pct', 4, { min: 0.01, max: 100 });

const myVolTab = input.tab('Volume Filter');
// Shortened title (was too long for the input() name limit)
const myUseVolFilter = myVolTab.boolean('Require Vol Expansion', true);
const myVolMaLen = myVolTab.number('Volume MA Length', 20, { min: 1, max: 500 });
// Shortened title (was too long for the input() name limit)
const myVolMult = myVolTab.number('Volume Mult vs MA', 1.2, { min: 1.0, max: 50 });

const myEntryTab = input.tab('Entry');
// Shortened title (was too long for the input() name limit)
const myBreakoutLookback = myEntryTab.number('Stop Entry Lookback', 3, { min: 1, max: 100 });

// -----------------------------------------------------------
// TREND TEMPLATE
// -----------------------------------------------------------
const myPrice = market[myPriceSource];
const myMa50 = sma(myPrice, myLen50);
const myMa150 = sma(myPrice, myLen150);
const myMa200 = sma(myPrice, myLen200);
const myMa200Shift1 = shift(myMa200, 1);
const myMa200ShiftLookback = shift(myMa200, myMaUpLookback);
const myMa50Shift1 = shift(myMa50, 1);

const myBullishTrend = for_every(
	close, myMa50, myMa150, myMa200, myMa200Shift1, myMa200ShiftLookback, myMa50Shift1,
	(_close, _ma50, _ma150, _ma200, _ma200p1, _ma200pLook, _ma50p1) => {
		return _close > _ma50 && _ma50 > _ma150 && _ma150 > _ma200 &&
			_ma200 > _ma200p1 && _ma200 > _ma200pLook && _ma50 >= _ma50p1;
	});

// -----------------------------------------------------------
// VOLATILITY SQUEEZE / PIVOT DETECTION
// -----------------------------------------------------------
const myHRange = highest(high, myAtrLen);
const myLRange = lowest(low, myAtrLen);
const myRangePct = for_every(myHRange, myLRange, (_h, _l) => (_h - _l) / _h * 100);

const myHClose = highest(close, myAtrLen);
const myLClose = lowest(close, myAtrLen);
const myCloseRangePct = for_every(myHClose, myLClose, (_h, _l) => (_h - _l) / _h * 100);

// percentrank: % of prior (lookback) values that are LESS than the
// current value, over a window of (lookback + 1) values (current + history)
const myRangePercentile = sliding_window_function(myRangePct, myLookback + 1, _vals => {
	const myCurrent = _vals[_vals.length - 1];
	const myHistory = _vals.slice(0, -1);
	const myCount = myHistory.filter(_v => _v < myCurrent).length;
	return myHistory.length > 0 ? (myCount / myHistory.length) * 100 : 0;
});

const myRangeSqueeze = for_every(myRangePercentile, _rp => _rp <= myPercentileMax);
const myCloseSqueeze = for_every(myCloseRangePct, _cr => _cr <= myCloseRangeMax);
const myPivot = for_every(myRangeSqueeze, myCloseSqueeze, (_rs, _cs) => _rs || _cs);

// -----------------------------------------------------------
// VOLUME CONFIRMATION
// -----------------------------------------------------------
const myVolMa = sma(volume, myVolMaLen);
const myVolumeOK = for_every(volume, myVolMa, (_v, _vma) => !myUseVolFilter || _v > _vma * myVolMult);

// -----------------------------------------------------------
// ENTRY SIGNAL (setup bar, matches Pine's longSignal / plotshape)
// -----------------------------------------------------------
const myLongSignal = for_every(
	myBullishTrend, myPivot, myVolumeOK,
	(_trend, _pivot, _volOk) => Boolean(_trend && _pivot && _volOk));

// Breakout trigger: Pine enters via a stop order at the previous bar's
// N-bar high. We approximate the "order would have been triggered"
// condition as "current high crosses above the prior bar's N-bar high".
const myRecentHigh = highest(high, myBreakoutLookback);
const myRecentHighShift1 = shift(myRecentHigh, 1);
const myBreakoutTriggered = for_every(
	high, myRecentHighShift1,
	(_h, _rh1) => _rh1 !== null && _h > _rh1);

const myEntrySignal = for_every(
	myLongSignal, myBreakoutTriggered,
	(_setup, _trigger) => Boolean(_setup && _trigger));

register_signal(myLongSignal, 'Setup Signal');
register_signal(myEntrySignal, 'Entry Trigger');

// -----------------------------------------------------------
// VISUALS
// -----------------------------------------------------------
paint(myMa50, { name: 'MA 50', color: '#2d7dfa', thickness: 1 });
paint(myMa150, { name: 'MA 150', color: '#2ca599', thickness: 1 });
paint(myMa200, { name: 'MA 200', color: '#ee5451', thickness: 1 });

const mySetupMarks = for_every(myLongSignal, low, (_signal, _low) => _signal ? _low : null);
paint(mySetupMarks, { name: 'Setup', style: 'labels_below', color: '#39ff14', thickness: 3 });