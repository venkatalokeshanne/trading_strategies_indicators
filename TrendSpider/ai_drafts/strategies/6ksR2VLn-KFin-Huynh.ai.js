describe_indicator('ST Fast Slow plus SMA DCA Basket', 'price');

// This indicator reproduces the trend/entry logic of the original
// Pine Script strategy. The Custom JS API has no access to a
// strategy engine (no open trades count, no equity, no order
// management, no basket TP/SL/trailing). Only the SuperTrend lines,
// the SMA and the resulting trend-based entry signals are
// reproduced here. See the flagged warning below for details.

const myTab = input.tab('Supertrend');
const myFastGroup = myTab.group('Fast Supertrend');
const myFastRow = myFastGroup.row();
const myStFastAtr = myFastRow.number('ST Fast ATR', 10, { min: 1, max: 100 });
const myStFastMult = myFastRow.number('ST Fast Mult', 3.0, { min: 0.1, max: 20, step: 0.1 });

const mySlowGroup = myTab.group('Slow Supertrend');
const mySlowRow = mySlowGroup.row();
const myStSlowAtr = mySlowRow.number('ST Slow ATR', 10, { min: 1, max: 100 });
const myStSlowMult = mySlowRow.number('ST Slow Mult', 6.0, { min: 0.1, max: 20, step: 0.1 });

const myMaTab = input.tab('MA and Orders');
const myMaGroup = myMaTab.group('Moving Average');
const myMaPeriod = myMaGroup.number('MA Period', 10, { min: 1, max: 500 });

const myOrdersGroup = myMaTab.group('DCA Basket (signal approximation only)');
const myOrdersRow = myOrdersGroup.row();
const myMaxOrders = myOrdersRow.number('Max Orders', 6, { min: 1, max: 50 });
const myDcaDelaySeconds = myOrdersRow.number('DCA Delay (seconds)', 60, { min: 0, max: 86400 });

// SuperTrend lines (built-in supertrend() only returns the line value,
// not a direction flag, so direction is derived by comparing price
// to the line, which is mathematically equivalent to the Pine
// direction flip logic).
const myStFastLine = supertrend(myStFastAtr, myStFastMult, false);
const myStSlowLine = supertrend(myStSlowAtr, myStSlowMult, false);
const myMaValue = sma(close, myMaPeriod);

const myTrendUp = for_every(myStFastLine, myStSlowLine, close, myMaValue, (_fast, _slow, _close, _ma) => _fast > _slow && _close > _ma);
const myTrendDown = for_every(myStFastLine, myStSlowLine, close, myMaValue, (_fast, _slow, _close, _ma) => _fast < _slow && _close < _ma);

// Approximates the "enough delay passed and max orders not reached"
// gating from the Pine script, using an internal running counter
// and the last signal timestamp. There is no real open-trades count
// here (no strategy engine), so "orders opened since last flat trend"
// is used as a proxy for openTradesCount.
const myEntrySignals = for_every(myTrendUp, myTrendDown, time, (_up, _down, _time, _prev, _index) => {
	const myState = _prev || { lastTime: null, orderCount: 0, lastTrend: null };
	const myCurrentTrend = _up ? 'up' : (_down ? 'down' : null);

	if (myCurrentTrend === null) {
		myState.orderCount = 0;
		myState.lastTrend = null;
		return { buy: false, sell: false, state: myState };
	}

	if (myState.lastTrend !== myCurrentTrend) {
		myState.orderCount = 0;
	}

	const myDelayPassed = myState.lastTime === null || (_time - myState.lastTime >= myDcaDelaySeconds);
	let myBuy = false;
	let mySell = false;

	if (myState.orderCount < myMaxOrders && myDelayPassed) {
		myState.orderCount += 1;
		myState.lastTime = _time;
		myBuy = myCurrentTrend === 'up';
		mySell = myCurrentTrend === 'down';
	}

	myState.lastTrend = myCurrentTrend;
	return { buy: myBuy, sell: mySell, state: myState };
});

const myBuyEntry = for_every(myEntrySignals, _signal => _signal.buy);
const mySellEntry = for_every(myEntrySignals, _signal => _signal.sell);

paint(myStFastLine, { name: 'SuperTrend Fast', color: '#ef5350', thickness: 2, forceUsePriceAxis: true });
paint(myStSlowLine, { name: 'SuperTrend Slow', color: '#42a5f5', thickness: 2, forceUsePriceAxis: true });
paint(myMaValue, { name: 'SMA', color: '#ff9800', thickness: 1, forceUsePriceAxis: true });

register_signal(myTrendUp, 'Trend Up');
register_signal(myTrendDown, 'Trend Down');
register_signal(myBuyEntry, 'Buy Entry');
register_signal(mySellEntry, 'Sell Entry');