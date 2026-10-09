describe_indicator('Gold HFT Hybrid EMA ADX Signals', 'price');

// This script reproduces the entry-trigger logic of the supplied Pine
// Strategy (EMA9/EMA21 crossover + ADX filter + session filter).
// TrendSpider Custom JS indicators cannot place broker orders, cannot
// send PineConnector alert messages, and cannot manage trade exits
// (fixed TP/SL, trailing stop). Only the entry signal logic is
// reproduced here as paintable lines and register_signal() outputs,
// which can be used in Scanners, Alerts and the Strategy Tester.

const myFastLength = input.number('Fast EMA Length', 9, { min: 1, max: 200 });
const mySlowLength = input.number('Slow EMA Length', 21, { min: 1, max: 200 });
const myAdxLength = input.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxThreshold = input.number('ADX Threshold', 15, { min: 0, max: 100 });

const mySessionStartHour = input.number('Session Start Hour', 7, { min: 0, max: 23 });
const mySessionEndHour = input.number('Session End Hour', 20, { min: 0, max: 23 });

const myEmaFast = ema(close, myFastLength);
const myEmaSlow = ema(close, mySlowLength);
const myAdxObject = indicators.adx(myAdxLength);

// Session filter: Pine's "23456" day-of-week codes (1=Sun..7=Sat) stand for
// Monday through Friday. ISO dayOfWeek used by time_of() is 1=Mon..7=Sun,
// so Monday-Friday maps to ISO values 1-5.
const myIsSession = for_every(time, _t => {
	const myParsedTime = time_of(_t);
	const myIsWeekday = myParsedTime.dayOfWeek >= 1 && myParsedTime.dayOfWeek <= 5;
	const myIsInHourRange = myParsedTime.hours >= mySessionStartHour && myParsedTime.hours < mySessionEndHour;
	return myIsWeekday && myIsInHourRange;
});

// Crossover / crossunder detection, equivalent to ta.crossover / ta.crossunder
const myCrossoverRaw = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _idx) => {
	if (_idx === 0) return false;
	return _fast > _slow && myEmaFast[_idx - 1] <= myEmaSlow[_idx - 1];
});

const myCrossunderRaw = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _idx) => {
	if (_idx === 0) return false;
	return _fast < _slow && myEmaFast[_idx - 1] >= myEmaSlow[_idx - 1];
});

const myBuySignal = for_every(myCrossoverRaw, myAdxObject.adx, myIsSession, (_cross, _adx, _sess) => {
	return Boolean(_cross && _adx > myAdxThreshold && _sess);
});

const mySellSignal = for_every(myCrossunderRaw, myAdxObject.adx, myIsSession, (_cross, _adx, _sess) => {
	return Boolean(_cross && _adx > myAdxThreshold && _sess);
});

register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');

paint(myEmaFast, { name: 'EMA Fast', color: '#26A69A', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#EF5350', thickness: 2 });

const myBuyMarks = for_every(myBuySignal, low, (_sig, _low) => _sig ? _low : null);
const mySellMarks = for_every(mySellSignal, high, (_sig, _high) => _sig ? _high : null);

paint(myBuyMarks, { name: 'Buy Marker', color: '#26A69A', style: 'labels_below' });
paint(mySellMarks, { name: 'Sell Marker', color: '#EF5350', style: 'labels_above' });