describe_indicator('EMA Cross Optimized', 'price');

const myFastLength = input.number('Fast EMA', 9, { min: 1, max: 500 });
const mySlowLength = input.number('Slow EMA', 21, { min: 1, max: 500 });

const myEmaFast = ema(close, myFastLength);
const myEmaSlow = ema(close, mySlowLength);

// Crossover / crossunder conditions, replicating ta.crossover / ta.crossunder
const myBullCross = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast > _slow && myEmaFast[_i - 1] <= myEmaSlow[_i - 1];
});

const myBearCross = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast < _slow && myEmaFast[_i - 1] >= myEmaSlow[_i - 1];
});

// Slow EMA turning conditions (backup exit logic from Pine script)
const myEmaTurningDown = for_every(myEmaSlow, (_slow, _prev, _i) => {
	if (_i === 0) return false;
	return _slow < myEmaSlow[_i - 1];
});

const myEmaTurningUp = for_every(myEmaSlow, (_slow, _prev, _i) => {
	if (_i === 0) return false;
	return _slow > myEmaSlow[_i - 1];
});

// Exit conditions as defined in Pine (same as bear/bull cross, kept separate for clarity)
const myExitLong = myBearCross;
const myExitShort = myBullCross;

paint(myEmaFast, { name: 'Fast EMA', color: '#2962FF', thickness: 2 });
paint(myEmaSlow, { name: 'Slow EMA', color: '#FF9800', thickness: 2 });

const myBullMarks = for_every(myBullCross, low, (_c, _l) => _c ? _l : null);
const myBearMarks = for_every(myBearCross, high, (_c, _h) => _c ? _h : null);

paint(myBullMarks, { name: 'Bull Cross', style: 'labels_below', color: 'green', thickness: 3 });
paint(myBearMarks, { name: 'Bear Cross', style: 'labels_above', color: 'red', thickness: 3 });

// Signals for scanner/alerts/strategy use
register_signal(myBullCross, 'Bull Cross Long Entry');
register_signal(myBearCross, 'Bear Cross Short Entry');
register_signal(myExitLong, 'Exit Long Fast EMA Crossunder');
register_signal(myExitShort, 'Exit Short Fast EMA Crossover');
register_signal(myEmaTurningDown, 'Slow EMA Turning Down Backup Exit');
register_signal(myEmaTurningUp, 'Slow EMA Turning Up Backup Exit');