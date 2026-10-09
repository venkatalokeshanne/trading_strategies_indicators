describe_indicator('Mactv K Trend Keltner K160 2.5', 'price');

const myEmaLen = input.number('Midline EMA (exit rail)', 160, { min: 1, max: 1000 });
const myAtrLen = input.number('ATR length', 14, { min: 1, max: 500 });
const myMult = input.number('ATR multiplier (entry band)', 2.5, { min: 0.1, max: 20, step: 0.1 });
const myShowLower = input.boolean('Show lower band (cosmetic)', false);
const myShowState = input.boolean('Tint background while long', true);

const myMid = ema(close, myEmaLen);
const myAtr = atr(high, low, close, myAtrLen);
const myUpper = add(myMid, mult(myAtr, myMult));
const myLower = sub(myMid, mult(myAtr, myMult));

// State machine replicating the Pine "var int pos" logic.
// pos starts at 0 (flat); switches to 1 on a close above the
// upper band, and back to 0 on a close below the midline (EMA).
const myPosSeries = for_every(close, myUpper, myMid, (_close, _upper, _mid, _prevPos, _index) => {
	const myPrevPos = _prevPos === null || _prevPos === undefined ? 0 : _prevPos;
	if (myPrevPos === 0 && _close > _upper) {
		return 1;
	}
	if (myPrevPos === 1 && _close < _mid) {
		return 0;
	}
	return myPrevPos;
});

// Entry/exit flags are computed from the previous bar's state vs current state,
// mirroring Pine's longEntry/longExit which are evaluated using "pos" before update.
const myLongEntry = for_every(close, myUpper, myPosSeries, (_close, _upper, _pos, _prev, _index) => {
	const myPrevPos = _index > 0 ? (myPosSeries[_index - 1] === undefined ? 0 : myPosSeries[_index - 1]) : 0;
	return myPrevPos === 0 && _close > _upper;
});

const myLongExit = for_every(close, myMid, myPosSeries, (_close, _mid, _pos, _prev, _index) => {
	const myPrevPos = _index > 0 ? (myPosSeries[_index - 1] === undefined ? 0 : myPosSeries[_index - 1]) : 0;
	return myPrevPos === 1 && _close < _mid;
});

// Background tint: colors candles teal while in a long position (if enabled)
const myBgColors = for_every(myPosSeries, myLongEntry, (_pos, _entry) => {
	return (myShowState && _pos === 1) ? 'rgba(45,212,191,0.12)' : null;
});
color_candles(myBgColors);

const myMidPainted = paint(myMid, { name: 'ExitRail', color: '#F0B90B', thickness: 2 });
const myUpperPainted = paint(myUpper, { name: 'EntryBand', color: '#2DD4BF', thickness: 1 });
paint(myShowLower ? myLower : constants.empty_series, { name: 'LowerBand', color: 'rgba(45,212,191,0.4)', thickness: 1 });

fill(myUpperPainted, myMidPainted, '#2DD4BF', 0.06, 'ChannelFill');

const myEntryMarks = for_every(myLongEntry, low, (_entry, _low) => _entry ? _low : null);
const myExitMarks = for_every(myLongExit, high, (_exit, _high) => _exit ? _high : null);

paint(myEntryMarks, { name: 'Entry', style: 'labels_below', color: '#2EBD85' });
paint(myExitMarks, { name: 'Exit', style: 'labels_above', color: '#F6465D' });

// Timeframe warning overlay, replicating the Pine table warning for non-240 (4h) charts
const myIsWrongTimeframe = current.resolution !== '240';
paint_overlay('KTrendTimeframeWarning', { position: 'top_right' }, {
	rows: myIsWrongTimeframe ? [{
		cells: [{
			text: 'K-Trend is designed for 4h - this chart is ' + String(current.resolution),
			color: 'orange'
		}]
	}] : []
});

register_signal(myLongEntry, 'K Trend Buy');
register_signal(myLongExit, 'K Trend Exit');
register_signal(myPosSeries.map(_p => _p === 1), 'K Trend In Position');