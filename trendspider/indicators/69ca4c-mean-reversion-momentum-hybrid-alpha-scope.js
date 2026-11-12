<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Mean Reversion & Momentum Hybrid | Alpha-Scope', 'lower');

//--- User Inputs ---
const mySource = input.select('Source', 'close', constants.price_source_options);
const myPrice = market[mySource];
const myBbLength = input.number('Bollinger Bands Length', 20, { min: 1 });
const myBbMult = input.number('Bollinger Bands Multiplier', 2.0, { min: 0.1 });
const myMinBbWidth = input.number('Minimum BB Width (% of Price)', 0.5, { min: 0.0 });

//--- Bollinger Bands Percentage User Inputs ---
const myLongThreshold = input.number('BB% Long Threshold (L)', 55, { min: 0, max: 100 });
const myShortThreshold = input.number('BB% Short Threshold (S)', 45, { min: 0, max: 100 });

//--- ATR RMA User Inputs ---
const myLookback = input.number('RMA length', 15, { min: 1 });
const myAtrLookback = input.number('ATR length', 20, { min: 1 });

//--- 75th 25th Percentile Momentum User Inputs ---
const myMomentumLength = input.number('Momentum Length', 25, { min: 1 });
const myMult75 = input.number('mult_75', 1.3, { min: 0.1 });
const myMult25 = input.number('mult_25', 1.3, { min: 0.1 });

//--- Coloring Inputs ---
const myUseBgColor = input.boolean('Use Background Color for Signals', false);

//--- CALCULATIONS ---

//--- Bollinger Bands Calculations ---
const myBbBasis = sma(close, myBbLength);
const myBbDev = mult(stdev(close, myBbLength), myBbMult);
const myBbUpper = add(myBbBasis, myBbDev);
const myBbLower = sub(myBbBasis, myBbDev);
const myBbWidth = mult(div(sub(myBbUpper, myBbLower), myBbBasis), 100);

//--- RMA + ATR for trend filter ---
const myRma = wildma(myPrice, myLookback);
const myAtr = atr(high, low, close, myAtrLookback);
const myLongFil = for_every(myPrice, myRma, myAtr, (_price, _rma, _atr) => _price > _rma + _atr);
const myShortFil = for_every(myPrice, myRma, myAtr, (_price, _rma, _atr) => _price < _rma - _atr);
const myScore = for_every(myLongFil, myShortFil, (_long, _short, _prev) => {
    if (_long && !_short) return 1;
    if (_short) return -1;
    return _prev || 0;
});

//--- 75th 25th Percentile Momentum Calculations ---
const myPercentile75 = sliding_window_function(myPrice, myMomentumLength, _window => {
    const mySorted = _window.slice().sort((a, b) => a - b);
    const myIndex = Math.floor(mySorted.length * 0.75);
    return mySorted[myIndex];
});

const myPercentile25 = sliding_window_function(myPrice, myMomentumLength, _window => {
    const mySorted = _window.slice().sort((a, b) => a - b);
    const myIndex = Math.floor(mySorted.length * 0.25);
    return mySorted[myIndex];
});

const myMult75Series = series_of(myMult75);
const myMult25Series = series_of(myMult25);

const myLongMomentum = for_every(close, myPercentile75, myAtr, myMult75Series, (_close, _p75, _atr, _mult75) => 
    _close > _p75 + _mult75 * _atr);

const myShortMomentum = for_every(close, myPercentile25, myAtr, myMult25Series, (_close, _p25, _atr, _mult25) => 
    _close < _p25 - _mult25 * _atr);

const mySig = for_every(myLongFil, myShortFil, (_long, _short, _prev) => {
    if (_long && !_short) return 1;
    if (_short) return -1;
    return _prev || 0;
});

//--- Bollinger Bands Percentage Calculations ---
const myBbPercentSrc = for_every(close, open, high, low, (_c, _o, _h, _l) => (_c + _o + _h + _l) / 4);
const myBbPercentBasis = sma(myBbPercentSrc, myBbLength);
const myBbPercentDev = mult(stdev(myBbPercentSrc, myBbLength), myBbMult);
const myBbPercentUpper = add(myBbPercentBasis, myBbPercentDev);
const myBbPercentLower = sub(myBbPercentBasis, myBbPercentDev);

const myPositionBetweenBands = mult(
    div(
        sub(myBbPercentSrc, myBbPercentLower),
        sub(myBbPercentUpper, myBbPercentLower)
    ),
    100);

//--- BB% Signal Logic ---
const myLongThresholdSeries = series_of(myLongThreshold);
const myShortThresholdSeries = series_of(myShortThreshold);

const myBbPercentSig = for_every(myPositionBetweenBands, myLongThresholdSeries, myShortThresholdSeries, (_pos, _longTh, _shortTh, _prev) => {
    if (_pos > _longTh) return 1;
    if (_pos < _shortTh) return -1;
    return _prev || 0;
});

//--- Combined Signal Conditions ---
const myMinBbWidthSeries = series_of(myMinBbWidth);

const myBuyCondition = for_every(
    myBbPercentSig, mySig, myScore, myBbWidth, myMinBbWidthSeries,
    (_bbSig, _sig, _score, _width, _minWidth) => 
        _bbSig === 1 && _sig === 1 && _score === 1 && _width > _minWidth);

const mySellCondition = for_every(
    myBbPercentSig, mySig, myScore, myBbWidth, myMinBbWidthSeries,
    (_bbSig, _sig, _score, _width, _minWidth) => 
        _bbSig === -1 && _sig === -1 && _score === -1 && _width > _minWidth);

//--- Gradient Fade Oscillator ---
const myDecayRate = 0.1;

const myFadeSignal = for_every(myBuyCondition, mySellCondition, (_buy, _sell, _prev) => {
    if (_buy) return 1.0;
    if (_sell) return -1.0;
    return (_prev || 0) * (1 - myDecayRate);
});

const myGradientColor = for_every(myFadeSignal, (_fade) => {
    const myAbsFade = Math.abs(_fade);
    if (_fade > 0) {
        const myR = Math.round(255 + (0 - 255) * myAbsFade);
        const myG = Math.round(255 + (123 - 255) * myAbsFade);
        const myB = Math.round(255 + (167 - 255) * myAbsFade);
        return `rgb(${myR}, ${myG}, ${myB})`;
    } else if (_fade < 0) {
        const myR = Math.round(255 + (200 - 255) * myAbsFade);
        const myG = Math.round(255 + (60 - 255) * myAbsFade);
        const myB = Math.round(255 + (60 - 255) * myAbsFade);
        return `rgb(${myR}, ${myG}, ${myB})`;
    }
    return 'rgb(95, 92, 92)';
});

//--- Detect signal transitions for vertical lines ---
const myLongSignal = for_every(myBuyCondition, (_buy, _prev) => {
    if (_buy && !_prev) return true;
    return false;
});

const myShortSignal = for_every(mySellCondition, (_sell, _prev) => {
    if (_sell && !_prev) return true;
    return false;
});

//--- Create vertical line series (sparse series with values only at signal points) ---
const myLongVerticalLine = for_every(myLongSignal, myFadeSignal, (_long, _fade) => 
    _long ? _fade : null);

const myShortVerticalLine = for_every(myShortSignal, myFadeSignal, (_short, _fade) => 
    _short ? _fade : null);

//--- Plotting ---
const myZeroLineSeries = horizontal_line(0);
const myZeroLine = paint(myZeroLineSeries, { 
    color: 'rgba(77, 74, 74, 0.21)',
    name: 'Zero Line',
    style: 'line'
});

const mySignalLine = paint(myFadeSignal, { 
    color: myGradientColor,
    name: 'Gradient Signal Line',
    style: 'line'
});

//--- Paint vertical signal lines (50% transparent) ---
paint(myLongVerticalLine, {
    style: 'column',
    color: 'rgba(0, 123, 167, 0.5)',
    name: 'Long Signal'
});

paint(myShortVerticalLine, {
    style: 'column',
    color: 'rgba(200, 60, 60, 0.5)',
    name: 'Short Signal'
});

const myPositiveSignal = for_every(myFadeSignal, (_fade) => _fade >= 0 ? _fade : null);
const myNegativeSignal = for_every(myFadeSignal, (_fade) => _fade < 0 ? _fade : null);

const myFillColorPositive = for_every(myFadeSignal, (_fade) => {
    if (_fade >= 0) {
        const myAbsFade = Math.abs(_fade);
        const myOpacity = myAbsFade * 0.3;
        const myR = Math.round(255 + (0 - 255) * myAbsFade);
        const myG = Math.round(255 + (123 - 255) * myAbsFade);
        const myB = Math.round(255 + (167 - 255) * myAbsFade);
        return `rgba(${myR}, ${myG}, ${myB}, ${myOpacity})`;
    }
    return 'rgba(0, 0, 0, 0)';
});

const myFillColorNegative = for_every(myFadeSignal, (_fade) => {
    if (_fade < 0) {
        const myAbsFade = Math.abs(_fade);
        const myOpacity = myAbsFade * 0.3;
        const myR = Math.round(255 + (200 - 255) * myAbsFade);
        const myG = Math.round(255 + (60 - 255) * myAbsFade);
        const myB = Math.round(255 + (60 - 255) * myAbsFade);
        return `rgba(${myR}, ${myG}, ${myB}, ${myOpacity})`;
    }
    return 'rgba(0, 0, 0, 0)';
});

color_cloud(myZeroLineSeries, myFadeSignal, 'rgba(200, 60, 60, 0.3)' , 'rgba(0, 123, 167, 0.3)');
</code>