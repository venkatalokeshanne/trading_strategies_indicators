<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Ripster DTR vs ATR', 'price');

// === Inputs ===
const atrLen = input.number('ATR Length', 14);
const atrSmooth = input.select('Smoothing Type', 'RMA', ['EMA', 'RMA', 'SMA', 'WMA']);

// === Helpers ===
const roundVal = (val, decimals = 2) => {
    const factor = Math.pow(10, decimals);
    return Math.round(Math.abs(val * factor)) / factor * Math.sign(val);
};

// Use higher timeframe series for ATR and DTR
const timeframe = 'D';
const highTFData = await request.history(current.ticker, timeframe);
assert(!highTFData.error, `Error fetching data: ${highTFData.error}`);

// === ATR Calculation ===
const trSeries = for_every(highTFData.high, highTFData.low, highTFData.close, (h, l, c, _prev, i) => {
    const prevClose = i > 0 ? highTFData.close[i - 1] : c;
    return Math.max(h - l, Math.abs(h - prevClose), Math.abs(l - prevClose));
});

const atrSeries = (() => {
    if (atrSmooth === 'EMA') return ema(trSeries, atrLen);
    if (atrSmooth === 'SMA') return sma(trSeries, atrLen);
    if (atrSmooth === 'WMA') return wma(trSeries, atrLen);
    return wildma(trSeries, atrLen); // Default RMA
})();

// Ensure all series have the same length
const seriesLength = Math.min(highTFData.high.length, highTFData.low.length, atrSeries.length);
const highSeries = highTFData.high.slice(-seriesLength);
const lowSeries = highTFData.low.slice(-seriesLength);
const avgATR = atrSeries.slice(-seriesLength);
const dailyTR = sub(highSeries, lowSeries);
const dtrPct = mult(div(dailyTR, avgATR), 100);

// === Label Text ===
const dtrVal = roundVal(dailyTR[dailyTR.length - 1], 2);
const atrVal = roundVal(avgATR[avgATR.length - 1], 2);
const finalText = `DTR: ${dtrVal}   vs   ATR: ${atrVal}   (${roundVal(dtrPct[dtrPct.length - 1], 0)}%)`;

// === Color Coding ===
const atrColor = dtrPct[dtrPct.length - 1] <= 70 ? 'green' : dtrPct[dtrPct.length - 1] >= 90 ? '#d78585' : '#ffd500';
const textColor = atrColor === '#ffd500' ? 'black' : 'white';

// === Build Overlay Table ===
const rows = [
    {
        cells: [
            {
                text: finalText,
                background: atrColor,
                padding: '10px',
                color: textColor,
                fontSize: '14px'
            }
        ]
    }
];

// Position the overlay at the top right (top_center is not a valid position)
paint_overlay('DTR ATR Overlay', { position: 'top_right' }, {
    border: '1px solid var(--border-color)',
    borderRadius: '6px',
    background: 'var(--background-color)',
    rows
});</code>