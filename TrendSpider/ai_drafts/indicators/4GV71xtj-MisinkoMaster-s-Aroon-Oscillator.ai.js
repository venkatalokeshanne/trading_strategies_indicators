describe_indicator('MisinkoMaster Special Aroon Oscillator', 'lower');

// NOTE: Pine's plotcandle(force_overlay=true) which overlays colored
// candles on the price chart is approximated here using color_candles(),
// which is the closest equivalent available in this engine.
// NOTE: Pine's "fill" uses a dynamic color driven by `trend`, which can
// differ from the sign of mao only in rare edge persistence cases
// (mao == 0 keeps previous trend). We approximate the fill using
// color_cloud() comparing mao against zero, which matches almost always.

const mySrcChoice = input.select('Source', 'close', constants.price_source_options);
const mySrc = market[mySrcChoice];

const myLength = input.number('Length', 28, { min: 2, max: 500 });
const mySmooth = input.number('Smooth', 14, { min: 2, max: 500 });

// Replicates: ta.ema(src, smooth) * (1 - 2/(1+smooth)) + src * 2/(1+smooth)
const myEmaOfSrc = ema(mySrc, mySmooth);
const myFactorA = 1 - 2 / (1 + mySmooth);
const myFactorB = 2 / (1 + mySmooth);
const mySource = add(mult(myEmaOfSrc, myFactorA), mult(mySrc, myFactorB));

// Replicates ta.highestbars / ta.lowestbars: offset (0 = current bar,
// negative = bars back) of the highest/lowest value within the window.
// Ties resolve to the most recent occurrence, matching Pine's behavior.
const myWindowSize = myLength + 1;

const myHighestOffset = sliding_window_function(mySource, myWindowSize, _vals => {
	let myMaxVal = -Infinity;
	let myMaxIdx = 0;
	for (let myI = 0; myI < _vals.length; myI += 1) {
		if (_vals[myI] >= myMaxVal) {
			myMaxVal = _vals[myI];
			myMaxIdx = myI;
		}
	}
	return myMaxIdx - (_vals.length - 1);
});

const myLowestOffset = sliding_window_function(mySource, myWindowSize, _vals => {
	let myMinVal = Infinity;
	let myMinIdx = 0;
	for (let myI = 0; myI < _vals.length; myI += 1) {
		if (_vals[myI] <= myMinVal) {
			myMinVal = _vals[myI];
			myMinIdx = myI;
		}
	}
	return myMinIdx - (_vals.length - 1);
});

const myUp = mult(div(add(myHighestOffset, myLength), myLength), 100);
const myDown = mult(div(add(myLowestOffset, myLength), myLength), 100);
const myMao = sub(myUp, myDown);

// Replicates the persistent `trend` variable: stays unchanged while mao == 0
const myTrend = for_every(myMao, (_m, _prevTrend) => {
	const myPrev = _prevTrend == null ? 0 : _prevTrend;
	if (_m > 0) return 1;
	if (_m < 0) return -1;
	return myPrev;
});

const myNeutralColor = 'rgb(68, 75, 64)';
const myGreenColor = 'rgb(18, 112, 5)';
const myRedColor = 'rgb(163, 4, 4)';

const myLineColor = for_every(myTrend, myMao, (_t, _m) => {
	if (_m === 0) return myNeutralColor;
	return _t === 1 ? myGreenColor : myRedColor;
});

const myCandleColor = for_every(myTrend, myMao, (_t, _m) => {
	if (_m === 0) return myNeutralColor;
	return _t === 1 ? myGreenColor : myRedColor;
});

const myZeroLine = series_of(0);

paint(myMao, { name: 'SpecialAroonOscillator', color: myLineColor, thickness: 3, style: 'column' });
paint(myZeroLine, { name: 'NeutralValue', color: 'rgba(68, 75, 64, 0.4)', thickness: 2 });
paint(horizontal_line(100), { name: 'MaxValue', color: 'rgba(18, 112, 5, 0.4)', thickness: 2 });
paint(horizontal_line(-100), { name: 'MinValue', color: 'rgba(163, 4, 4, 0.4)', thickness: 2 });

color_cloud(myMao, myZeroLine, 'rgba(4, 243, 112, 0.3)', 'rgba(241, 20, 20, 0.3)', 'BullishFill', 'BearishFill', 0.3);

color_candles(myCandleColor);

// Replicates ta.crossover(mao, 0) and ta.crossunder(mao, 0)
const myMaoShifted = shift(myMao, 1);
const myBullishCross = for_every(myMao, myMaoShifted, (_m, _pm) => _m > 0 && _pm <= 0);
const myBearishCross = for_every(myMao, myMaoShifted, (_m, _pm) => _m < 0 && _pm >= 0);

register_signal(myBullishCross, 'Bullish Zero Cross');
register_signal(myBearishCross, 'Bearish Zero Cross');
register_signal(for_every(myTrend, _t => _t === 1), 'Bullish Trend');
register_signal(for_every(myTrend, _t => _t === -1), 'Bearish Trend');