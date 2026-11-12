<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('SmartVol SuperTrend | Alpha Scope');

// Inputs
const mySourceOption = input.select('Source', 'close', constants.price_source_options);
const mySrc = market[mySourceOption];
const myEmaLen = input.number('EMA Length', 5, { min: 1, max: 500 });
const myVwsdLen = input.number('VWSD Length', 30, { min: 1, max: 500 });
const myFactor = input.number('Factor', 1.8, { min: 0.1, max: 10 });

// EMA
const myEma = ema(mySrc, myEmaLen);

// Volume weighted standard deviation function
// This function computes a volume-weighted standard deviation by calculating
// the weighted variance and then taking its square root
const volumesd = (series, length) => {
  const myMean = vwma(series, length);
  
  // Calculate the sum of squared differences weighted by volume
  const mySumSq = for_every(series, volume, myMean, (_s, _v, _m, _prev, i) => {
    let myAccumulator = 0;
    for (let j = 0; j < length && i - j >= 0; j++) {
      const diff = series[i - j] - _m;
      myAccumulator += volume[i - j] * Math.pow(diff, 2);
    }
    return myAccumulator;
  });
  
  const myVolSum = sum(volume, length);
  const myVariance = div(mySumSq, myVolSum);
  
  return for_every(myVariance, _v => Math.sqrt(_v));
};

// SuperTrend calculation
const myVwsd = volumesd(mySrc, myVwsdLen);
const myUpperBandRaw = add(myEma, mult(myVwsd, myFactor));
const myLowerBandRaw = sub(myEma, mult(myVwsd, myFactor));

const myResult = for_every(myUpperBandRaw, myLowerBandRaw, close, (_upper, _lower, _close, _prev, i) => {
  if (i === 0) {
    return {
      upperBand: _upper,
      lowerBand: _lower,
      dir: 1,
      superTrend: _upper
    };
  }
  
  const prevResult = _prev || { upperBand: _upper, lowerBand: _lower, dir: 1, superTrend: _upper };
  
  let lowerBand = _lower > prevResult.lowerBand || close[i - 1] < prevResult.lowerBand ? _lower : prevResult.lowerBand;
  let upperBand = _upper < prevResult.upperBand || close[i - 1] > prevResult.upperBand ? _upper : prevResult.upperBand;
  
  let dir;
  if (prevResult.superTrend === prevResult.upperBand) {
    dir = _close > upperBand ? -1 : 1;
  } else {
    dir = _close < lowerBand ? 1 : -1;
  }
  
  const superTrend = dir === -1 ? lowerBand : upperBand;
  
  return { upperBand, lowerBand, dir, superTrend };
});

const mySt = for_every(myResult, _r => _r ? _r.superTrend : null);
const myDir = for_every(myResult, _r => _r ? _r.dir : null);

// Signals
const myLong = for_every(myDir, _d => _d < 0);
const myShort = for_every(myDir, _d => _d > 0);

const myOquant = for_every(myLong, myShort, (_long, _short, _prev) => {
  const prevValue = _prev || 0;
  if (_long && !_short) return 1;
  if (_short) return -1;
  return prevValue;
});

// Colors
const myOquantGreen = '#1fd325';
const myOquantPurple = '#bc08db';
const myColors = for_every(myOquant, _o => _o === 1 ? myOquantGreen : _o === -1 ? myOquantPurple : null);

// Plotting
const myStUp = for_every(myOquant, mySt, (_o, _st) => _o === 1 ? _st : null);
const myStDown = for_every(myOquant, mySt, (_o, _st) => _o === -1 ? _st : null);

const myPlotStUp = paint(myStUp, { name: 'Up direction', color: myOquantGreen, style: 'line' });
const myPlotStDown = paint(myStDown, { name: 'Down direction', color: myOquantPurple, style: 'line' });
const myPlotOc2 = paint(oc2, { name: 'Plot oc2', color: myColors, style: 'line' });

fill(myPlotOc2, myPlotStUp, myOquantGreen, 0.2);
fill(myPlotOc2, myPlotStDown, myOquantPurple, 0.2);

color_candles(myColors);

// Signals for alerts - these register binary signals for use in scanners and alerts
register_signal(myOquant.map((v, i) => myOquant[i - 1] < 0 && v > 0), 'SmartVol SuperTrend Bullish');
register_signal(myOquant.map((v, i) => myOquant[i - 1] > 0 && v < 0), 'SmartVol SuperTrend Bearish');
</code>