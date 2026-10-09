describe_indicator('Kelly Breakout Bands (Pine conversion)', 'price');

// NOTE: This Custom JS API has no strategy/backtesting engine
// (no strategy.equity, strategy.wintrades, position sizing, etc).
// Kelly ratio position sizing, equity tracking, take profit/stop
// loss exits and strategy.cancel/entry calls from the original
// Pine strategy cannot be reproduced here. This indicator
// reproduces the band logic, cross/entry/cancel signal logic
// (the actual trading triggers), exposed via register_signal()
// so they can be used in scanners/alerts.

const myLengthTab = input.tab('Bands');
const myLength = myLengthTab.number('Length', 20, { min: 1, max: 500 });
const myMult = myLengthTab.number('Multiplier', 1.0, { min: 0.01, max: 50 });
const myUseExp = myLengthTab.boolean('Use Exponential MA', true);
const myBandsStyle = myLengthTab.select('Bands Style', 'Average True Range', ['Average True Range', 'True Range', 'Range']);
const myAtrLength = myLengthTab.number('ATR Length', 10, { min: 1, max: 500 });

// mintick approximation: Pine uses syminfo.mintick, we approximate
// using the smallest price increment implied by current.decimals.
const myMinTick = Math.pow(10, -current.decimals);

const mySrc = close;

const myMa = myUseExp ? ema(mySrc, myLength) : sma(mySrc, myLength);

// True range series, needed for both "True Range" and "Range" styles
const myTrueRange = atr(high, low, close, 1);
const myHighLowRange = sub(high, low);

let myRangeMa;
if (myBandsStyle === 'True Range') {
	myRangeMa = wildma(myTrueRange, myLength);
}
else if (myBandsStyle === 'Average True Range') {
	myRangeMa = atr(high, low, close, myAtrLength);
}
else {
	myRangeMa = wildma(myHighLowRange, myLength);
}

const myUpper = add(myMa, mult(myRangeMa, myMult));
const myLower = sub(myMa, mult(myRangeMa, myMult));

// crossover / crossunder of src vs bands
const myCrossUpper = for_every(mySrc, myUpper, (_s, _u, _p, _i) => {
	if (_i === 0) return false;
	return _s > _u && mySrc[_i - 1] <= myUpper[_i - 1];
});

const myCrossLower = for_every(mySrc, myLower, (_s, _l, _p, _i) => {
	if (_i === 0) return false;
	return _s < _l && mySrc[_i - 1] >= myLower[_i - 1];
});

// bprice / sprice: persist last breakout trigger price
const myBPrice = for_every(myCrossUpper, high, (_cu, _h, _prev, _i) => {
	if (_cu) return _h + myMinTick;
	return _i === 0 ? 0 : _prev;
});

const mySPrice = for_every(myCrossLower, low, (_cl, _l, _prev, _i) => {
	if (_cl) return _l - myMinTick;
	return _i === 0 ? 0 : _prev;
});

// crossBcond / crossScond: sticky flags, latched true on cross, persist otherwise
const myCrossBcond = for_every(myCrossUpper, (_cu, _prev, _i) => {
	if (_cu) return true;
	return _i === 0 ? false : _prev;
});

const myCrossScond = for_every(myCrossLower, (_cl, _prev, _i) => {
	if (_cl) return true;
	return _i === 0 ? false : _prev;
});

// cancel conditions
const myCancelBcond = for_every(myCrossBcond, mySrc, myMa, high, myBPrice, (_cb, _s, _m, _h, _bp) => {
	return _cb && (_s < _m || _h >= _bp);
});

const myCancelScond = for_every(myCrossScond, mySrc, myMa, low, mySPrice, (_cs, _s, _m, _l, _sp) => {
	return _cs && (_s > _m || _l <= _sp);
});

// Paint the bands and midline
paint(myMa, { name: 'MA', color: '#9c7bd4', thickness: 1, style: 'line' });

fill(
	paint(myUpper, { name: 'Upper', color: '#4DA3FF', thickness: 1, style: 'line' }),
	paint(myLower, { name: 'Lower', color: '#FFA64D', thickness: 1, style: 'line' }),
	'#4DA3FF',
	0.05
);

// Register the actual trading triggers for use in scanners/alerts
register_signal(myCrossUpper, 'Long Entry Signal');
register_signal(myCrossLower, 'Short Entry Signal');
register_signal(myCancelBcond, 'Long Cancel Signal');
register_signal(myCancelScond, 'Short Cancel Signal');