<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Mark Minervini Trend Template Candles');

// Toggle for overlay table
const showTable = input.boolean('Show Criteria Table', true);

// Discrete neon color scale - one color per score
const colorPalette = [
  '#FF1A1A', // 1 criteria (neon red - extreme worst)
  '#FF4D1A', // 2 criteria (bright red-orange)
  '#FF751A', // 3 criteria (strong orange)
  '#FF9933', // 4 criteria (warm amber-orange)
  '#FFB84D', // 5 criteria (golden orange)
  '#FFD966', // 6 criteria (light yellow-orange)
  '#99CCFF', // 7 criteria (brighter powder blue)
  '#66B2FF', // 8 criteria (vivid medium blue)
  '#3399FF', // 9 criteria (bright azure blue)
  '#00F2FE'  // 10 criteria (neon cyan - extreme best)
];

/* ===================== COMPUTE NATIVE TIMEFRAME INDICATORS ===================== */
// Calculate all indicators on native chart timeframe data
const nativeSMA50 = sma(close, 50);
const nativeSMA150 = sma(close, 150);
const nativeSMA200 = sma(close, 200);
// Fetch weekly data for 52-week high/low (gets much longer history than daily)
const weeklyDataFor52Week = await request.history(current.ticker, 'W');
assert(!weeklyDataFor52Week.error, `Error fetching weekly data: ${weeklyDataFor52Week.error}`);

// Calculate 52-week high/low using 52 weeks of weekly data (conceptually perfect)
const weekly52WeekHigh = highest(weeklyDataFor52Week.high, 52);
const weekly52WeekLow = lowest(weeklyDataFor52Week.low, 52);

// Map weekly 52-week high/low to chart timeframe
const native52WeekHigh = interpolate_sparse_series(
    land_points_onto_series(weeklyDataFor52Week.time, weekly52WeekHigh, time, 'le'), 
    'constant'
);
const native52WeekLow = interpolate_sparse_series(
    land_points_onto_series(weeklyDataFor52Week.time, weekly52WeekLow, time, 'le'), 
    'constant'
);

const nativeSMA200Shifted = shift(nativeSMA200, 30);

// Fetch RP data and interpolate from weekly to work across all timeframes
let nativeRP = series_of(null);
const relativePerformanceData = await request.relative_performance(current.ticker, 'yearly', 'spx500');
if (!relativePerformanceData.error && relativePerformanceData.length > 0) {
    const rpValues = relativePerformanceData.map(_dataPoint => _dataPoint[1]);
    const rpTimes = relativePerformanceData.map(_dataPoint => _dataPoint[0]);
    // Land weekly RP data to chart timeframe and interpolate to fill gaps
    nativeRP = interpolate_sparse_series(
        land_points_onto_series(rpTimes, rpValues, time, 'le'), 
        'constant'
    );
}

/* ===================== COMPUTE NATIVE TIMEFRAME MINERVINI SCORES ===================== */
// Compute scores on native chart timeframe data with partial scoring
const nativeScores = for_every(
    close, nativeSMA50, nativeSMA150, nativeSMA200,
    native52WeekHigh, native52WeekLow, nativeRP, nativeSMA200Shifted,
    (currentClose, sma50, sma150, sma200, high52, low52, rp, sma200_30_ago) => {
        // Never return null for whole bar - compute partial scores
        let score = 0;
        
        // Guard each criterion individually
        if (rp !== null && rp > 70) score++;                           // 1. RP > 70
        if (currentClose !== null && sma50 !== null && currentClose > sma50) score++;        // 2. Close > SMA50
        if (currentClose !== null && sma150 !== null && currentClose > sma150) score++;      // 3. Close > SMA150
        if (currentClose !== null && sma200 !== null && currentClose > sma200) score++;      // 4. Close > SMA200
        if (sma50 !== null && sma150 !== null && sma50 > sma150) score++;               // 5. SMA50 > SMA150
        if (sma50 !== null && sma200 !== null && sma50 > sma200) score++;               // 6. SMA50 > SMA200
        if (sma150 !== null && sma200 !== null && sma150 > sma200) score++;             // 7. SMA150 > SMA200
        if (currentClose !== null && low52 !== null && currentClose >= low52 * 1.30) score++;    // 8. Close ≥ 1.30 × 52wLow
        if (currentClose !== null && high52 !== null && currentClose >= high52 * 0.75) score++;  // 9. Close ≥ 0.75 × 52wHigh
        if (sma200 !== null && sma200_30_ago !== null && sma200 > sma200_30_ago) score++;    // 10. Rising SMA200
        
        return score;
    }
);

// Gradient helpers (kept for future use)
function clamp01(t) { return Math.max(0, Math.min(1, t)); }
function hex_to_rgb(hex) {
    const h = hex.replace('#','');
    const r = parseInt(h.substring(0,2), 16);
    const g = parseInt(h.substring(2,4), 16);
    const b = parseInt(h.substring(4,6), 16);
    return { r, g, b };
}
function rgb_to_hex(r, g, b) {
    const to2 = (n) => {
        const s = Math.round(Math.max(0, Math.min(255, n))).toString(16).toUpperCase();
        return s.length === 1 ? '0' + s : s;
    };
    return '#' + to2(r) + to2(g) + to2(b);
}
function lerp_color(c1, c2, t) {
    const a = hex_to_rgb(c1), b = hex_to_rgb(c2);
    const r = a.r + (b.r - a.r) * t;
    const g = a.g + (b.g - a.g) * t;
    const bl = a.b + (b.b - a.b) * t;
    return rgb_to_hex(r, g, bl);
}
function color_from_gradient(v, lo, hi, cLo, cHi) {
    if (v == null || lo == null || hi == null) return null;
    const t = clamp01((v - lo) / (hi - lo));
    return lerp_color(cLo, cHi, t);
}

/* ===================== MAP NATIVE SCORES TO COLORS ===================== */
// Map native scores to discrete colors with backfill for early nulls
const nativeColors = for_every(nativeScores, (score, prev, i) => {
    if (score === null) {
        // Backfill early nulls with worst color
        return i === 0 ? colorPalette[0] : prev;
    }
    
    // Direct mapping: score 0-10 to color palette
    if (score >= 1 && score <= 10) {
        return colorPalette[score - 1]; // score 1 → index 0, score 10 → index 9
    }
    
    // Score 0 gets worst color
    return colorPalette[0];
});


/* ===================== COLOR CANDLES DIRECTLY ===================== */
// Color candles directly using native timeframe data
color_candles(nativeColors);

/* ===================== SIGNALS BASED ON NATIVE TIMEFRAME ===================== */
// Register signals based on native scores - no landing needed
register_signal(for_every(nativeScores, score => score !== null && score === 10), 'Meets All 10 Trend Template Criteria');
register_signal(for_every(nativeScores, score => score !== null && score >= 9), '9+ Criteria Met');
register_signal(for_every(nativeScores, score => score !== null && score >= 8), '8+ Criteria Met');
register_signal(for_every(nativeScores, score => score !== null && score >= 7), '7+ Criteria Met');
register_signal(for_every(nativeScores, score => score !== null && score >= 6), '6+ Criteria Met');
register_signal(for_every(nativeScores, score => score !== null && score >= 5), '5+ Criteria Met');
register_signal(for_every(nativeScores, score => score !== null && score >= 4), '4+ Criteria Met');
register_signal(for_every(nativeScores, score => score !== null && score >= 3), '3+ Criteria Met');
register_signal(for_every(nativeScores, score => score !== null && score >= 2), '2+ Criteria Met');
register_signal(for_every(nativeScores, score => score !== null && score >= 1), '1+ Criteria Met');

/* ===================== PAINT NATIVE SMAS ===================== */
// Paint native timeframe SMAs directly
paint(nativeSMA50, { name: 'SMA 50', color: 'yellow' });
paint(nativeSMA150, { name: 'SMA 150', color: 'orange' });
paint(nativeSMA200, { name: 'SMA 200', color: 'red' });

/* ===================== OVERLAY TABLE ===================== */
// Get current values for table using native timeframe data
const currentCriteria = nativeScores[nativeScores.length - 1];
const currentClose = close[close.length - 1];
const currentSMA50 = nativeSMA50[nativeSMA50.length - 1];
const currentSMA150 = nativeSMA150[nativeSMA150.length - 1];
const currentSMA200 = nativeSMA200[nativeSMA200.length - 1];
const currentHigh52 = native52WeekHigh[native52WeekHigh.length - 1];
const currentLow52 = native52WeekLow[native52WeekLow.length - 1];
const currentRP = nativeRP[nativeRP.length - 1];
const currentSMA200Shifted = nativeSMA200Shifted[nativeSMA200Shifted.length - 1];

// Helper functions for table styling
const headCell = text => ({ text: `${text}`, fontWeight: 'bold', color: 'var(--text-color)', padding: '1px 5px' });
const valueCell = text => ({ text: `${text}`, color: 'var(--text-color)', padding: '3px 7px', textAlign: 'right' });
const coloredValueCell = (text, isPositive) => ({ 
    text: `${text}`, 
    color: isPositive ? '#2ecc53' : '#e74c3c', 
    padding: '3px 7px', 
    textAlign: 'right',
    fontWeight: 'bold'
});
const leftTitleCell = text => ({ text: `${text}`, fontWeight: 'bold', color: 'var(--text-color)', padding: '1px 7px', width: '70%', textAlign: 'left' });
const statusCell = (text, isMet) => ({ 
    text: `${text}`, 
    color: isMet ? '#2ecc53' : '#e74c3c', 
    textAlign: 'right', 
    padding: '1px 7px', 
    width: '30%',
    fontWeight: 'bold'
});

const SEPARATOR = { cells: [{ text: "", colspan: 2, borderBottom: '1px solid var(--border-color)' }] };

// Evaluate current criteria status
const criteriaStatus = {
    rp: currentRP !== null && currentRP > 70,
    priceAbove50: currentClose !== null && currentSMA50 !== null && currentClose > currentSMA50,
    priceAbove150: currentClose !== null && currentSMA150 !== null && currentClose > currentSMA150,
    priceAbove200: currentClose !== null && currentSMA200 !== null && currentClose > currentSMA200,
    sma50Above150: currentSMA50 !== null && currentSMA150 !== null && currentSMA50 > currentSMA150,
    sma50Above200: currentSMA50 !== null && currentSMA200 !== null && currentSMA50 > currentSMA200,
    sma150Above200: currentSMA150 !== null && currentSMA200 !== null && currentSMA150 > currentSMA200,
    price30AboveLow: currentClose !== null && currentLow52 !== null && currentClose >= currentLow52 * 1.30,
    priceWithin25High: currentClose !== null && currentHigh52 !== null && currentClose >= currentHigh52 * 0.75,
    sma200Rising: currentSMA200 !== null && currentSMA200Shifted !== null && currentSMA200 > currentSMA200Shifted
};

// Calculate total criteria met based on RP availability
const totalMet = Object.values(criteriaStatus).filter(Boolean).length;
const maxCriteria = 10;

// Only show table if showTable is enabled
if (showTable) {
    paint_overlay('Minervini Criteria Table', { position: 'top_right', order: 'above_all' }, {
    fontSize: 12,
    border: '1px solid var(--border-color)',
    background: 'var(--background-color)',
    width: '280px',
    rows: [{
        cells: [{ colspan: 2, text: `Minervini Trend Template (${current.resolution}) - ${totalMet}/${maxCriteria}${currentRP === null ? ' (RP N/A)' : ''}`, color: 'var(--text-color)', padding: '3px 7px', textAlign: 'center', fontWeight: 'bold' }]
    }, {
        cells: [SEPARATOR]
    }, {
        cells: [leftTitleCell('RP > 70'), currentRP !== null ? statusCell(criteriaStatus.rp ? '✓' : '✗', criteriaStatus.rp) : valueCell('N/A')]
    }, {
        cells: [leftTitleCell('Price > SMA 50'), statusCell(criteriaStatus.priceAbove50 ? '✓' : '✗', criteriaStatus.priceAbove50)]
    }, {
        cells: [leftTitleCell('Price > SMA 150'), statusCell(criteriaStatus.priceAbove150 ? '✓' : '✗', criteriaStatus.priceAbove150)]
    }, {
        cells: [leftTitleCell('Price > SMA 200'), statusCell(criteriaStatus.priceAbove200 ? '✓' : '✗', criteriaStatus.priceAbove200)]
    }, {
        cells: [leftTitleCell('SMA 50 > SMA 150'), statusCell(criteriaStatus.sma50Above150 ? '✓' : '✗', criteriaStatus.sma50Above150)]
    }, {
        cells: [leftTitleCell('SMA 50 > SMA 200'), statusCell(criteriaStatus.sma50Above200 ? '✓' : '✗', criteriaStatus.sma50Above200)]
    }, {
        cells: [leftTitleCell('SMA 150 > SMA 200'), statusCell(criteriaStatus.sma150Above200 ? '✓' : '✗', criteriaStatus.sma150Above200)]
    }, {
        cells: [leftTitleCell('Price 30% > 52W Low'), statusCell(criteriaStatus.price30AboveLow ? '✓' : '✗', criteriaStatus.price30AboveLow)]
    }, {
        cells: [leftTitleCell('Price w/in 25% of 52W High'), statusCell(criteriaStatus.priceWithin25High ? '✓' : '✗', criteriaStatus.priceWithin25High)]
    }, {
        cells: [leftTitleCell('SMA 200 Rising'), statusCell(criteriaStatus.sma200Rising ? '✓' : '✗', criteriaStatus.sma200Rising)]
    }, {
        cells: [SEPARATOR]
    }, {
        cells: [{ colspan: 2, text: `Current Values:`, color: 'var(--text-color)', padding: '2px 7px', fontWeight: 'bold' }]
    }, {
        cells: [leftTitleCell('RP'), valueCell(currentRP ? currentRP.toFixed(1) : 'N/A')]
    }, {
        cells: [leftTitleCell('Price vs 52W High'), currentClose && currentHigh52 ? (() => {
            const pct = ((currentClose / currentHigh52 - 1) * 100);
            const isPositive = pct >= 0;
            return coloredValueCell(`${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`, isPositive);
        })() : valueCell('N/A')]
    }, {
        cells: [leftTitleCell('Price vs 52W Low'), currentClose && currentLow52 ? (() => {
            const pct = ((currentClose / currentLow52 - 1) * 100);
            const isPositive = pct >= 0;
            return coloredValueCell(`${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`, isPositive);
        })() : valueCell('N/A')]
    }]
    });
}
</code>