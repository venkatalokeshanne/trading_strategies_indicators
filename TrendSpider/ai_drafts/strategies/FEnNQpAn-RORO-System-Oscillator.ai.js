describe_indicator('RORO System Oscillator', 'lower');

// Inputs
const myAlmaLength = input.number('Alma Length', 24, { min: 1, max: 500 });
const myAlmaOffset = input.number('Alma Offset', 0.85, { min: 0, max: 1 });
const myAlmaSigma = input.number('Alma Sigma', 6, { min: 1, max: 50 });
const myVwmaLength = input.number('VWMA Length', 120, { min: 1, max: 1000 });
const myRocLength = input.number('ROC Length', 14, { min: 1, max: 500 });

const myScalingFactor = 20;

// Core calculations
const myAlma = alma(close, myAlmaLength, myAlmaOffset, myAlmaSigma);
const myVwma = vwma(close, myVwmaLength);

// Trend = normalize((Alma - VWMA) / VWMA * ScalingFactor)
const myTrendRaw = sub(myAlma, myVwma);
const myTrendNorm = div(myTrendRaw, myVwma);
const myTrendScaled = mult(myTrendNorm, myScalingFactor);
const myTrend = for_every(myTrendScaled, _x => _x / (1 + Math.abs(_x)));

// Momentum = normalize(ROC / stdev(ROC, 50))
const myRoc = roc(close, myRocLength);
const myRocVol = stdev(myRoc, 50);
const myMomentumRaw = div(myRoc, myRocVol);
const myMomentum = for_every(myMomentumRaw, _x => _x / (1 + Math.abs(_x)));

// Score, Osc
const myScore = for_every(myTrend, myMomentum, (_t, _m) => (_t * 0.6) + (_m * 0.4));
const myOsc = for_every(myScore, _s => Math.max(Math.min(_s * 100, 100), -100));

// Smoothed oscillator using same Alma parameters
const myOscSmooth = alma(myOsc, myAlmaLength, myAlmaOffset, myAlmaSigma);

// Conditions
const myOscPrev = shift(myOscSmooth, 1);
const myLongCondition = for_every(myOscSmooth, myOscPrev, (_c, _p) => _c > 30 && _p <= 30);
const myExitCondition = for_every(myOscSmooth, _c => _c < -10);
const myShortCondition = for_every(myOscSmooth, myOscPrev, (_c, _p) => _c < -30 && _p >= -30);
const myExitShort = for_every(myOscSmooth, _c => _c > 0);

// Color the oscillator line aqua/fuchsia depending on sign
const myOscColor = for_every(myOscSmooth, _c => _c > 0 ? '#00E5FF' : '#FF00FF');

paint(myOscSmooth, { name: 'Oscillator', color: myOscColor, thickness: 2 });

paint(horizontal_line(30), { name: 'RiskOn', color: 'green', style: 'dotted' });
paint(horizontal_line(0), { name: 'Neutral', color: 'gray', style: 'dotted' });
paint(horizontal_line(-30), { name: 'RiskOff', color: 'red', style: 'dotted' });

// Signals for scanning / strategy use
register_signal(myLongCondition, 'Long Entry');
register_signal(myExitCondition, 'Long Exit');
register_signal(myShortCondition, 'Short Entry');
register_signal(myExitShort, 'Short Exit');