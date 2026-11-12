<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Intermarket Strength Heatmap', 'overlay', { shortName: 'IM Heatmap' });

// =========================  Inputs  =========================
const benchmarkSymbol = input.symbol('Benchmark', 'SPY');
const asset1Symbol = input.symbol('Asset 1', 'QQQ');
const asset2Symbol = input.symbol('Asset 2', 'TLT');
const asset3Symbol = input.symbol('Asset 3', 'GLD');
const asset4Symbol = input.symbol('Asset 4', 'DBA');
const lookbackPeriod = input.number('Lookback Period (Bars)', 50, { min: 20, max: 100, step: 1 });
const strengthThreshold = input.number('Strength Threshold (Z-Score)', 0.5, { min: 0.2, max: 1.5, step: 0.1 });

// Colors for the heatmap
const strongBullish = '#00CC0050'; // Green with transparency
const weakBullish = '#00CC0020';   // Light Green
const neutralColor = '#00000000';  // Transparent
const weakBearish = '#FF000020';   // Light Red
const strongBearish = '#FF000050'; // Red with transparency

// =========================  Data Fetching  =========================
// Function to safely fetch data for a symbol
async function fetchSymbolData(symbol) {
    const data = await request.history(symbol, current.resolution);
    assert(!data.error, `Could not fetch data for ${symbol}: ${data.error}`);
    return data.close;
}

// Fetch data for all symbols
const benchmarkData = await fetchSymbolData(benchmarkSymbol);
const asset1Data = await fetchSymbolData(asset1Symbol);
const asset2Data = await fetchSymbolData(asset2Symbol);
const asset3Data = await fetchSymbolData(asset3Symbol);
const asset4Data = await fetchSymbolData(asset4Symbol);

// Ensure all data series have the same length
const minLength = Math.min(
    benchmarkData.length,
    asset1Data.length,
    asset2Data.length,
    asset3Data.length,
    asset4Data.length
);

// Function to trim series to the same length
function trimSeries(series, length) {
    return series.slice(-length);
}

const myBenchmarkData = trimSeries(benchmarkData, minLength);
const myAsset1Data = trimSeries(asset1Data, minLength);
const myAsset2Data = trimSeries(asset2Data, minLength);
const myAsset3Data = trimSeries(asset3Data, minLength);
const myAsset4Data = trimSeries(asset4Data, minLength);

// =========================  Calculations  =========================
// Calculate relative strength (Asset / Benchmark)
function calculateStrength(assetData, benchmarkData) {
    return for_every(assetData, benchmarkData, (asset, bench) => {
        if (asset === null || bench === null || bench === 0) return null;
        return asset / bench;
    });
}

const strength1 = calculateStrength(myAsset1Data, myBenchmarkData);
const strength2 = calculateStrength(myAsset2Data, myBenchmarkData);
const strength3 = calculateStrength(myAsset3Data, myBenchmarkData);
const strength4 = calculateStrength(myAsset4Data, myBenchmarkData);

// Calculate Z-Score of relative strength
function calculateZScore(strengthSeries, period) {
    const myMean = sma(strengthSeries, period);
    const myStdDev = stdev(strengthSeries, period);
    
    return for_every(strengthSeries, myMean, myStdDev, (_str, _m, _sd) => {
        if (_str === null || _m === null || _sd === null || _sd === 0) return null;
        return (_str - _m) / _sd;
    });
}

const zScore1 = calculateZScore(strength1, lookbackPeriod);
const zScore2 = calculateZScore(strength2, lookbackPeriod);
const zScore3 = calculateZScore(strength3, lookbackPeriod);
const zScore4 = calculateZScore(strength4, lookbackPeriod);

// =========================  Visualization  =========================
// Create the heatmap overlay
paint_overlay('Intermarket Heatmap', { position: 'top_right', width: 220 }, {
    rows: [
        {
            cells: [
                { text: 'Asset', color: 'white', background: '#2C2C2C', align: 'left', width: '40%' },
                { text: 'Vs Benchmark', color: 'white', background: '#2C2C2C', align: 'center', width: '60%' }
            ]
        },
        createHeatmapRow(asset1Symbol, zScore1),
        createHeatmapRow(asset2Symbol, zScore2),
        createHeatmapRow(asset3Symbol, zScore3),
        createHeatmapRow(asset4Symbol, zScore4)
    ]
});

// Helper function to create a heatmap row based on Z-Score
function createHeatmapRow(symbol, zScoreSeries) {
    const lastZScore = zScoreSeries[zScoreSeries.length - 1];
    let bgColor = neutralColor;
    let textColor = 'var(--text-color)';
    let displayValue = 'N/A';
    
    if (lastZScore !== null) {
        displayValue = lastZScore.toFixed(2);
        
        if (lastZScore > strengthThreshold) {
            bgColor = strongBullish;
            textColor = 'white';
        } else if (lastZScore > strengthThreshold / 2) {
            bgColor = weakBullish;
        } else if (lastZScore < -strengthThreshold) {
            bgColor = strongBearish;
            textColor = 'white';
        } else if (lastZScore < -strengthThreshold / 2) {
            bgColor = weakBearish;
        }
    }
    
    return {
        cells: [
            { text: symbol, color: textColor, align: 'left', width: '40%' },
            { text: displayValue, color: textColor, background: bgColor, align: 'center', width: '60%' }
        ]
    };
}
</code>