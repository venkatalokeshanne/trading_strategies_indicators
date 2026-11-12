<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Returns Distribution #TSBuild25', {shortName:'Returns Dist'});

const inputs = {
    lookback: input.number('Lookback (0 = All)', 0, { min: 0 }),
    bins: input.number('Histogram Bins', 30, { min: 10, max: 50 }),
    color_positive: input.color('Positive Color', 'rgba(0, 230, 118, 0.85)'),
    color_negative: input.color('Negative Color', 'rgba(255, 23, 68, 0.85)'),
    color_current:  input.color('Current Bar Color', '#03A9F4')
};

const returns = [];
for (let i = 1; i < close.length; i++) {
    returns.push(((close[i] / close[i - 1]) - 1) * 100);
}

const historicalReturns = inputs.lookback > 0
    ? returns.slice(-inputs.lookback - 1, -1)
    : returns.slice(0, -1);

assert(historicalReturns.length > 1, 'Not enough historical data to build distribution.');

const n = historicalReturns.length;
const mean = historicalReturns.reduce((a, b) => a + b, 0) / n;
const var_samp = historicalReturns.reduce((a,b)=> a + (b-mean)*(b-mean), 0) / Math.max(n - 1, 1);
const stdDev = Math.sqrt(Math.max(var_samp, 0));
const maxHist = Math.max(...historicalReturns);
const minHist = Math.min(...historicalReturns);
const currentReturn = returns[returns.length - 1];

const minReturn = Math.min(minHist, currentReturn);
const maxReturn = Math.max(maxHist, currentReturn);
const isNewExtremeHigh = currentReturn > maxHist;
const isNewExtremeLow  = currentReturn < minHist;

const numBins = inputs.bins > 0 ? inputs.bins : Math.max(10, Math.ceil(Math.sqrt(n)));

const span = Math.max(maxReturn - minReturn, 0.01);
const binSize = span / numBins;

let bins = Array(numBins).fill(0);
let binLabels = [];
for (let i = 0; i < numBins; i++) {
    const binStart = minReturn + (i * binSize);
    const binEnd   = binStart + binSize;
    binLabels.push(binStart.toFixed(2) + '%');

    for (let j = 0; j < n; j++){
        const r = historicalReturns[j];
        if (r >= binStart && (r < binEnd || (i === numBins - 1 && r <= binEnd))) {
            bins[i]++;
        }
    }
}

let currentBinIndex = -1;
if (binSize > 0) {
    const idx = Math.floor((currentReturn - minReturn) / binSize);
    currentBinIndex = Math.max(0, Math.min(numBins - 1, idx));
}

const distributionChart = {
  width: '320px', height: '140px', type: 'bar',
  options: {
    scales: {
      y: { display: false },
      x: {
        ticks: { autoSkip: true, maxRotation: 0, minRotation: 0, font: { size: 9 }, color: '#C9CED6' },
        grid: { display: false }
      }
    },
    plugins: { legend: { display: false } },
    layout: { padding: { top: 8 } }
  },
  data: {
    labels: binLabels,
    datasets: [{
      data: bins,
      backgroundColor: bins.map((_, i) => {
        if (i === currentBinIndex) return inputs.color_current;                 
        const binCenter = minReturn + (i + 0.5) * binSize;
        return binCenter >= 0 ? inputs.color_positive : inputs.color_negative; 
      }),
      borderColor: bins.map((_, i) => i === currentBinIndex ? (isNewExtremeHigh || isNewExtremeLow ? '#FFD166' : '#FFFFFF') : '#2A2F3A'),
      borderWidth: bins.map((_, i) => i === currentBinIndex ? (isNewExtremeHigh || isNewExtremeLow ? 2 : 1.5) : 0.5),
      borderRadius: 2
    }]
  }
};

const titleCell = text => ({ text, fontWeight: 600, color: '#E7EBF3', padding: '8px 10px', fontSize: 13 });
const statCell = (label, value) => ({
    text: `<span style="opacity:0.85">${label}</span><span style="float:right;font-weight:600">${value}</span>`,
    color: '#D3D7DF',
    padding: '6px 10px',
    fontSize: 12
});
const keyCell = (text, color) => ({ text, fontWeight: 700, fontSize: 13, color, padding: '8px 10px', textAlign: 'center' });
const SEPARATOR = { text: "", colspan: 2, borderBottom: '1px solid #2A2F3A', padding: '2px 0' };

const titleText = inputs.lookback > 0 
    ? `${current.ticker} Returns Distribution` 
    : `${current.ticker} Returns Distribution`;
const extremeTag = isNewExtremeHigh ? ' (NEW MAX)' : (isNewExtremeLow ? ' (NEW MIN)' : '');
{ cells: [{ ...keyCell(`Current: ${currentReturn.toFixed(2)}%${extremeTag}`, inputs.color_current), colspan: 2 }] }

paint_overlay('Table', { position: 'bottom_right', order: 'above_all' }, {
    fontSize: 12,
    border: '1px solid #2A2F3A',
    background: 'rgba(16, 18, 24, 0.92)',   
    borderRadius: '10px',
    boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
    rows: [
        { cells: [{ ...titleCell(titleText), colspan: 2, textAlign: 'center' }] },
        { cells: [SEPARATOR] },
        { cells: [{ chart: distributionChart, colspan: 2 }] },
        { cells: [SEPARATOR] },
        { cells: [ statCell('Mean: ', `${mean.toFixed(2)}%`), statCell('Std Dev: ', `${stdDev.toFixed(2)}%`) ] },
        { cells: [ statCell('Max: ', `${maxReturn.toFixed(2)}%`), statCell('Min: ', `${minReturn.toFixed(2)}%`) ] },
        { cells: [{ ...keyCell(`Current: ${currentReturn.toFixed(2)}%`, inputs.color_current), colspan: 2 }] }
    ]
});</code>