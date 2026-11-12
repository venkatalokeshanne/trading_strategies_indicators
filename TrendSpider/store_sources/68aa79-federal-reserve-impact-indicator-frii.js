<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Federal Reserve Impact Indicator (FRII)', 'lower', { shortName: 'FRII' });
// This is an experimental indicator and may not work as intended or make sense.
// It's based on simulated data and should not be used for actual trading decisions.

// =========================  Inputs  =========================
const economicDataWeight = input.number('Economic Data Weight %', 40, { min: 10, max: 90, step: 5 });
const momentumPeriod = input.number('Momentum Period', 20, { min: 10, max: 50, step: 1 });
const signalThreshold = input.number('Signal Threshold', 2.0, { min: 1.0, max: 5.0, step: 0.1 });

// FRED API series IDs
const fedFundsId = 'FEDFUNDS';
const gdpId = 'GDP';
const unemploymentId = 'UNRATE';
const inflationId = 'CPIAUCSL';

// Colors
const accommodativeColor = '#08998120'; // Light green
const restrictiveColor = '#F2364520';   // Light red
const oscillatorColor = '#5D3FD3';      // Purple
const buySignalColor = '#089981';       // Green
const sellSignalColor = '#F23645';      // Red

// =========================  Data Fetching  =========================
// Function to fetch economic data from FRED API
async function fetchEconomicData(seriesId) {
    try {
        // Simulated economic data for hackathon demonstration
        let simulatedData = series_of(null);
        
        // Create realistic economic data patterns based on series ID
        for (let i = 0; i < close.length; i++) {
            if (seriesId === fedFundsId) {
                // Simulate Fed Funds Rate between 4.0% and 6.0%
                simulatedData[i] = 4.5 + Math.sin(i / 100) * 1.0;
            } else if (seriesId === gdpId) {
                // Simulate GDP growth between -2% and 4%
                simulatedData[i] = 1.0 + Math.sin(i / 200) * 3.0;
            } else if (seriesId === unemploymentId) {
                // Simulate Unemployment Rate between 3.5% and 6.5%
                simulatedData[i] = 4.5 + Math.cos(i / 150) * 1.5;
            } else if (seriesId === inflationId) {
                // Simulate Inflation between 2% and 8%
                simulatedData[i] = 3.5 + Math.sin(i / 120) * 2.5;
            }
        }
        
        return simulatedData;
    } catch (error) {
        throw `Error fetching ${seriesId}: ${error}`;
    }
}

// Fetch economic data
const fedFundsRate = await fetchEconomicData(fedFundsId);
const gdpGrowth = await fetchEconomicData(gdpId);
const unemploymentRate = await fetchEconomicData(unemploymentId);
const inflationRate = await fetchEconomicData(inflationId);

// =========================  Calculations  =========================
// 1. Normalize economic indicators to a common scale (0-100)
const normalizeSeries = (series, invert = false) => {
    const minVal = 0; // Adjust based on realistic ranges for each indicator
    const maxVal = 10; // Adjust based on realistic ranges for each indicator
    
    return for_every(series, val => {
        if (val === null) return 50; // Neutral value if data missing
        let normalized = ((val - minVal) / (maxVal - minVal)) * 100;
        normalized = Math.max(0, Math.min(100, normalized)); // Clamp to 0-100
        return invert ? 100 - normalized : normalized;
    });
};

// Normalize each series (invert some so higher = better for economy)
const normFedFunds = normalizeSeries(fedFundsRate, true); // Lower rates are better
const normGDP = normalizeSeries(gdpGrowth, false);        // Higher GDP is better
const normUnemployment = normalizeSeries(unemploymentRate, true); // Lower unemployment is better
const normInflation = normalizeSeries(inflationRate, true);       // Lower inflation is better

// 2. Create composite economic score
const economicScore = for_every(normFedFunds, normGDP, normUnemployment, normInflation, 
    (ff, gdp, unemp, inf) => {
        if (ff === null || gdp === null || unemp === null || inf === null) return 50;
        // Weighted average of economic indicators
        return (ff * 0.3) + (gdp * 0.3) + (unemp * 0.2) + (inf * 0.2);
    });

// 3. Calculate price momentum
const priceMomentum = for_every(close, (c, i) => {
    if (i < momentumPeriod) return 50;
    const pastClose = close[i - momentumPeriod];
    if (pastClose === null || c === null) return 50;
    return ((c - pastClose) / pastClose) * 100 + 50; // Convert to 0-100 scale
});

// 4. Combine economic score with price momentum
const compositeOscillator = for_every(economicScore, priceMomentum, (econ, mom) => {
    if (econ === null || mom === null) return 50;
    const econWeight = economicDataWeight / 100;
    const momWeight = 1 - econWeight;
    return (econ * econWeight) + (mom * momWeight);
});

// 5. Generate signals
const bullSignal = series_of(null);
const bearSignal = series_of(null);
for (let i = 1; i < compositeOscillator.length; i++) {
    const currentValue = compositeOscillator[i];
    const previousValue = compositeOscillator[i - 1];
    
    if (currentValue !== null && previousValue !== null) {
        // Bullish when oscillator crosses above 50 with strong momentum
        if (previousValue < 50 && currentValue >= 50 && currentValue - previousValue > signalThreshold) {
            bullSignal[i] = currentValue;
        }
        // Bearish when oscillator crosses below 50 with strong momentum
        if (previousValue > 50 && currentValue <= 50 && previousValue - currentValue > signalThreshold) {
            bearSignal[i] = currentValue;
        }
    }
}

// =========================  Visualization  =========================
// 1. Main oscillator
const oscLine = paint(compositeOscillator, {
    name: "FRII Oscillator",
    color: oscillatorColor,
    thickness: 2
});

// 2. Policy stance background
const policyStance = for_every(economicScore, score => {
    if (score === null) return 0;
    return score > 60 ? 1 : (score < 40 ? -1 : 0);
});

// Use color_cloud instead of paint_background
const upperBound = series_of(100);
const lowerBound = series_of(0);
color_cloud(upperBound, compositeOscillator, accommodativeColor, restrictiveColor);

// 3. Signal arrows
paint(bullSignal, {
    name: "Bullish Signal",
    color: buySignalColor,
    style: "labels_above"
});

paint(bearSignal, {
    name: "Bearish Signal",
    color: sellSignalColor,
    style: "labels_below"
});

// 4. Economic data overlay
const lastFedFunds = fedFundsRate[fedFundsRate.length - 1];
const lastGDP = gdpGrowth[gdpGrowth.length - 1];
const lastUnemployment = unemploymentRate[unemploymentRate.length - 1];
const lastInflation = inflationRate[inflationRate.length - 1];

paint_overlay('Economic Data', { position: 'top_left' }, {
    rows: [
        {
            cells: [
                { text: 'Economic Indicator', color: 'white', background: '#2C2C2C', align: 'left', width: '50%' },
                { text: 'Current Value', color: 'white', background: '#2C2C2C', align: 'center', width: '50%' }
            ]
        },
        {
            cells: [
                { text: 'Fed Funds Rate', color: 'var(--text-color)', align: 'left', width: '50%' },
                { text: lastFedFunds ? `${lastFedFunds.toFixed(2)}%` : 'N/A', color: 'var(--text-color)', align: 'center', width: '50%' }
            ]
        },
        {
            cells: [
                { text: 'GDP Growth', color: 'var(--text-color)', align: 'left', width: '50%' },
                { text: lastGDP ? `${lastGDP.toFixed(2)}%` : 'N/A', color: 'var(--text-color)', align: 'center', width: '50%' }
            ]
        },
        {
            cells: [
                { text: 'Unemployment', color: 'var(--text-color)', align: 'left', width: '50%' },
                { text: lastUnemployment ? `${lastUnemployment.toFixed(2)}%` : 'N/A', color: 'var(--text-color)', align: 'center', width: '50%' }
            ]
        },
        {
            cells: [
                { text: 'Inflation', color: 'var(--text-color)', align: 'left', width: '50%' },
                { text: lastInflation ? `${lastInflation.toFixed(2)}%` : 'N/A', color: 'var(--text-color)', align: 'center', width: '50%' }
            ]
        }
    ]
});

// =========================  Signals & Alerts  =========================
register_signal(bullSignal, 'FRII Bullish Signal');
register_signal(bearSignal, 'FRII Bearish Signal');
</code>