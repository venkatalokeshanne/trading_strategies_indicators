describe_indicator('EMA Golden Dead Cross', 'price');

// ── Inputs ──────────────────────────────────────────────────────────────
const myFastLen = input.number('Fast EMA Length', 50, { min: 1, max: 1000 });
const mySlowLen = input.number('Slow EMA Length', 200, { min: 1, max: 1000 });
const myTradeDir = input.select('Trade Direction', 'Both', ['Long Only', 'Short Only', 'Both']);

// ── EMAs ──────────────────────────────────────────────────────────────
const myFastEMA = ema(close, myFastLen);
const mySlowEMA = ema(close, mySlowLen);

const myFastLine = paint(myFastEMA, { name: 'Fast EMA', color: '#FF9800', thickness: 2 });
const mySlowLine = paint(mySlowEMA, { name: 'Slow EMA', color: '#2196F3', thickness: 2 });

// ── Cross signals (equivalent of ta.crossover / ta.crossunder) ─────────
const myGoldenCross = for_every(myFastEMA, mySlowEMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast > _slow && myFastEMA[_i - 1] <= mySlowEMA[_i - 1];
});

const myDeadCross = for_every(myFastEMA, mySlowEMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast < _slow && myFastEMA[_i - 1] >= mySlowEMA[_i - 1];
});

// ── Visual markers (plotshape equivalent) ───────────────────────────────
const myBuyMarks = for_every(myGoldenCross, low, (_cross, _low) => (_cross ? _low : null));
const mySellMarks = for_every(myDeadCross, high, (_cross, _high) => (_cross ? _high : null));

// Note: these paint() calls use the names "Golden Cross" and "Dead Cross".
// register_signal() names must be unique across the whole indicator
// (they share the same namespace as paint() line names), so the
// corresponding signals below have been renamed to avoid the collision
// that was causing the "signal already exists" error.
paint(myBuyMarks, { name: 'Golden Cross', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Dead Cross', style: 'labels_above', color: 'red' });

// ── Trend background (bgcolor equivalent, via candle coloring) ──────────
const myInBull = for_every(myFastEMA, mySlowEMA, (_fast, _slow) => _fast > _slow);
const myCandleColors = for_every(myInBull, _bull => (_bull ? 'rgba(76,175,80,0.2)' : 'rgba(244,67,54,0.2)'));
color_candles(myCandleColors);

// ── Strategy entry/exit signals, filtered by trade direction ────────────
// Note: strategy.entry/strategy.close orders aren't expressible as JS
// strategy orders in this API; we expose the equivalent conditions as
// register_signal() series so they can be used in Strategy Tester,
// Scanners and Alerts.
const myLongAllowed = (myTradeDir === 'Long Only' || myTradeDir === 'Both');
const myShortAllowed = (myTradeDir === 'Short Only' || myTradeDir === 'Both');

const myLongEntrySignal = for_every(myGoldenCross, _cross => _cross && myLongAllowed);
const myShortEntrySignal = for_every(myDeadCross, _cross => _cross && myShortAllowed);
const myLongExitSignal = for_every(myDeadCross, _cross => _cross && myLongAllowed);
const myShortExitSignal = for_every(myGoldenCross, _cross => _cross && myShortAllowed);

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');
register_signal(myGoldenCross, 'Golden Cross Signal');
register_signal(myDeadCross, 'Dead Cross Signal');
register_signal(myInBull, 'Bull Trend');

// ── Info table overlay (table.new equivalent) ────────────────────────────
const myLastFastEMA = myFastEMA.length ? myFastEMA[myFastEMA.length - 1] : null;
const myLastSlowEMA = mySlowEMA.length ? mySlowEMA[mySlowEMA.length - 1] : null;
const myLastInBull = myInBull.length ? myInBull[myInBull.length - 1] : false;

paint_overlay('EmaInfoTable', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: 'Fast EMA', color: '#FF9800', background_color: 'rgba(0,0,0,0.6)' },
			{ text: myLastFastEMA === null ? 'n/a' : myLastFastEMA.toFixed(2), color: '#FF9800', background_color: 'rgba(0,0,0,0.6)' }
		]
	}, {
		cells: [
			{ text: 'Slow EMA', color: '#2196F3', background_color: 'rgba(0,0,0,0.6)' },
			{ text: myLastSlowEMA === null ? 'n/a' : myLastSlowEMA.toFixed(2), color: '#2196F3', background_color: 'rgba(0,0,0,0.6)' }
		]
	}, {
		cells: [
			{ text: 'Trend', color: 'white', background_color: 'rgba(0,0,0,0.6)' },
			{ text: myLastInBull ? 'BULL' : 'BEAR', color: myLastInBull ? 'green' : 'red', background_color: 'rgba(0,0,0,0.6)' }
		]
	}]
});