<code x-ref="code" class="hljs" data-clipboard-text>// This indicator code was generated using AI. It was not checked by Quality Assurance
// and did not pass any quality assurance processes that we normally would use at TrendSpider.
// As a result, we can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only.

describe_indicator('Trend Directional Force Index - TDFI - v2', 'lower');

// Inputs
const lookback = input.number('Lookback Period', 13);
const mmaLength = input.number('MMA Length', 13);
const smmaLength = input.number('SMMA Length', 13);
const nLength = input.number('N Length', 3);
const filterHigh = input.number('Filter High', 0.05);
const filterLow = input.number('Filter Low', -0.05);
const mmaMode = input.select('MMA Type', 'ema', ['ema', 'wma', 'vwma', 'hull', 'tema']);
const smmaMode = input.select('SMMA Type', 'ema', ['ema', 'wma', 'vwma', 'hull', 'tema']);
const price = prices['close']; // Assuming 'prices' is an object with price data

// Helper function: TEMA calculation
function tema(src, len) {
    const ema1 = ema(src, len);
    const ema2 = ema(ema1, len);
    const ema3 = ema(ema2, len);
    return (3 * ema1) - (3 * ema2) + ema3;
}

// Generalized moving average function based on mode
function ma(mode, src, len) {
    switch (mode) {
        case "ema": return ema(src, len);
        case "wma": return wma(src, len);
        case "vwma": return vwma(src, len);
        case "hull": return hullma(src, len);
        case "tema": return tema(src, len);
        default: return sma(src, len);
    }
}

// Function to calculate the TDFI
function tdfi() {
    const mma = ma(mmaMode, price.map(p => p * 1000), mmaLength);
    const smma = ma(smmaMode, mma, smmaLength);
    const impetmma = mma.map((m, idx) => m - (mma[idx - 1] || 0));
    const impetsmma = smma.map((s, idx) => s - (smma[idx - 1] || 0));
    const divma = mma.map((m, idx) => Math.abs(m - smma[idx]));
    const averimpet = impetmma.map((im, idx) => (im + impetsmma[idx]) / 2);
    const tdf = divma.map((d, idx) => Math.pow(d, 1) * Math.pow(averimpet[idx], nLength));
    const highestTdf = highest(tdf.map(Math.abs), lookback * nLength);
    return tdf.map((t, idx) => t / highestTdf[idx]);
}

// Calculate the TDFI signal
const signal = tdfi();

// Define color scheme for the signal
const signalColor = signal.map(s => s > filterHigh ? 'green' : s < filterLow ? 'red' : 'gray');

// Paint the TDFI line
paint(signal, {
    style: 'line',
    color: signalColor,
    thickness: 2,
    name: 'TDFI'
});

// Paint horizontal lines for filters
paint(horizontal_line(filterHigh), { color: 'black', name: 'Filter High', style: 'line' });
paint(horizontal_line(filterLow), { color: 'black', name: 'Filter Low', style: 'line' });

// Paint background shading manually using the filterHigh and filterLow
const aboveFilter = signal.map(s => s > filterHigh ? filterHigh : null);
const belowFilter = signal.map(s => s < filterLow ? filterLow : null);

// Paint shaded regions (green above filterHigh and red below filterLow)
paint(aboveFilter, { style: 'column', color: 'rgba(0,255,0,0.1)' });
paint(belowFilter, { style: 'column', color: 'rgba(255,0,0,0.1)' });
</code>