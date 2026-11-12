<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Sector Rotation Matrix', 'lower', { shortName: 'SectorRotation' });

/* =========================  Inputs  ========================= */
// Core sectors to track - LIMITED TO 5 due to TrendSpider's 6 history call limit
const sectors = input.text('Sectors (max 5, comma)', 'XLK,XLF,XLV,XLE,XLI');
const benchmark = input.symbol('Benchmark', 'SPY');

// Rotation detection
const rotationThreshold = input.number('Rotation Threshold', 1.5, { min: 0.5, max: 3, step: 0.1 });

// Display options
const displayMode = input.select('Display Mode', 'Rotation Score', 
  ['Rotation Score', 'Relative Strength', 'Volume Flow', 'Combined Signal']);

/* =========================  Helper Functions  ========================= */
const fetchSectorData = async (ticker) => {
  const res = await request.history(ticker, current.resolution);
  if (res.error) {
    console.warn(`Error fetching ${ticker}: ${res.error}`);
    return null;
  }
  return res;
};

const alignToChart = (data, dataTime, chartTime) => {
  const map = {};
  for (let i = 0; i < dataTime.length; i++) {
    map[dataTime[i]] = data[i];
  }
  return chartTime.map(t => map[t] ?? null);
};

// Helper to create filled array
const createFilledArray = (length, value) => {
  const arr = [];
  for (let i = 0; i < length; i++) {
    arr.push(value);
  }
  return arr;
};

// Helper to create null series (renamed from series_of)
const createNullSeries = (value) => {
  return createFilledArray(time.length, value);
};

// Simple relative strength calculation
const calcRelativeStrength = (sectorClose, benchClose) => {
  const result = [];
  for (let i = 0; i < sectorClose.length; i++) {
    if (i < 20) {
      result.push(null);
      continue;
    }
    
    const sectorStart = sectorClose[i - 20];
    const sectorEnd = sectorClose[i];
    const benchStart = benchClose[i - 20];
    const benchEnd = benchClose[i];
    
    if (sectorStart && sectorEnd && benchStart && benchEnd) {
      const sectorReturn = (sectorEnd - sectorStart) / sectorStart;
      const benchReturn = (benchEnd - benchStart) / benchStart;
      result.push(((1 + sectorReturn) / (1 + benchReturn) - 1) * 100);
    } else {
      result.push(null);
    }
  }
  return result;
};

// Simple volume intensity calculation
const calcVolumeIntensity = (volume, closeData) => {
  const result = [];
  for (let i = 0; i < volume.length; i++) {
    if (i < 20) {
      result.push(null);
      continue;
    }
    
    let vwSum = 0, volSum = 0;
    let validCount = 0;
    
    for (let j = i - 19; j <= i; j++) {
      if (j > 0 && volume[j] && closeData[j] && closeData[j-1]) {
        const ret = (closeData[j] - closeData[j-1]) / closeData[j-1];
        vwSum += ret * volume[j];
        volSum += volume[j];
        validCount++;
      }
    }
    
    if (validCount > 10 && volSum > 0) {
      result.push(vwSum / volSum * 1000);
    } else {
      result.push(null);
    }
  }
  return result;
};

// Simple z-score normalization
const normalizeToZScore = (series) => {
  const result = [];
  for (let i = 0; i < series.length; i++) {
    if (i < 60) {
      result.push(null);
      continue;
    }
    
    // Get last 60 values
    const window = [];
    for (let j = i - 59; j <= i; j++) {
      if (series[j] != null) {
        window.push(series[j]);
      }
    }
    
    if (window.length < 20) {
      result.push(null);
      continue;
    }
    
    // Calculate mean and std
    const meanVal = window.reduce((a, b) => a + b, 0) / window.length;
    const squaredDiffs = window.map(v => Math.pow(v - meanVal, 2));
    const varVal = squaredDiffs.reduce((a, b) => a + b, 0) / window.length;
    const stdVal = Math.sqrt(varVal);
    
    if (stdVal === 0 || series[i] == null) {
      result.push(null);
    } else {
      result.push((series[i] - meanVal) / stdVal);
    }
  }
  return result;
};

// Simple smoothing
const smoothData = (series, window) => {
  const result = [];
  for (let i = 0; i < series.length; i++) {
    if (i < window - 1) {
      result.push(null);
      continue;
    }
    
    let total = 0, count = 0;
    for (let j = i - window + 1; j <= i; j++) {
      if (series[j] != null) {
        total += series[j];
        count++;
      }
    }
    
    result.push(count > 0 ? total / count : null);
  }
  return result;
};

/* =========================  Fetch and Process Sector Data  ========================= */
const sectorList = sectors.split(',').map(s => s.trim()).slice(0, 5); // LIMIT TO 5 SECTORS
const chartTime = time;

// Initialize default values - these will ALWAYS be painted
let rotationScore = createFilledArray(chartTime.length, 0);
let primarySeries = createFilledArray(chartTime.length, 0);
let seriesName = 'Market Rotation Intensity';
let seriesColor = 'purple';

const sectorMetrics = {};

// Initialize dashboard rows with empty data
let dashboardRows = [];

// Process data
let hasError = false;
let errorMessage = '';

// Check if we have too many sectors
if (sectorList.length > 5) {
  hasError = true;
  errorMessage = 'Max 5 sectors allowed';
  // Keep everything as null/zero series
} else {
  // Fetch benchmark
  const benchData = await fetchSectorData(benchmark);
  if (!benchData || !benchData.close) {
    hasError = true;
    errorMessage = 'Cannot fetch benchmark';
  } else {
    const benchClose = alignToChart(benchData.close, benchData.time, chartTime);

    // Process each sector (max 5)
    for (const ticker of sectorList) {
      const data = await fetchSectorData(ticker);
      if (!data) continue;
      
      const closeData = alignToChart(data.close, data.time, chartTime);
      const volumeData = alignToChart(data.volume, data.time, chartTime);
      
      // Calculate metrics
      const rs = calcRelativeStrength(closeData, benchClose);
      const vi = calcVolumeIntensity(volumeData, closeData);
      
      // Normalize to z-scores
      const rsZ = normalizeToZScore(rs);
      const viZ = normalizeToZScore(vi);
      
      // Combined rotation signal
      const combined = [];
      for (let i = 0; i < rsZ.length; i++) {
        if (rsZ[i] == null && viZ[i] == null) {
          combined.push(null);
        } else if (rsZ[i] == null) {
          combined.push(viZ[i] * 0.4);
        } else if (viZ[i] == null) {
          combined.push(rsZ[i] * 0.6);
        } else {
          combined.push(rsZ[i] * 0.6 + viZ[i] * 0.4);
        }
      }
      
      // Smooth the signal
      const smoothed = smoothData(combined, 3);
      
      sectorMetrics[ticker] = {
        relativeStrength: rs,
        volumeIntensity: vi,
        rsZScore: rsZ,
        viZScore: viZ,
        combined: smoothed
      };
      
      // Add to rotation score
      for (let i = 0; i < smoothed.length; i++) {
        if (smoothed[i] != null && Math.abs(smoothed[i]) > rotationThreshold) {
          rotationScore[i] += smoothed[i] > 0 ? 1 : -1;
        }
      }
    }
  }
}

/* =========================  Rankings and Display Mode  ========================= */

// Get rankings (even if empty)
const getCurrentRankings = () => {
  const latest = {};
  for (const [ticker, metrics] of Object.entries(sectorMetrics)) {
    const val = metrics.combined[metrics.combined.length - 1];
    if (val != null) latest[ticker] = val;
  }
  return Object.entries(latest)
    .sort((a, b) => b[1] - a[1])
    .map(([ticker, score]) => ({ ticker, score }));
};

const rankings = getCurrentRankings();

// Select display based on mode (always assign something)
if (!hasError) {
  switch (displayMode) {
    case 'Rotation Score':
      primarySeries = rotationScore;
      seriesName = 'Market Rotation Intensity';
      seriesColor = 'purple';
      break;
    case 'Relative Strength':
      if (rankings.length > 0 && sectorMetrics[rankings[0].ticker]) {
        primarySeries = sectorMetrics[rankings[0].ticker].relativeStrength;
        seriesName = `${rankings[0].ticker} Relative Strength`;
        seriesColor = 'green';
      }
      break;
    case 'Volume Flow':
      let volFlow = createFilledArray(chartTime.length, 0);
      let count = 0;
      for (const metrics of Object.values(sectorMetrics)) {
        for (let i = 0; i < metrics.viZScore.length; i++) {
          if (metrics.viZScore[i] != null) {
            volFlow[i] += metrics.viZScore[i];
          }
        }
        count++;
      }
      primarySeries = volFlow.map(v => count > 0 ? v / count : 0);
      seriesName = 'Aggregate Volume Flow';
      seriesColor = 'blue';
      break;
    case 'Combined Signal':
      if (rankings.length > 0 && sectorMetrics[rankings[0].ticker]) {
        primarySeries = sectorMetrics[rankings[0].ticker].combined;
        seriesName = `${rankings[0].ticker} Combined Signal`;
        seriesColor = 'orange';
      }
      break;
  }
}

/* =========================  Generate Rotation Signals  ========================= */
// Simple rotation signal detection
const rotationSignal = [];
for (let i = 0; i < rotationScore.length; i++) {
  if (i < 2) {
    rotationSignal.push(null);
    continue;
  }
  
  const avgVal = (rotationScore[i] + rotationScore[i-1]) / 2;
  if (Math.abs(avgVal) > sectorList.length * 0.3) {
    rotationSignal.push(avgVal > 0 ? 1 : -1);
  } else {
    rotationSignal.push(0);
  }
}

/* =========================  ALWAYS PAINT EVERYTHING  ========================= */

// Main series - ALWAYS painted
paint(primarySeries, { name: seriesName, color: seriesColor, thickness: 3});

// Horizontal lines - ALWAYS painted
paint(horizontal_line(0), { name: "Neutral", color: "gray", style: "dotted" });
paint(horizontal_line(rotationThreshold), { name: "Upper Threshold", color: "green", style: "dotted" });
paint(horizontal_line(-rotationThreshold), { name: "Lower Threshold", color: "red", style: "dotted" });

/* =========================  Signals  ========================= */
const bullishRotation = for_every(rotationSignal, s => s === 1 ? 1 : null);
const bearishRotation = for_every(rotationSignal, s => s === -1 ? 1 : null);

register_signal(bullishRotation, 'Risk-On Rotation');
register_signal(bearishRotation, 'Risk-Off Rotation');

/* =========================  Build Dashboard Content  ========================= */

const lastIdx = time.length - 1;
const currentRotation = rotationScore[lastIdx] || 0;

// Determine market regime
let regimeText = 'NEUTRAL';
let regimeSymbol = '◆';
let regimeColor = '#808080';
let interpretText = hasError ? errorMessage : 'Balanced sector participation';

if (!hasError) {
  if (currentRotation >= 3) {
    regimeText = 'STRONG RISK-ON';
    regimeSymbol = '🚀';
    regimeColor = '#00FF88';
    interpretText = 'Broad sector strength';
  } else if (currentRotation >= 2) {
    regimeText = 'MODERATE RISK-ON';
    regimeSymbol = '📈';
    regimeColor = '#00A8E1';
    interpretText = 'Multiple sectors advancing';
  } else if (currentRotation >= 1) {
    regimeText = 'MILD RISK-ON';
    regimeSymbol = '↗️';
    regimeColor = '#87CEEB';
    interpretText = 'Selective sector strength';
  } else if (currentRotation <= -3) {
    regimeText = 'STRONG RISK-OFF';
    regimeSymbol = '⚠️';
    regimeColor = '#FC3D21';
    interpretText = 'Broad sector weakness';
  } else if (currentRotation <= -2) {
    regimeText = 'MODERATE RISK-OFF';
    regimeSymbol = '📉';
    regimeColor = '#FF6B35';
    interpretText = 'Multiple sectors declining';
  } else if (currentRotation <= -1) {
    regimeText = 'MILD RISK-OFF';
    regimeSymbol = '↘️';
    regimeColor = '#FFB347';
    interpretText = 'Selective sector weakness';
  }
}

// Build dashboard rows - ALWAYS build the structure
dashboardRows = [
  {
    cells: [{
      text: 'SECTOR ROTATION',
      color: '#FFFFFF',
      textAlign: 'center',
      fontWeight: 'bold',
      fontSize: 11,
      padding: 4
    }]
  },
  {
    cells: [{
      text: `${regimeSymbol} ${regimeText}`,
      color: regimeColor,
      textAlign: 'center',
      fontWeight: 'bold',
      fontSize: 12,
      padding: 4
    }]
  },
  {
    cells: [{
      text: interpretText,
      color: '#FFFFFF',
      textAlign: 'center',
      fontSize: 9,
      padding: 2
    }]
  },
  {
    cells: [{
      text: `Score: ${currentRotation.toFixed(1)} / ${sectorList.length}`,
      color: '#FFFFFF',
      textAlign: 'center',
      fontSize: 10,
      padding: 3
    }]
  }
];

// Add sector info only if we have data
if (!hasError && rankings.length > 0) {
  const topRanked = rankings[0];
  const bottomRanked = rankings[rankings.length - 1];
  
  dashboardRows.push(
    {
      cells: [{
        text: '━━━━━━━━━━━━━━━',
        color: '#606060',
        textAlign: 'center',
        fontSize: 8,
        padding: 2
      }]
    },
    {
      cells: [{
        text: 'LEADING',
        color: '#00A8E1',
        textAlign: 'center',
        fontSize: 9
      }]
    },
    {
      cells: [{
        text: `${topRanked.ticker}: ${topRanked.score.toFixed(2)}`,
        color: '#00FF88',
        textAlign: 'center',
        fontSize: 10
      }]
    },
    {
      cells: [{
        text: 'LAGGING',
        color: '#FF6B35',
        textAlign: 'center',
        fontSize: 9
      }]
    },
    {
      cells: [{
        text: `${bottomRanked.ticker}: ${bottomRanked.score.toFixed(2)}`,
        color: '#FC3D21',
        textAlign: 'center',
        fontSize: 10
      }]
    }
  );
}

/* =========================  ALWAYS PAINT OVERLAYS  ========================= */

// Dashboard panel - ALWAYS painted
paint_overlay('ROTATION_DASHBOARD',
  { position: 'center_right' },
  {
    background: '#1a1a2eDD',
    border: `2px solid ${regimeColor}`,
    borderRadius: 6,
    padding: 4,
    rows: dashboardRows
  }
);

// Info display - ALWAYS painted
const topSectors = rankings.slice(0, 3).map(r => r.ticker).join(', ') || 'N/A';
const bottomSectors = rankings.slice(-3).map(r => r.ticker).join(', ') || 'N/A';

paint_overlay('overlay', { position: 'bottom_right' }, {
  rows: [{
    cells: [
      { text: `Leading: ${topSectors}`, color: 'green', border: 'solid var(--border-color) 1px', padding: 5 },
      { text: `Lagging: ${bottomSectors}`, color: 'red', border: 'solid var(--border-color) 1px', padding: 5 },
      { text: `Rotation: ${currentRotation.toFixed(1)}`, 
        color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5 },
      { text: `Tracking: ${sectorList.length} sectors`, 
        color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5 }
    ]
  }]
});</code>