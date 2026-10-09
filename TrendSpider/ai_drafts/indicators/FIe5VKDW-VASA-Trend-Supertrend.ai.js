describe_indicator('VASA Trend (Supertrend)', 'price');

// ---------- Inputs ----------
const trendTab = input.tab('Trend');
const myAtrLength = trendTab.number('ATR Length', 10, { min: 1, max: 200 });
const myAtrMultiplier = trendTab.number('ATR Multiplier', 3.0, { min: 0.5, max: 20, step: 0.1 });

const styleTab = input.tab('Style');
const myShowFlips = styleTab.boolean('Show Flip Markers', true);
const myShowFill = styleTab.boolean('Shade Trend Channel', true);

// ---------- Supertrend ----------
// Built-in supertrend() returns the trend line series itself (price value
// which the trend currently references). Direction is derived by comparing
// Close to this line: Close above line means up-trend (equivalent to Pine's
// dir < 0), Close below line means down-trend.
const mySupertrendLine = supertrend(myAtrLength, myAtrMultiplier, false);
const myIsUp = for_every(close, mySupertrendLine, (_c, _st) => _c > _st);

// Default colors matching the Pine script's up/down colours
const myUpColor = '#15803d';
const myDownColor = '#b91c1c';

const myLineColor = for_every(myIsUp, _up => _up ? myUpColor : myDownColor);

// ---------- Plots ----------
const myStPainted = paint(mySupertrendLine, { name: 'VASATrend', color: myLineColor, thickness: 2 });
const myClosePainted = paint(close, { name: 'CloseHidden', hidden: true });

// Shade trend channel between Close and the trend line
if (myShowFill) {
	fill(myClosePainted, myStPainted, myUpColor, 0.1);
}
else {
	fill(myClosePainted, myStPainted, myUpColor, 0);
}

// ---------- Confirmed flips (non-repainting) ----------
// Since historical bars are always "confirmed" in this engine (no live
// repainting bar concept exposed), flip detection on closed data is
// equivalent to Pine's barstate.isconfirmed gating for historical bars.
const myFlipUp = for_every(myIsUp, (_up, _prev, _i) => _i > 0 ? (_up && !myIsUp[_i - 1]) : false);
const myFlipDown = for_every(myIsUp, (_up, _prev, _i) => _i > 0 ? (!_up && myIsUp[_i - 1]) : false);

const myFlipUpMarks = myShowFlips ? for_every(myFlipUp, mySupertrendLine, (_f, _st) => _f ? _st : null) : constants.empty_series;
const myFlipDownMarks = myShowFlips ? for_every(myFlipDown, mySupertrendLine, (_f, _st) => _f ? _st : null) : constants.empty_series;

paint(myFlipUpMarks, { name: 'FlipUp', style: 'labels_below', color: myUpColor, thickness: 3 });
paint(myFlipDownMarks, { name: 'FlipDown', style: 'labels_above', color: myDownColor, thickness: 3 });

// ---------- Scanner / Alert / Strategy signals ----------
register_signal(myFlipUp, 'Trend Flipped Up');
register_signal(myFlipDown, 'Trend Flipped Down');
register_signal(myIsUp, 'Up Trend Active');