describe_indicator('TEWMA Trend Strength', 'lower');

// Inputs
const myLen = input.number('Length', 50, { min: 1, max: 500 });
const myMulti = input.number('Multiplier', 2, { min: 0.05, max: 10, step: 0.05 });
const myAtrLength = input.number('ATR Length', 40, { min: 1, max: 500 });
const mySmoothLen = input.number('Smoothing Length', 50, { min: 1, max: 500 });
const myUpper = input.number('Upper Level', 1, { min: -10, max: 10, step: 0.1 });
const myLower = input.number('Lower Level', -1, { min: -10, max: 10, step: 0.1 });

// Price source (defaults to Close, matching the Pine script's input.source(close))
const myPriceSource = input.select('Price source', 'close', constants.price_source_options);
const myPrice = market[myPriceSource];

// len2 = round(len * multi)
const myLen2 = Math.round(myLen * myMulti);

const myAtr = atr(high, low, close, myAtrLength);

// TEMA of WMA, computed for both lengths
const myWma1 = wma(myPrice, myLen);
const myTewma1 = indicators.tema(myWma1, myLen);

const myWma2 = wma(myPrice, myLen2);
const myTewma2 = indicators.tema(myWma2, myLen2);

// TEWMA = average of the two TEMAs
const myTewma = div(add(myTewma1, myTewma2), 2);

// strength = (close - TEWMA) / ATR
const myStrength = div(sub(close, myTewma), myAtr);

// smoothed = EMA of strength
const mySmoothed = ema(myStrength, mySmoothLen);

const myBullColor = '#3184E4';
const myBearColor = '#84039E';

const myStrengthColor = for_every(myStrength, _s => _s > 0 ? myBullColor : myBearColor);
const mySmoothedColor = for_every(mySmoothed, _s => _s > 0 ? myBullColor : myBearColor);

const myZeroLine = series_of(0);

const myStrengthLine = paint(myStrength, { name: 'Strength', color: myStrengthColor, thickness: 2 });
const myZeroLineStrength = paint(myZeroLine, { name: 'ZeroStrength', hidden: true });
fill(myStrengthLine, myZeroLineStrength, 'gray', 0.15);

const mySmoothedLine = paint(mySmoothed, { name: 'Smoothed', color: mySmoothedColor, thickness: 1 });
const myZeroLineSmoothed = paint(myZeroLine, { name: 'ZeroSmoothed', hidden: true });
fill(mySmoothedLine, myZeroLineSmoothed, 'gray', 0.15);

paint(horizontal_line(myUpper), { name: 'UpperLevel', color: 'silver', style: 'dotted' });
paint(horizontal_line(myLower), { name: 'LowerLevel', color: 'silver', style: 'dotted' });

// Signals for scanning/alerts/strategy
register_signal(for_every(myStrength, _s => _s > 0), 'Strength Bullish');
register_signal(for_every(myStrength, _s => _s < 0), 'Strength Bearish');
register_signal(for_every(mySmoothed, _s => _s > 0), 'Smoothed Bullish');
register_signal(for_every(mySmoothed, _s => _s < 0), 'Smoothed Bearish');
register_signal(for_every(myStrength, _s => _s > myUpper), 'Strength Above Upper');
register_signal(for_every(myStrength, _s => _s < myLower), 'Strength Below Lower');
register_signal(for_every(mySmoothed, _s => _s > myUpper), 'Smoothed Above Upper');
register_signal(for_every(mySmoothed, _s => _s < myLower), 'Smoothed Below Lower');