<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('DSS Blau with BB - V2', 'lower');

// This indicator is an experimental implementation based on the provided formula.
// It may not be an exact representation and should be used with caution.

const myFastLength = input.number('Fast Length', 10, { min: 1 });
const mySlowLength = input.number('Slow Length', 15, { min: 1 });
const mySmoothing = input.number('Smoothing', 5, { min: 1 });
const myHighestHigh = highest(high, myFastLength);
const myLowestLow = lowest(low, myFastLength);
const myCloseMinusLow = sub(close, myLowestLow);
const myHighMinusLow = sub(myHighestHigh, myLowestLow);
const myFirstSmoothNumerator = ema(myCloseMinusLow, mySlowLength);
const myFirstSmoothDenominator = ema(myHighMinusLow, mySlowLength);
const myDoubleSmoothNumerator = ema(myFirstSmoothNumerator, mySmoothing);
const myDoubleSmoothDenominator = ema(myFirstSmoothDenominator, mySmoothing);
const myDSS = mult(div(myDoubleSmoothNumerator, myDoubleSmoothDenominator), 100);
const mySignalLine = ema(myDSS, mySmoothing);

// Add Bollinger Bands around the signal line
const myBBLength = input.number('BB Length', 20, { min: 1 });
const myBBMultiplier = input.number('BB Multiplier', 1, { min: 0.1, max: 5, step: 0.1 });
const myBBMid = ema(myDSS, myBBLength);
const myBBDev = mult(stdev(myDSS, myBBLength), myBBMultiplier);
const myBBUpper = add(myBBMid, myBBDev);
const myBBLower = sub(myBBMid, myBBDev);

// User-configurable colors
const myBBColor = input.color('BB Color', '#555555');
const myFillColor = input.color('BB Fill Color', '#eeeeee');
const myDSSAboveColor = input.color('DSS Above Color', 'white');
const myDSSBelowColor = input.color('DSS Below Color', 'yellow');

const myBBUpperPainted = paint(myBBUpper, { color: myBBColor, name: 'BB Upper', style: 'line' });
const myBBLowerPainted = paint(myBBLower, { color: myBBColor, name: 'BB Lower', style: 'line' });
//const myBBMidPainted = paint(myBBMid, { color: '#888888', name: 'BB Mid', style: 'line' });

// Create a dynamic color series for the signal line
const mySignalColor = for_every(mySignalLine, myDSS, (_signal, _dss) => 
    _signal > _dss ? myDSSAboveColor : myDSSBelowColor
);

paint(myDSS, { color: mySignalColor, name: 'DSS' });

// Paint the signal line with dynamic color
paint(mySignalLine, { color: mySignalColor, name: 'Signal' });

fill(myBBUpperPainted, myBBLowerPainted, myFillColor, 0.3);
</code>