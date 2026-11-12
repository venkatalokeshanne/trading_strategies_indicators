<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Volume-Weighted Adaptive Momentum Oscillator (VWAMO)', 'lower', { shortName: 'VWAMO' });

// =========================  Inputs  =========================
const momPeriod = input.number('Momentum Period', 14, { min: 5, max: 30, step: 1 });
const volMultiplier = input.number('Volume Multiplier', 1.5, { min: 0.5, max: 3, step: 0.1 });
const atrPeriod = input.number('ATR Period', 20, { min: 10, max: 50, step: 1 });
const bandTightness = input.number('Band Tightness', 2.0, { min: 1, max: 3, step: 0.1 });

// Colors
const oscColor = '#5D3FD3'; // Purple
const volColor = '#787B86'; // Gray
const upperBandColor = '#F23645'; // Red
const lowerBandColor = '#089981'; // Green
const buySignalColor = '#089981'; // Green
const sellSignalColor = '#F23645'; // Red

// =========================  Calculations  =========================
// 1. Calculate a robust momentum value
const myMomentum = for_every(close, (c, i) => {
    if (i < momPeriod) return null;
    const pastClose = close[i - momPeriod];
    if (pastClose === null || c === null) return null;
    return (c - pastClose) / pastClose * 100;
});

// Smooth the momentum
const smoothMomentum = sma(myMomentum, 3);

// 2. Calculate volume component
const avgVolume = sma(volume, 20);
const volumeRatio = for_every(volume, avgVolume, (vol, avg) => {
    if (vol === null || avg === null || avg === 0) return 1;
    return Math.min(2, Math.max(0.5, vol / avg * volMultiplier));
});

// 3. Create volume-weighted momentum
const volumeWeightedMomentum = for_every(smoothMomentum, volumeRatio, (mom, ratio) => {
    if (mom === null || ratio === null) return null;
    return mom * ratio;
});

// 4. Calculate dynamic bands based on ATR volatility
const atrValues = atr(atrPeriod);
const atrPercent = for_every(atrValues, close, (atrVal, c) => {
    if (atrVal === null || c === null || c === 0) return 1;
    return (atrVal / c) * 100;
});
const avgAtrPercent = sma(atrPercent, 20);
const dynamicUpper = for_every(avgAtrPercent, (val) => {
    if (val === null) return 20;
    return 30 + (val * bandTightness);
});
const dynamicLower = for_every(avgAtrPercent, (val) => {
    if (val === null) return -20;
    return -30 - (val * bandTightness);
});

// 5. Signal detection
const bullSignal = series_of(false);
const bearSignal = series_of(false);
for (let i = 1; i < volumeWeightedMomentum.length; i++) {
    const currentMom = volumeWeightedMomentum[i];
    const prevMom = volumeWeightedMomentum[i-1];
    const currentUpper = dynamicUpper[i];
    const currentLower = dynamicLower[i];
    const currentVolRatio = volumeRatio[i];
    
    if (currentMom !== null && prevMom !== null && 
        currentUpper !== null && currentLower !== null &&
        currentVolRatio !== null) {
        
        // Bullish signal: crosses above lower band with good volume
        if (prevMom < currentLower && currentMom >= currentLower && currentVolRatio > 1) {
            bullSignal[i] = true;
        }
        
        // Bearish signal: crosses below upper band with good volume
        if (prevMom > currentUpper && currentMom <= currentUpper && currentVolRatio > 1) {
            bearSignal[i] = true;
        }
    }
}

// =========================  Visualizations  =========================
// 1. Paint the main oscillator
const oscLine = paint(volumeWeightedMomentum, {
    name: "VWAMO",
    color: oscColor,
    thickness: 2
});

// 2. Paint the dynamic bands
paint(dynamicUpper, {
    name: "Upper Band",
    color: upperBandColor,
    style: "dotted"
});
paint(dynamicLower, {
    name: "Lower Band",
    color: lowerBandColor,
    style: "dotted"
});

// 3. Paint volume component as bars
paint(volumeRatio, {
    name: "Volume Ratio",
    color: volColor,
    style: "column",
    thickness: 1,
    hidden: true
});

// 4. Paint signal arrows
paint(bullSignal, {
    name: "Buy Signal",
    color: buySignalColor,
    style: "labels_above"
});
paint(bearSignal, {
    name: "Sell Signal",
    color: sellSignalColor,
    style: "labels_below"
});

// =========================  Signals & Alerts  =========================
register_signal(bullSignal, 'VWAMO Bullish Signal');
register_signal(bearSignal, 'VWAMO Bearish Signal');

// =========================  Info Overlay  =========================
const lastMom = volumeWeightedMomentum[volumeWeightedMomentum.length - 1];
const lastUpper = dynamicUpper[dynamicUpper.length - 1];
const lastLower = dynamicLower[dynamicLower.length - 1];
const lastVolRatio = volumeRatio[volumeRatio.length - 1];

let signalText = "Neutral";
let signalColor = "var(--text-color)";
if (lastMom !== null && lastUpper !== null && lastLower !== null) {
    if (lastMom > lastUpper) {
        signalText = "Overbought";
        signalColor = upperBandColor;
    } else if (lastMom < lastLower) {
        signalText = "Oversold";
        signalColor = lowerBandColor;
    }
}

paint_overlay('overlay', { position: 'top_right' }, {
    rows: [{
        cells: [
            { text: `Signal: ${signalText}`, color: signalColor, border: 'solid var(--border-color) 1px', padding: 5 },
            { text: `Momentum: ${lastMom ? lastMom.toFixed(2) : 'N/A'}`, color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5 },
            { text: `Volume: ${lastVolRatio ? (lastVolRatio * 100).toFixed(0) + '%' : 'N/A'}`, color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5 }
        ]
    }]
});
</code>