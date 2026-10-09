// ─────────────────────────────────────────────────────────────────
// This is a conversion of a Pine Script STRATEGY into a TrendSpider
// Custom JS INDICATOR. The Custom JS API has no concept of broker
// positions, pyramided entries, average price, or stop/limit orders
// (strategy.entry/strategy.exit/strategy.close do not exist here).
// So the "nanpin" (position averaging), max positions, stop loss and
// take profit management from the Pine script CANNOT be reproduced
// exactly - those are strategy/broker-side behaviors.
// What IS reproduced exactly is the core signal logic:
//   - Fast/Slow SMA (with the 5-minute period halving rule)
//   - Time filter (start/end hour)
//   - Long/Short entry signal conditions
//   - Trend background coloring
// Long/Short signals are exposed via register_signal() so they can be
// used in Scanners, Alerts and the Strategy Tester module.
// ─────────────────────────────────────────────────────────────────
describe_indicator('Scalping London New York Signals', 'price');

const myTab = input.tab('Moving Averages');
const myFastPeriod = myTab.number('Fast SMA Period', 60, { min: 1, max: 2000 });
const mySlowPeriod = myTab.number('Slow SMA Period', 280, { min: 1, max: 2000 });

const myTimeTab = input.tab('Time Filter');
const myUseTimeFilter = myTimeTab.boolean('Use Time Filter', true);
const myStartHour = myTimeTab.number('Start Hour', 7, { min: 0, max: 23 });
const myEndHour = myTimeTab.number('End Hour', 17, { min: 0, max: 23 });

const myDisplayTab = input.tab('Display');
const myOnlyLong = myDisplayTab.boolean('Only Long', false);
const myShowBackground = myDisplayTab.boolean('Show Trend Background', true);
const myShowSignals = myDisplayTab.boolean('Show Additional Signals', false);

// Pine halves the periods when timeframe is exactly 5 minutes
const myIsM5 = current.resolution === '5';
const myFastPeriodResolved = myIsM5 ? Math.max(1, Math.floor(myFastPeriod / 5)) : myFastPeriod;
const mySlowPeriodResolved = myIsM5 ? Math.max(1, Math.floor(mySlowPeriod / 5)) : mySlowPeriod;

const myFastMA = sma(close, myFastPeriodResolved);
const mySlowMA = sma(close, mySlowPeriodResolved);

// Hour of each candle, in exchange time zone (proxy for Pine's hour(time))
const myHourAtIndex = time.map(_t => time_of(_t).hours);

const myTimeAllowed = myHourAtIndex.map(_h => {
	if (!myUseTimeFilter) return true;
	return myStartHour <= myEndHour
		? (_h >= myStartHour && _h <= myEndHour)
		: (_h >= myStartHour || _h <= myEndHour);
});

// Signals use PREVIOUS candle's open/close and MA relation, same as
// Pine's open[1], close[1], fastMA[1], slowMA[1] (barstate.isconfirmed
// means "evaluate on the previous, already-closed bar").
const myPrevOpen = shift(open, 1);
const myPrevClose = shift(close, 1);
const myPrevFastMA = shift(myFastMA, 1);
const myPrevSlowMA = shift(mySlowMA, 1);

const myLongSignal = for_every(
	myPrevOpen, myPrevClose, myPrevFastMA, myPrevSlowMA,
	(_po, _pc, _pf, _ps, _prev, _i) =>
		myTimeAllowed[_i] && _po < _pc && _pf > _ps
);

const myShortSignal = for_every(
	myPrevOpen, myPrevClose, myPrevFastMA, myPrevSlowMA,
	(_po, _pc, _pf, _ps, _prev, _i) =>
		myTimeAllowed[_i] && _po > _pc && _pf < _ps && !myOnlyLong
);

paint(myFastMA, { name: 'Fast SMA', color: '#00DCFF', thickness: 2 });
paint(mySlowMA, { name: 'Slow SMA', color: '#FFBE3C', thickness: 2 });

// Trend background approximation - colors candles instead of a
// full-panel background, since color_candles is the closest built-in
const myTrendColors = for_every(myFastMA, mySlowMA, (_f, _s) => {
	if (!myShowBackground) return null;
	if (_f > _s) return 'rgba(0,120,255,0.15)';
	if (_f < _s) return 'rgba(255,70,90,0.15)';
	return null;
});
color_candles(myTrendColors);

// Optional entry markers
const myBuyMarks = for_every(myLongSignal, _l => (myShowSignals && _l) ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myShortSignal, _s => (myShowSignals && _s) ? constants.icons.triangle_down : null);
paint(myBuyMarks, { style: 'labels_below', color: '#00FFAA', name: 'Buy Signal' });
paint(mySellMarks, { style: 'labels_above', color: '#FF5A78', name: 'Sell Signal' });

// Signals for Scanners / Alerts / Strategy Tester
register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');