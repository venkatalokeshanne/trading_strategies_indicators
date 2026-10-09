describe_indicator('Author Strategy HA Signals On Regular Candles', 'price');

// NOTE: TrendSpider custom indicators cannot place real orders or track an
// actual strategy position (entries/exits/pyramiding). This script
// reproduces the Pine Script signal logic (Heikin Ashi based Chandelier
// Exit + ZL SMMA cross) as closely as possible and exposes the buy/sell
// and MA-exit conditions as signals you can use in Scanners/Alerts.
// Position-based exit tracking (strategy.position_size checks) is
// approximated using the raw cross condition only.

const myAtrPeriod = input.number('Chandelier ATR Period', 1, { min: 1, max: 200 });
const myAtrMultiplier = input.number('Chandelier ATR Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });
const mySmmaLength = input.number('ZLSMA Length', 50, { min: 1, max: 500 });
const myShowLabels = input.boolean('Show Buy/Sell Labels', true);
const myShowZlSmma = input.boolean('Show ZL SMMA', true);

// === Heikin Ashi reconstruction from the current chart candles ===
const myHaCloseArr = ohlc4;
const myHaOpenState = for_every(open, close, myHaCloseArr, (_o, _c, _hc, _prev, _i) => {
	const myPrevOpen = _prev ? _prev.open : (_o + _c) / 2;
	const myPrevClose = _prev ? _prev.close : _hc;
	const myOpen = (_i === 0) ? (_o + _c) / 2 : (myPrevOpen + myPrevClose) / 2;
	return { open: myOpen, close: _hc };
});
const myHaOpenArr = myHaOpenState.map(_d => _d.open);
const myHaHighArr = max_of(high, max_of(myHaOpenArr, myHaCloseArr));
const myHaLowArr = min_of(low, min_of(myHaOpenArr, myHaCloseArr));

// === Chandelier Exit computed off the HA data ===
const myAtrHA = atr(myHaHighArr, myHaLowArr, myHaCloseArr, myAtrPeriod);
const myLongStopRaw = sub(highest(myHaHighArr, myAtrPeriod), mult(myAtrHA, myAtrMultiplier));
const myShortStopRaw = add(lowest(myHaLowArr, myAtrPeriod), mult(myAtrHA, myAtrMultiplier));
const myPrevHaClose = shift(myHaCloseArr, 1);

// Fixed: warm-up candles (ATR/highest/lowest window) can yield null raw
// stop values. The original code did not guard against that, so the
// chandelier state object itself became null and later ".dir" access
// crashed. Now we fall back to the previous state (or sane defaults)
// whenever a raw input is not a valid number yet.
const myChandelierState = for_every(myPrevHaClose, myHaCloseArr, myLongStopRaw, myShortStopRaw, (_prevClose, _close, _rawLong, _rawShort, _prev) => {
	const myDefaultState = { longStop: _close, shortStop: _close, dir: 1 };

	if (_rawLong === null || _rawLong === undefined || isNaN(_rawLong) ||
		_rawShort === null || _rawShort === undefined || isNaN(_rawShort) ||
		_prevClose === null || _prevClose === undefined) {
		return _prev ? _prev : myDefaultState;
	}

	const myPrevLongStop = _prev ? _prev.longStop : _rawLong;
	const myPrevShortStop = _prev ? _prev.shortStop : _rawShort;
	const myPrevDir = _prev ? _prev.dir : 1;

	const myLongStop = (_prevClose > myPrevLongStop) ? Math.max(_rawLong, myPrevLongStop) : _rawLong;
	const myShortStop = (_prevClose < myPrevShortStop) ? Math.min(_rawShort, myPrevShortStop) : _rawShort;

	let myDir;
	if (_close > myPrevShortStop) {
		myDir = 1;
	}
	else if (_close < myPrevLongStop) {
		myDir = -1;
	}
	else {
		myDir = myPrevDir;
	}

	return { longStop: myLongStop, shortStop: myShortStop, dir: myDir };
});

// Guarded against null state objects during the warm-up period.
const myDirArr = myChandelierState.map(_d => (_d ? _d.dir : null));
const myPrevDirArr = shift(myDirArr, 1);
const myBuySignal = for_every(myDirArr, myPrevDirArr, (_d, _pd) => (_d === 1 && _pd === -1));
const mySellSignal = for_every(myDirArr, myPrevDirArr, (_d, _pd) => (_d === -1 && _pd === 1));

// === ZL SMMA ===
const myLag = Math.max(1, Math.floor(mySmmaLength / 2));
const myZlSource = add(myHaCloseArr, sub(myHaCloseArr, shift(myHaCloseArr, myLag)));
const mySmaOfZl = sma(myZlSource, mySmmaLength);
const myZlSmmaArr = for_every(myZlSource, mySmaOfZl, (_src, _sma0, _prev) => {
	if (_prev === null || _prev === undefined) {
		return (_sma0 === undefined) ? null : _sma0;
	}
	return (_prev * (mySmmaLength - 1) + _src) / mySmmaLength;
});

// === Author logic: HA cross signals confirmed by HA close vs ZL SMMA ===
const myLongCondition = for_every(myBuySignal, myHaCloseArr, myZlSmmaArr, (_b, _hc, _z) => (_b && _hc > _z));
const myShortCondition = for_every(mySellSignal, myHaCloseArr, myZlSmmaArr, (_s, _hc, _z) => (_s && _hc < _z));

// Approximated MA-exit condition (position tracking not available)
const myExitLongCondition = for_every(myHaCloseArr, myZlSmmaArr, (_hc, _z) => (_hc < _z));
const myExitShortCondition = for_every(myHaCloseArr, myZlSmmaArr, (_hc, _z) => (_hc > _z));

// === Plots ===
paint(myShowZlSmma ? myZlSmmaArr : series_of(null), { name: 'ZL SMMA', color: 'white', thickness: 2 });

const myBuyLabelSeries = for_every(myBuySignal, _b => (_b ? constants.icons.arrow_up : null));
const mySellLabelSeries = for_every(mySellSignal, _s => (_s ? constants.icons.arrow_down : null));

paint(myShowLabels ? myBuyLabelSeries : series_of(null), { name: 'Buy', style: 'labels_below', color: 'green' });
paint(myShowLabels ? mySellLabelSeries : series_of(null), { name: 'Sell', style: 'labels_above', color: 'red' });

// === Signals for Scanners/Alerts/Strategy Tester ===
register_signal(myBuySignal, 'HA Buy Signal');
register_signal(mySellSignal, 'HA Sell Signal');
register_signal(myLongCondition, 'Long Entry Condition');
register_signal(myShortCondition, 'Short Entry Condition');
register_signal(myExitLongCondition, 'Long Exit Condition');
register_signal(myExitShortCondition, 'Short Exit Condition');