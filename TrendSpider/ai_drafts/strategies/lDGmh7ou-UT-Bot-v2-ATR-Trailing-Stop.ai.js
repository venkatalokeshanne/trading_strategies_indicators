describe_indicator('UT Bot v2 - ATR Trailing Stop', 'price');

// ---- Config ----
const myConfigTab = input.tab('Config');
const myMult = myConfigTab.number('Multiplier', 1, { min: 0.1, max: 50, step: 0.1 });
const myAtrLen = myConfigTab.number('ATR Period', 10, { min: 1, max: 500 });
const mySourceName = myConfigTab.select('Source', 'close', constants.price_source_options);

// ---- Backtesting Range ----
const myRangeTab = input.tab('Backtesting Range');
const myUseDateFilter = myRangeTab.boolean('Use Backtest Date Range', true);
const myStartDateText = myRangeTab.text('Start Date', '2020-01-01');
const myEndDateText = myRangeTab.text('End Date', '2030-01-01');

// ---- Display ----
const myDisplayTab = input.tab('Display');
const myShowSignals = myDisplayTab.boolean('Show Buy/Sell Signals', true);
const myColorBars = myDisplayTab.boolean('Color Bars by Trend', false);
const myShowTsl = myDisplayTab.boolean('Show Trailing Stop Line', true);

const mySource = market[mySourceName];

// ATR and stop loss distance
const myAtr = atr(high, low, close, myAtrLen);
const mySlValue = mult(myAtr, myMult);

const myPrevSource = shift(mySource, 1);

// Recursive ATR trailing stop line (replicates Pine's var tsl_price logic)
const myTslPrice = for_every(mySource, myPrevSource, mySlValue, (_s, _prevS, _slv, _prevValue, _idx) => {
	const myPrev = _idx === 0 ? 0 : (_prevValue === null || _prevValue === undefined ? 0 : _prevValue);

	if (_s > myPrev && _prevS > myPrev) {
		return Math.max(myPrev, _s - _slv);
	}
	else if (_s < myPrev && _prevS < myPrev) {
		return Math.min(myPrev, _s + _slv);
	}
	else if (_s > myPrev) {
		return _s - _slv;
	}
	else {
		return _s + _slv;
	}
});

const myPrevTsl = shift(myTslPrice, 1);

// Crossover/crossunder of source vs trailing stop line
const myBuySignal = for_every(mySource, myPrevSource, myTslPrice, myPrevTsl, (_s, _prevS, _tsl, _prevTsl) => {
	return _prevS <= _prevTsl && _s > _tsl;
});

const mySellSignal = for_every(mySource, myPrevSource, myTslPrice, myPrevTsl, (_s, _prevS, _tsl, _prevTsl) => {
	return _prevS >= _prevTsl && _s < _tsl;
});

// Date range filter, mirrors Pine's time >= start_time and time <= end_time
const myStartTimestamp = Date.parse(myStartDateText) / 1000;
const myEndTimestamp = Date.parse(myEndDateText) / 1000;

const myInDateRange = for_every(time, _t => {
	return !myUseDateFilter || (_t >= myStartTimestamp && _t <= myEndTimestamp);
});

// Trend color state (bull/bear), carried forward like Pine's tsl_color
const myTrendIsBull = for_every(myBuySignal, mySellSignal, (_buy, _sell, _prevValue, _idx) => {
	if (_idx === 0) {
		return true;
	}
	if (_sell) {
		return false;
	}
	if (_buy) {
		return true;
	}
	return _prevValue === null || _prevValue === undefined ? true : _prevValue;
});

const myTslColor = for_every(myTrendIsBull, _bull => _bull ? '#26A69A' : '#EF5350');

color_candles(myColorBars ? myTslColor : constants.empty_series);

paint(myShowTsl ? myTslPrice : constants.empty_series, { name: 'Trailing Stop', color: myTslColor, thickness: 2 });

const myBuyMarks = for_every(myBuySignal, close, (_buy, _c) => (_buy && myShowSignals) ? _c : null);
const mySellMarks = for_every(mySellSignal, close, (_sell, _c) => (_sell && myShowSignals) ? _c : null);

paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: 'red' });

// Strategy / scanner / alert signals (barstate.isconfirmed and date filter
// combined into the signal; "entry" style strategy actions aren't directly
// expressible here, so register_signal exposes buy/sell for scanners/alerts)
const myBuyInRange = for_every(myBuySignal, myInDateRange, (_buy, _inRange) => _buy && _inRange);
const mySellInRange = for_every(mySellSignal, myInDateRange, (_sell, _inRange) => _sell && _inRange);

register_signal(myBuySignal, 'UT Bot Buy');
register_signal(mySellSignal, 'UT Bot Sell');
register_signal(myBuyInRange, 'UT Bot Buy In Range');
register_signal(mySellInRange, 'UT Bot Sell In Range');