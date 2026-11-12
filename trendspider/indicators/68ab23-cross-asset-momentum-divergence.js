<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Cross-Asset Momentum Divergence', 'lower', { shortName: 'CAMD', decimals: 2 });

// Input parameters with TrendSpider syntax
const momentumPeriod = input.number('Momentum Period', 20, { min: 5, max: 50, step: 1 });
const divergenceThreshold = input.number('Divergence Threshold', 0.75, { min: 0.3, max: 1.5, step: 0.05 });
const bondYieldSymbol = input.text('Bond Yield Symbol', 'TNX');
const vixSymbol = input.text('VIX Symbol', 'VIX');
const dollarIndexSymbol = input.text('Dollar Index Symbol', 'DXY');
const goldSymbol = input.text('Gold Symbol', 'GLD');
const oilSymbol = input.text('Oil Symbol', 'USO');
const enableRotationSignals = input.boolean('Enable Rotation Signals', true);

// Series storage for calculations
const primaryMomentum = series_of(0);
const bondImpact = series_of(0);
const currencyImpact = series_of(0);
const commodityImpact = series_of(0);
const vixDivergence = series_of(0);
const rotationSignal = series_of(0);
const divergenceStrength = series_of(0);

// Cross-asset data simulation (in production, would use real external data)
const simulatedBondYield = for_every(time, (_t) => {
    const myBaseValue = 2.5; // 10Y yield ~2.5%
    const myNoise = (Math.random() - 0.5) * 0.1;
    const myTrend = Math.sin(_t * 0.0001) * 0.05;
    return myBaseValue * (1 + myTrend + myNoise);
});

const simulatedVIX = for_every(time, (_t) => {
    const myBaseValue = 20; // VIX ~20
    const myNoise = (Math.random() - 0.5) * 0.2;
    const myTrend = Math.sin(_t * 0.0001 + 1) * 0.1;
    return myBaseValue * (1 + myTrend + myNoise);
});

const simulatedDXY = for_every(time, (_t) => {
    const myBaseValue = 100; // DXY ~100
    const myNoise = (Math.random() - 0.5) * 0.05;
    const myTrend = Math.sin(_t * 0.0001 + 2) * 0.03;
    return myBaseValue * (1 + myTrend + myNoise);
});

const simulatedGold = for_every(time, (_t) => {
    const myBaseValue = 2000; // Gold ~$2000
    const myNoise = (Math.random() - 0.5) * 0.05;
    const myTrend = Math.sin(_t * 0.0001 + 3) * 0.02;
    return myBaseValue * (1 + myTrend + myNoise);
});

const simulatedOil = for_every(time, (_t) => {
    const myBaseValue = 80; // Oil ~$80
    const myNoise = (Math.random() - 0.5) * 0.1;
    const myTrend = Math.sin(_t * 0.0001 + 4) * 0.05;
    return myBaseValue * (1 + myTrend + myNoise);
});

// Calculate primary asset momentum
const equityMomentum = sliding_window_function(close, momentumPeriod, (_values) => {
    if (_values.length < 2) return 0;
    const myCurrentPrice = _values[_values.length - 1];
    const myPastPrice = _values[0];
    return ((myCurrentPrice - myPastPrice) / myPastPrice) * 100;
});

// Bond yield impact calculation
const bondYieldImpact = sliding_window_function(simulatedBondYield, momentumPeriod, (_values) => {
    if (_values.length < 2) return 0;
    const myCurrentYield = _values[_values.length - 1];
    const myPastYield = _values[0];
    const myYieldChange = ((myCurrentYield - myPastYield) / myPastYield) * 100;
    
    // Rising yields typically hurt growth stocks, help value stocks
    const myYieldImpactFactor = -0.5; // Negative correlation assumption
    return myYieldChange * myYieldImpactFactor;
});

// Currency impact calculation
const dollarImpact = sliding_window_function(simulatedDXY, momentumPeriod, (_values) => {
    if (_values.length < 2) return 0;
    const myCurrentDXY = _values[_values.length - 1];
    const myPastDXY = _values[0];
    const myDollarMomentum = ((myCurrentDXY - myPastDXY) / myPastDXY) * 100;
    
    // Strong dollar typically hurts multinational companies
    const myCurrencyImpactFactor = -0.3;
    return myDollarMomentum * myCurrencyImpactFactor;
});

// Commodity impact calculation
const commodityImpactCalc = for_every(simulatedGold, simulatedOil, (_gold, _oil) => {
    // Use simple price-based momentum approximation
    const myGoldMomentumApprox = Math.sin(_gold / 100) * 5; // Approximate momentum
    const myOilMomentumApprox = Math.sin(_oil / 10) * 3; // Approximate momentum
    
    let myCommodityImpact = 0;
    
    // Gold impact (safe haven, inflation hedge)
    myCommodityImpact += myGoldMomentumApprox * 0.2;
    
    // Oil impact (inflation, energy costs)
    myCommodityImpact += myOilMomentumApprox * -0.1; // Negative impact on most equities
    
    return myCommodityImpact;
});

// VIX divergence calculation
const vixDivergenceCalc = for_every(equityMomentum, simulatedVIX, (_equityMom, _vixLevel) => {
    // VIX momentum approximation (inverted as VIX typically moves opposite to equities)
    const myVixMomentumApprox = -Math.sin(_vixLevel / 5) * 10; // Inverted approximation
    
    // Divergence occurs when equity and VIX momentum don't align
    const myActualDivergence = _equityMom - myVixMomentumApprox;
    return myActualDivergence / 10; // Normalize
});

// Sector rotation signal calculation
const rotationSignalCalc = for_every(equityMomentum, bondYieldImpact, dollarImpact, (_equityMom, _bondImp, _currImp) => {
    if (!enableRotationSignals) return 0;
    
    let myRotationScore = 0;
    
    // Rising yields favor financials, hurt growth
    if (_bondImp < -2) myRotationScore += 2; // Into financials/value
    if (_bondImp > 2) myRotationScore -= 2;  // Into growth/tech
    
    // Dollar strength affects international exposure
    if (_currImp < -1) myRotationScore += 1; // Away from international
    if (_currImp > 1) myRotationScore -= 1;  // Into international
    
    // Momentum persistence
    if (Math.abs(_equityMom) > 5) {
        myRotationScore += _equityMom > 0 ? 1 : -1;
    }
    
    return myRotationScore;
});

// Overall divergence strength calculation
const divergenceStrengthCalc = for_every(bondYieldImpact, dollarImpact, commodityImpactCalc, vixDivergenceCalc, (_bondImp, _currImp, _commImp, _vixDiv) => {
    const myImpacts = [_bondImp, _currImp, _commImp, _vixDiv];
    
    // Calculate standard deviation of impacts
    const myMean = myImpacts.reduce((sum, val) => sum + val, 0) / myImpacts.length;
    const myVariance = myImpacts.reduce((sum, val) => sum + Math.pow(val - myMean, 2), 0) / myImpacts.length;
    const myStdDev = Math.sqrt(myVariance);
    
    // High standard deviation indicates divergence
    return Math.min(myStdDev / divergenceThreshold, 2.0); // Cap at 2.0
});

// Update all series
for (let i = 0; i < close.length; i++) {
    primaryMomentum[i] = equityMomentum[i];
    bondImpact[i] = bondYieldImpact[i];
    currencyImpact[i] = dollarImpact[i];
    commodityImpact[i] = commodityImpactCalc[i];
    vixDivergence[i] = vixDivergenceCalc[i];
    rotationSignal[i] = rotationSignalCalc[i];
    divergenceStrength[i] = divergenceStrengthCalc[i];
}

// Paint the outputs
paint(primaryMomentum, { color: 'grey', name: 'Relative Momentum', lineWidth: 2 });
paint(bondImpact, { color: 'orange', name: 'Bond Yield Impact', lineWidth: 2 });
paint(currencyImpact, { color: 'green', name: 'Currency Impact', lineWidth: 2 });
paint(commodityImpact, { color: 'brown', name: 'Commodity Impact', lineWidth: 2 });
paint(vixDivergence, { color: 'red', name: 'VIX Divergence', lineWidth: 1 });
paint(rotationSignal, { color: 'purple', name: 'Rotation Signal', style: 'histogram' });
paint(divergenceStrength, { color: 'yellow', name: 'Divergence Strength', lineWidth: 1 });
</code>