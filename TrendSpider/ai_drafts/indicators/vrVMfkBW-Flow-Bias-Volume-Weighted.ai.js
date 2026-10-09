describe_indicator('Flow Bias VWAP Cloud', 'price');

// =====================================================
// INPUTS
// =====================================================
const myTab = input.tab('Settings');
const mySmoothLen = myTab.number('Smoothing Length', 5, { min: 1, max: 200 });
const myDirectionLen = myTab.number('Direction Sensitivity', 3, { min: 1, max: 200 });
const myNeutralATR = myTab.number('Neutral Zone (ATR mult)', 0.03, { min: 0, max: 5, step: 0.01 });

// =====================================================
// SESSION ANCHORED VWAP OF HIGH AND LOW
// Pine's ta.vwap() resets at the start of each session (day).
// The built-in vwap() call only supports one static start index per call,
// so a session-anchored VWAP must be computed manually using cumulative
// sums that reset whenever a new session begins. This is plain arithmetic,
// not a call to an indicator function, so looping is safe here.
// =====================================================
const mySessionAtIndex = time.map(_t => bar_at(_t).session);

const myVwapHigh = series_of(null);
const myVwapLow = series_of(null);

let mySumHV = 0;
let mySumLV = 0;
let mySumV = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewSession = myIndex === 0 || mySessionAtIndex[myIndex] !== mySessionAtIndex[myIndex - 1];

	if (myNewSession) {
		mySumHV = 0;
		mySumLV = 0;
		mySumV = 0;
	}

	mySumHV += high[myIndex] * volume[myIndex];
	mySumLV += low[myIndex] * volume[myIndex];
	mySumV += volume[myIndex];

	myVwapHigh[myIndex] = mySumV > 0 ? mySumHV / mySumV : high[myIndex];
	myVwapLow[myIndex] = mySumV > 0 ? mySumLV / mySumV : low[myIndex];
}

// =====================================================
// VOLUME WEIGHTED SMOOTHING (ta.vwma equivalent)
// =====================================================
const mySmoothHigh = vwma(myVwapHigh, mySmoothLen);
const mySmoothLow = vwma(myVwapLow, mySmoothLen);

const myCloudMid = div(add(mySmoothHigh, mySmoothLow), 2);

// =====================================================
// DIRECTION
// =====================================================
const mySlope = sub(myCloudMid, shift(myCloudMid, myDirectionLen));
const myAtr = atr(high, low, close, 14);
const myNeutralZone = mult(myAtr, myNeutralATR);

const myBullish = for_every(mySlope, myNeutralZone, (_s, _n) => _s > _n);
const myBearish = for_every(mySlope, myNeutralZone, (_s, _n) => _s < -_n);

// =====================================================
// COLORS
// Pine's cloud uses 3 colors (blue/red/gray) depending on state.
// The platform's fill()/color_cloud() only support a single static
// color or a 2-state comparison-based color, not a 3-state per-candle
// condition. As a close approximation, the upper/lower boundary lines
// are colored dynamically (blue/red/gray) to reflect the state, and the
// cloud itself is filled with a neutral gray, since fill() cannot take
// a dynamic/conditional color series.
// =====================================================
const myLineColor = for_every(myBullish, myBearish, (_bull, _bear) => _bull ? 'rgba(33,150,243,0.45)' : (_bear ? 'rgba(239,83,80,0.45)' : 'rgba(158,158,158,0.45)'));

const myUpperPainted = paint(mySmoothHigh, { name: 'VWAP High', color: myLineColor, thickness: 2, style: 'line' });
const myLowerPainted = paint(mySmoothLow, { name: 'VWAP Low', color: myLineColor, thickness: 2, style: 'line' });

fill(myUpperPainted, myLowerPainted, 'gray', 0.15);

// =====================================================
// SIGNALS FOR SCANNERS, ALERTS AND STRATEGIES
// =====================================================
register_signal(myBullish, 'Flow Bias Bullish');
register_signal(myBearish, 'Flow Bias Bearish');