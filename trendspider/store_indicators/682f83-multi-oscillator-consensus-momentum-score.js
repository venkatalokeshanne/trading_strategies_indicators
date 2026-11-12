<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Multi-Oscillator Consensus Momentum Score');

// === Input Parameters ===
const macdFast = input.number('MACD Fast Length', 12, { min: 1 });
const macdSlow = input.number('MACD Slow Length', 26, { min: 1 });
const macdSignal = input.number('MACD Signal Length', 9, { min: 1 });
const rsiLength = input.number('RSI Length', 14, { min: 1 });
const ppoFast = input.number('PPO Fast Length', 12, { min: 1 });
const ppoSlow = input.number('PPO Slow Length', 26, { min: 1 });
const ppoSignal = input.number('PPO Signal Length', 9, { min: 1 });
const mfiLength = input.number('MFI Length', 14, { min: 1 });
const cciLength = input.number('CCI Length', 20, { min: 1 });
const stochRsiLength = input.number('Stoch RSI Length', 14, { min: 1 });
const fischerLength = input.number('Fischer Length', 9, { min: 1 });
const cmoLength = input.number('CMO Length', 14, { min: 1 });
const kstRoc1 = input.number('KST ROC1', 10, { min: 1 });
const kstRoc2 = input.number('KST ROC2', 15, { min: 1 });
const kstRoc3 = input.number('KST ROC3', 20, { min: 1 });
const kstRoc4 = input.number('KST ROC4', 30, { min: 1 });
const kstSma1 = input.number('KST SMA1', 10, { min: 1 });
const kstSma2 = input.number('KST SMA2', 10, { min: 1 });
const kstSma3 = input.number('KST SMA3', 10, { min: 1 });
const kstSma4 = input.number('KST SMA4', 15, { min: 1 });
const kstSignal = input.number('KST Signal', 9, { min: 1 });
const smLength = input.number('Stoch Mom Length', 10, { min: 1 });
const smSmoothK = input.number('SM %K', 3, { min: 1 });
const smSmoothD = input.number('SM %D', 3, { min: 1 });
const aroonLength = input.number('Aroon Length', 14, { min: 1 });
const awesomeOscFast = input.number('AO Fast Length', 5, { min: 1 });
const awesomeOscSlow = input.number('AO Slow Length', 34, { min: 1 });
const overboughtThreshold = input.number('Overbought Threshold', 5, { min: 1, max: 10 });
const oversoldThreshold = input.number('Oversold Threshold', -5, { max: -1, min: -10 });
const filterDuplicates = input.boolean('Filter Duplicate Signals', false);
// New inputs for SMA crossover
const mySma50Length = input.number('SMA 50 Length', 50, { min: 1 });
const mySma200Length = input.number('SMA 200 Length', 200, { min: 1 });
const myStdDevLength = input.number('Standard Deviation Length', 20, { min: 1 });
// New input for %B
const myBBLength = input.number('%B Length', 20, { min: 1 });
const myBBMultiplier = input.number('%B Multiplier', 2, { min: 0.1 });

// === Indicator Calculations ===
const myMacd = sub(ema(close, macdFast), ema(close, macdSlow));
const myMacdSignal = ema(myMacd, macdSignal);
const myMacdHist = sub(myMacd, myMacdSignal);
const myRsi = rsi(close, rsiLength);
const myPpo = mult(div(sub(ema(close, ppoFast), ema(close, ppoSlow)), ema(close, ppoSlow)), 100);
const myPpoSignal = ema(myPpo, ppoSignal);
const myPpoHist = sub(myPpo, myPpoSignal);
const myMfi = mfi(hlc3, volume, mfiLength);
const myCci = cci(hlc3, cciLength);
const myStochRsi = stochastic_rsi(close, stochRsiLength, 3);
const myFischer = sliding_window_function(close, fischerLength, _window => {
    const myHigh = Math.max(..._window);
    const myLow = Math.min(..._window);
    const val = 0.33 * 2 * ((_window[_window.length - 1] - myLow) / (myHigh - myLow) - 0.5) + 0.67 * (_window[_window.length - 2] || 0);
    return 0.5 * Math.log((1 + val) / (1 - val));
});
const myCmo = cmo(close, cmoLength);
const myKst = for_every(close, (_c, _pc, i) => {
    if (i < kstRoc4 + kstSma4 - 1) return null;
    const roc1 = sma(roc(close, kstRoc1), kstSma1);
    const roc2 = sma(roc(close, kstRoc2), kstSma2);
    const roc3 = sma(roc(close, kstRoc3), kstSma3);
    const roc4 = sma(roc(close, kstRoc4), kstSma4);
    return roc1[i] + 2 * roc2[i] + 3 * roc3[i] + 4 * roc4[i];
});
const myKstSignal = ema(myKst, kstSignal);
const myKstHist = sub(myKst, myKstSignal);
const myStochMomentum = sliding_window_function(close, smLength, _window => {
    const myHigh = Math.max(..._window);
    const myLow = Math.min(..._window);
    return 100 * (_window[_window.length - 1] - myLow) / (myHigh - myLow);
});
const mySmK = sma(myStochMomentum, smSmoothK);
const mySmD = sma(mySmK, smSmoothD);
// New indicators: AROON Oscillator and Awesome Oscillator
const myAroonUp = for_every(high, (_h, _ph, i) => {
    if (i < aroonLength) return null;
    const window = high.slice(i - aroonLength + 1, i + 1);
    return 100 * (aroonLength - window.lastIndexOf(Math.max(...window))) / aroonLength;
});
const myAroonDown = for_every(low, (_l, _pl, i) => {
    if (i < aroonLength) return null;
    const window = low.slice(i - aroonLength + 1, i + 1);
    return 100 * (aroonLength - window.lastIndexOf(Math.min(...window))) / aroonLength;
});
const myAroonOsc = sub(myAroonUp, myAroonDown);
const myAwesomeOsc = sub(sma(hl2, awesomeOscFast), sma(hl2, awesomeOscSlow));
// New SMA crossover indicator
const mySma50 = sma(close, mySma50Length);
const mySma200 = sma(close, mySma200Length);
const myStdDev = stdev(close, myStdDevLength);
const mySmaCrossover = for_every(mySma50, mySma200, myStdDev, (_sma50, _sma200, _stdDev) => {
    if (_sma50 - _sma200 >= _stdDev) return 1;
    if (_sma200 - _sma50 >= _stdDev) return -1;
    return 0;
});

// New %B indicator
const myBBMid = sma(close, myBBLength);
const myBBDev = mult(stdev(close, myBBLength), myBBMultiplier);
const myBBUpper = add(myBBMid, myBBDev);
const myBBLower = sub(myBBMid, myBBDev);
const myPercentB = for_every(close, myBBUpper, myBBLower, (_c, _u, _l) => {
    return (_c - _l) / (_u - _l);
});

// === Zone Scoring ===
const getZoneScore = (_v, _hi, _lo) => (_v >= _hi ? 1 : _v <= _lo ? -1 : 0);
const macdZoneScore = for_every(myMacdHist, _h => getZoneScore(_h, 0.5, -0.5));
const rsiZoneScore = for_every(myRsi, _r => getZoneScore(_r, 70, 30));
const ppoZoneScore = for_every(myPpoHist, _p => getZoneScore(_p, 0.5, -0.5));
const mfiZoneScore = for_every(myMfi, _m => getZoneScore(_m, 80, 20));
const cciZoneScore = for_every(myCci, _c => getZoneScore(_c, 100, -100));
const stochRsiZoneScore = for_every(myStochRsi, _s => getZoneScore(_s, 80, 20));
const fischerZoneScore = for_every(myFischer, _f => getZoneScore(_f, 2, -2));
const cmoZoneScore = for_every(myCmo, _c => getZoneScore(_c, 50, -50));
const kstZoneScore = for_every(myKstHist, _k => getZoneScore(_k, 0.5, -0.5));
const smZoneScore = for_every(sub(mySmK, mySmD), _s => getZoneScore(_s, 20, -20));
const aroonOscZoneScore = for_every(myAroonOsc, _a => getZoneScore(_a, 50, -50));
const awesomeOscZoneScore = for_every(myAwesomeOsc, _a => getZoneScore(_a, 0.5, -0.5));
const percentBZoneScore = for_every(myPercentB, _b => getZoneScore(_b, 1, 0));

// === Aggregate Score ===
const aggregateScore = for_every(
    macdZoneScore, rsiZoneScore, ppoZoneScore, mfiZoneScore, cciZoneScore, stochRsiZoneScore, fischerZoneScore,
    cmoZoneScore, kstZoneScore, smZoneScore, aroonOscZoneScore, awesomeOscZoneScore, mySmaCrossover, percentBZoneScore,
    (_macd, _rsi, _ppo, _mfi, _cci, _stochRsi, _fischer, _cmo, _kst, _sm, _aroon, _awesome, _sma, _percentB) => {
        const scores = [_macd, _rsi, _ppo, _mfi, _cci, _stochRsi, _fischer, _cmo, _kst, _sm, _aroon, _awesome, _sma, _percentB];
        const overboughtCount = scores.filter(_s => _s === 1).length;
        const oversoldCount = scores.filter(_s => _s === -1).length;
        return overboughtCount - oversoldCount;
    });

// === Signal Logic (trigger on presence, avoid duplicates with same count if enabled) ===
let lastSignal = null;
let lastCount = 0;
const signals = for_every(aggregateScore, (_s, _p, i) => {
    const score = aggregateScore[i];
    const agreeingIndicators = {
        overbought: score,
        oversold: -score
    };
    
    // Fix: Use greater than or equal to for overbought, and less than or equal to for oversold
    if (score <= oversoldThreshold && (!filterDuplicates || lastSignal !== 'oversold' || lastCount !== agreeingIndicators.oversold)) {
        lastSignal = 'oversold';
        lastCount = agreeingIndicators.oversold;
        return 'oversold';
    }
    if (score >= overboughtThreshold && (!filterDuplicates || lastSignal !== 'overbought' || lastCount !== agreeingIndicators.overbought)) {
        lastSignal = 'overbought';
        lastCount = agreeingIndicators.overbought;
        return 'overbought';
    }
    return null;
});

// === Paint Labels ===
const myHighPainted = paint(high, { name: 'highs', color: 'white', style: 'dotted' });
const myLowPainted = paint(low, { name: 'lows', color: 'white', style: 'dotted' });
const agreeingIndicators = for_every(
    macdZoneScore, rsiZoneScore, ppoZoneScore, mfiZoneScore, cciZoneScore, stochRsiZoneScore, fischerZoneScore,
    cmoZoneScore, kstZoneScore, smZoneScore, aroonOscZoneScore, awesomeOscZoneScore, mySmaCrossover, percentBZoneScore,
    (_macd, _rsi, _ppo, _mfi, _cci, _stochRsi, _fischer, _cmo, _kst, _sm, _aroon, _awesome, _sma, _percentB) => {
        const scores = [_macd, _rsi, _ppo, _mfi, _cci, _stochRsi, _fischer, _cmo, _kst, _sm, _aroon, _awesome, _sma, _percentB];
        const overboughtCount = scores.filter(_s => _s === 1).length;
        const oversoldCount = scores.filter(_s => _s === -1).length;
        return { overbought: overboughtCount, oversold: oversoldCount };
    });

for (let i = 0; i < signals.length; i++) {
    if (signals[i] === 'oversold') {
        paint_label_at_line(myLowPainted, i, `▲${agreeingIndicators[i].oversold}`, {
            color: 'green', vertical_align: 'bottom'
        });
    } else if (signals[i] === 'overbought') {
        paint_label_at_line(myHighPainted, i, `▼${agreeingIndicators[i].overbought}`, {
            color: 'red', vertical_align: 'top'
        });
    }
}

// === Debug Overlay (optional) ===
//paint(aggregateScore, { name: 'Consensus Score', color: 'blue' });

// === Register Signals ===
register_signal(for_every(signals, _s => _s === 'oversold'), 'Oversold Signal');
register_signal(for_every(signals, _s => _s === 'overbought'), 'Overbought Signal');
</code>