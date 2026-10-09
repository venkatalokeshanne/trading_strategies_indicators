describe_indicator('O.Insidebox Mapper', 'price');
// NOTE: Pine's box/line drawing primitives (box.new, line.new, box.set_top,
// line.set_xy1 etc.) do not exist in TrendSpider Custom JS API. The
// "Asian session range" is approximated here using a filled area built
// from the running high/low of the session (via a ladder-style fill),
// which reproduces the same high/low values as the Pine box, but is
// visually a filled band instead of a resizable rectangle object.
// Session time matching uses UTC calendar hours derived directly from the
// candle timestamp (since Pine's time() with timezone="UTC" is UTC-based),
// so the "Timezone" input from the original script is not reproduced as a
// generic input; it is fixed to UTC like the script's default.
const myShowBox = input.boolean('Show Session Range', true);
const myInsideColor = input.color('Inside Bar and Marker Color', '#FFFF00');
const myBoxColor = input.color('Session Range Box Color', '#2962FF');
const myShowMarker = input.boolean('Show Marker Below Bar', true);
// Shortened input names below to satisfy the platform's input name length limit.
const mySessionStartHour = input.number('Asian Start Hour UTC', 0, { min: 0, max: 23 });
const mySessionEndHour = input.number('Asian End Hour UTC', 8, { min: 0, max: 23 });

// Determine, for every candle, whether its UTC time falls inside the
// configured session window (session is assumed not to wrap midnight,
// matching the default "0000-0800" window).
const myUtcHour = time.map(_t => Math.floor((_t % 86400) / 3600));
const myInAsianRange = myUtcHour.map(_h => _h >= mySessionStartHour && _h < mySessionEndHour);

// Inside bar condition: current high/low fully contained within previous bar.
const myIsInsideBar = for_every(high, low, (_h, _l, _prev, _i) => {
	if (_i === 0) return false;
	return _h <= high[_i - 1] && _l >= low[_i - 1];
});

const myTargetCondition = for_every(myIsInsideBar, (_inside, _prev, _i) => _inside && myInAsianRange[_i]);

// Color candles that are inside bars within the Asian session.
const myCandleColors = for_every(myTargetCondition, _target => _target ? myInsideColor : null);
color_candles(myCandleColors);

// Marker below bar for target condition.
const myMarkerSeries = myTargetCondition.map(_target => (myShowMarker && _target) ? constants.icons.triangle_up : null);
paint(myMarkerSeries, { style: 'labels_below', color: myInsideColor, name: 'InsideBarMarker' });

// New session detection: current candle is in the session while the
// previous one was not.
const myIsNewSession = for_every(myInAsianRange.map(_v => _v), (_inRange, _prev, _i) => {
	if (_i === 0) return _inRange;
	return _inRange && !myInAsianRange[_i - 1];
});

// Build running Asian session high/low, resetting at each new session.
const myAsianHigh = series_of(null);
const myAsianLow = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myIsNewSession[myIndex]) {
		myAsianHigh[myIndex] = high[myIndex];
		myAsianLow[myIndex] = low[myIndex];
	}
	else if (myInAsianRange[myIndex]) {
		const myPrevHigh = myAsianHigh[myIndex - 1];
		const myPrevLow = myAsianLow[myIndex - 1];
		myAsianHigh[myIndex] = myPrevHigh === null || myPrevHigh === undefined ? high[myIndex] : Math.max(myPrevHigh, high[myIndex]);
		myAsianLow[myIndex] = myPrevLow === null || myPrevLow === undefined ? low[myIndex] : Math.min(myPrevLow, low[myIndex]);
	}
	else {
		myAsianHigh[myIndex] = null;
		myAsianLow[myIndex] = null;
	}
}

const myBoxHighFinal = myShowBox ? myAsianHigh : series_of(null);
const myBoxLowFinal = myShowBox ? myAsianLow : series_of(null);

fill(
	paint(myBoxHighFinal, { name: 'AsianHigh', style: 'ladder', color: myBoxColor }),
	paint(myBoxLowFinal, { name: 'AsianLow', style: 'ladder', color: myBoxColor }),
	myBoxColor,
	0.25
);

// Signals for scanning/alerting/backtesting.
register_signal(myTargetCondition, 'Inside Bar In Asian Session');
register_signal(myIsNewSession, 'New Asian Session Started');
register_signal(myInAsianRange, 'In Asian Session');