<code x-ref="code" class="hljs" data-clipboard-text>﻿describe_indicator('Daily Pivot Breakout');


// ===== Input Parameters =====
const leftStrength = input.number('Left Strength', 5, { min: 1 });
const rightStrength = input.number('Right Strength', 5, { min: 1 });
const pivotLookback = input.number('Pivot Lookback', 100, { min: 1 });
const rocPeriod = input.number('ROC Period (days)', 100, { min: 1 });
const minimumROC = input.number('Minimum ROC (%)', 30, { min: 0 });
const rvolPeriod = input.number('RVOL Period (days)', 20, { min: 1 });
const minimumRVOL = input.number('Minimum Daily RVOL (0 = Off)', 1, { min: 0 });
const emaLength = input.number('EMA Length', 100, { min: 1, max: 2000 });
const slopeLookback = input.number('EMA Slope Lookback', 100, { min: 1, max: 2000 });
const smoothLen = input.number('EMA Smooth Length', 1, { min: 1, max: 200 });
const minimumEmaSlope = input.number('Min EMA Slope %', 20, { min: -100 });
const trailingStopPercent = input.number('Trailing Stop Percent', 20, { min: 0.1, max: 99 });
const trailingStopMultiplier = 1 - trailingStopPercent / 100;
const enableCandleColors = input.boolean('Enable Momentum Candle Colors', true);


// ===== Request Daily Data =====
const dailyData = await request.history(current.ticker, 'D');
assert(!dailyData.error, `Error fetching daily data: ${dailyData.error}`);
assert(dailyData.close.length >= Math.max(rocPeriod, rvolPeriod, pivotLookback), 
    `Insufficient daily data. Need at least ${Math.max(rocPeriod, rvolPeriod, pivotLookback)} days`);


// ===== Daily Filter Calculations =====
// ROC calculation on daily data
const dailyROC = series_of(0);
for (let i = rocPeriod; i < dailyData.close.length; i++) {
    if (dailyData.close[i - rocPeriod] !== 0) {
        dailyROC[i] = ((dailyData.close[i] - dailyData.close[i - rocPeriod]) / dailyData.close[i - rocPeriod]) * 100;
    } else {
        dailyROC[i] = 0;
    }
}


// ===== EMA Slope % Filter (ROC on EMA, optionally smoothed) =====
// Step 1: Calculate EMA on daily close
const dailyEMA = series_of(null);
let emaMultiplier = 2 / (emaLength + 1);
for (let i = 0; i < dailyData.close.length; i++) {
    if (i === 0) {
        dailyEMA[i] = dailyData.close[i];
    } else {
        dailyEMA[i] = (dailyData.close[i] - dailyEMA[i - 1]) * emaMultiplier + dailyEMA[i - 1];
    }
}


// Step 2: Calculate raw EMA slope % (ROC on EMA)
const dailyEmaSlope = series_of(null);
for (let i = slopeLookback; i < dailyData.close.length; i++) {
    const pastEMA = dailyEMA[i - slopeLookback];
    const currEMA = dailyEMA[i];
    if (pastEMA !== null && pastEMA !== 0 && currEMA !== null) {
        dailyEmaSlope[i] = ((currEMA - pastEMA) / pastEMA) * 100;
    }
}


// Step 3: Smooth the EMA slope using SMA
const dailyEmaSlopeSmoothed = series_of(null);
for (let i = slopeLookback + smoothLen - 1; i < dailyData.close.length; i++) {
    let slopeTotal = 0;
    let slopeCount = 0;
    for (let j = i - smoothLen + 1; j <= i; j++) {
        if (dailyEmaSlope[j] !== null) {
            slopeTotal += dailyEmaSlope[j];
            slopeCount++;
        }
    }
    if (slopeCount === smoothLen) {
        dailyEmaSlopeSmoothed[i] = slopeTotal / smoothLen;
    }
}


// ===== Daily Momentum Color State Series =====
// Determines candle color based on combined daily ROC and EMA slope states
// Colors are assigned per daily bar and later mapped to chart timeframe
const dailyColorState = series_of(null);
for (let i = 0; i < dailyData.close.length; i++) {
    const rocVal = dailyROC[i];
    const emaVal = dailyEmaSlopeSmoothed[i];


    // Determine individual states
    const rocBull = rocVal >= minimumROC;
    const rocBear = rocVal <= -minimumROC;
    // rocNeutral = neither bull nor bear


    const emaHasVal = emaVal !== null && emaVal !== undefined;
    const emaBull = emaHasVal && emaVal >= minimumEmaSlope;
    const emaBear = emaHasVal && emaVal <= -minimumEmaSlope;
    // emaNeutral = null or neither bull nor bear


    // Combine into final color
    if (rocBull && emaBull) {
        dailyColorState[i] = '#16C172';   // Both bullish
    } else if (rocBear && emaBear) {
        dailyColorState[i] = '#FF3B30';   // Both bearish
    } else if (rocBull && emaBear || rocBear && emaBull) {
        dailyColorState[i] = '#AF52DE';   // Mixed (one bullish + one bearish)
    } else if (rocBull || emaBull) {
        dailyColorState[i] = '#00BCFF';   // One bullish, other neutral
    } else if (rocBear || emaBear) {
        dailyColorState[i] = '#FF9F0A';   // One bearish, other neutral
    } else {
        dailyColorState[i] = '#8E8E93';   // Both neutral
    }
}


// RVOL calculation on daily data
const dailyRVOL = series_of(0);
for (let i = rvolPeriod; i < dailyData.volume.length; i++) {
    const avgVolume = dailyData.volume.slice(i - rvolPeriod, i).reduce((sum, vol) => sum + vol, 0) / rvolPeriod;
    if (avgVolume !== 0) {
        dailyRVOL[i] = dailyData.volume[i] / avgVolume;
    } else {
        dailyRVOL[i] = 0;
    }
}


// ===== Daily Pivot High Detection (Exact TrendSpider Logic) =====
function isDailyPivotHigh(idx) {
    if (idx - leftStrength < 0 || idx + rightStrength >= dailyData.high.length) return false;
    const ph = dailyData.high[idx];
    for (let j = idx - leftStrength; j <= idx + rightStrength; j++) {
        if (j === idx) continue;
        if (ph <= dailyData.high[j]) return false;
    }
    return true;
}


// Find all daily pivot highs
const dailySwingHigh = series_of(null);
const dailySwingHighBarIndex = series_of(null);


for (let b = 0; b < dailyData.high.length; b++) {
    if (isDailyPivotHigh(b)) {
        dailySwingHigh[b] = dailyData.high[b];
        dailySwingHighBarIndex[b] = b;
    }
}


// ===== Daily Strategy Logic (Exact EasyLanguage Logic) =====
const dailySignals = series_of(false);


// Get most recent confirmed pivot (like PivotHighVS(1, ...))
function getMostRecentPivot(currentBar) {
    for (let lookback = rightStrength; lookback <= Math.min(pivotLookback, currentBar); lookback++) {
        const pivotBar = currentBar - lookback;
        if (pivotBar >= 0 && dailySwingHigh[pivotBar] !== null) {
            return dailySwingHigh[pivotBar];
        }
    }
    return null;
}


let lastPivotHigh = null;
let firedForPivot = false;


// Main loop on daily data
for (let i = 1; i < dailyData.close.length; i++) {
    // Get current confirmed pivot (equivalent to PivotHighVS)
    const ph = getMostRecentPivot(i);
    
    // Reset fired flag when pivot changes (like EasyLanguage)
    if (ph !== null && ph !== -1 && ph !== lastPivotHigh) {
        lastPivotHigh = ph;        // latest confirmed pivot-high (price)
        firedForPivot = false;     // allow a fresh entry on this new pivot
    }


    // TRUE BREAKOUT LOGIC: exactly like EasyLanguage
    if (lastPivotHigh !== null && lastPivotHigh > 0 &&
        dailyData.close[i - 1] <= lastPivotHigh &&  // Close[1] <= lastPivotHigh
        dailyData.close[i] > lastPivotHigh &&       // Close > lastPivotHigh
        !firedForPivot) {                           // not firedForPivot
        
        // Check filters
        const rocFilter = dailyROC[i] >= minimumROC;  // ROC >= MinimumROC
        const emaSlopeFilter = dailyEmaSlopeSmoothed[i] !== null && dailyEmaSlopeSmoothed[i] >= minimumEmaSlope; // EMA Slope %
        const rvolFilter = minimumRVOL <= 0 || dailyRVOL[i] > minimumRVOL;
        const momentumFilter = rocFilter || emaSlopeFilter; // OR logic between momentum filters
        
        if (momentumFilter && rvolFilter) {
            dailySignals[i] = true;
            firedForPivot = true;                     // block re-entry on this pivot
        }
    }
}


// Create pivot price series for visualization
const dailyPivPrice = series_of(null);
for (let i = 0; i < dailyData.close.length; i++) {
    dailyPivPrice[i] = getMostRecentPivot(i);
}


// ===== Adjustable Trailing Stop Logic (Daily Data, No Repainting) =====
const dailyStopLevel = series_of(null);


// Track a single active position
let activePosition = {
    isActive: false,
    entryBar: null,
    entryPrice: null,
    highestPrice: null,
    stopLevel: null,
    stopHitBar: null
};


// Loop through all bars including current (uses i-1 for prices to prevent repainting)
for (let i = 1; i < dailyData.close.length; i++) {
    // Check if previous bar had entry signal (entry executes on bar i, signal on bar i-1)
    if (dailySignals[i - 1] === true && !activePosition.isActive) {
        // Start new position on entry day (day after signal)
        activePosition.isActive = true;
        activePosition.entryBar = i;
        activePosition.entryPrice = dailyData.open[i];
        activePosition.highestPrice = dailyData.open[i];  // Start with entry bar's open
        activePosition.stopLevel = activePosition.highestPrice * trailingStopMultiplier; // Initial stop
        activePosition.stopHitBar = null;
    }
    
    // Update active position
    if (activePosition.isActive) {
        const isEntryBar = (i === activePosition.entryBar);
        
        // STEP 1: Check if PREVIOUS bar hit the stop level that existed at that time
        // (Stop level is based on data BEFORE bar i-1)
        if (!isEntryBar && activePosition.stopHitBar === null) {
            if (dailyData.low[i - 1] <= activePosition.stopLevel) {
                activePosition.stopHitBar = i - 1; // Mark the bar that actually hit (previous bar)
            }
        }
        
        // STEP 2: Update highest price and trail stop for NEXT bar
        // Only update if stop wasn't hit
        if (activePosition.stopHitBar === null) {
            if (dailyData.high[i - 1] > activePosition.highestPrice) {
                activePosition.highestPrice = dailyData.high[i - 1];
                activePosition.stopLevel = activePosition.highestPrice * trailingStopMultiplier; // Trail up
            }
        }
        
        // Paint stop level until one day after stop hit
        if (activePosition.stopHitBar === null || i <= activePosition.stopHitBar + 1) {
            dailyStopLevel[i] = activePosition.stopLevel;
        } else {
            // Explicitly clear stop line after the grace period
            dailyStopLevel[i] = null;
        }
        
        // Deactivate position one day after stop hit (allow new entries)
        if (activePosition.stopHitBar !== null && i > activePosition.stopHitBar + 1) {
            activePosition.isActive = false;
        }
    }
}


// ===== Map Results to Current Timeframe =====
const mappedPivotPrice = interpolate_sparse_series(
    land_points_onto_series(dailyData.time, dailyPivPrice, time, 'le'), 
    'constant'
);


// Map trailing stop to current timeframe (no interpolation to prevent forward-fill)
const mappedTrailingStop = land_points_onto_series(dailyData.time, dailyStopLevel, time, 'le');


// Map daily color state to current timeframe using 'le' (same day alignment, no repainting)
const mappedCandleColor = interpolate_sparse_series(
    land_points_onto_series(dailyData.time, dailyColorState, time, 'le'),
    'constant'
);


// ===== NEW: Day-0 signal (no shift) =====
const mappedSignals_Day0 = land_points_onto_series(dailyData.time, dailySignals, time, 'le');


// Shift daily signals forward by 1 day for next-day execution
const dailySignalsNextDay = series_of(false);
for (let i = 0; i < dailyData.time.length - 1; i++) {
    if (dailySignals[i] === true) {
        dailySignalsNextDay[i + 1] = true; // Signal fires NEXT day
    }
}


// Map the shifted signals to 5-minute timeframe
const mappedSignals = land_points_onto_series(dailyData.time, dailySignalsNextDay, time, 'le');


// ===== Generate 5-Minute Entry Signals =====
const entrySignals = series_of(null);
const entryLabels = series_of(null);


// Only place signals on the first 5-minute candle of each day
for (let i = 1; i < time.length; i++) {
    if (mappedSignals[i] === true) {
        // Check if this is the first candle of a new day
        const currentTime = time[i];
        const prevTime = time[i - 1];
        const currentDayStart = Math.floor(currentTime / (24 * 60 * 60)) * (24 * 60 * 60);
        const prevDayStart = Math.floor(prevTime / (24 * 60 * 60)) * (24 * 60 * 60);
        const isFirstCandleOfDay = currentDayStart > prevDayStart;
        
        if (isFirstCandleOfDay) {
            entrySignals[i] = true;
            entryLabels[i] = '▲ Breakout';
        }
    }
}


// ===== Visual Elements =====
// Paint pivot high line
paint(mappedPivotPrice, {
    name: 'Pivot High',
    color: '#16c172',
    style: 'line',
    width: 2,
    ignoreWhenScaling: true  // Don't extend chart Y-axis range
});


// Paint adjustable trailing stop line
paint(mappedTrailingStop, {
    name: 'Trailing Stop',
    color: '#00BCFF',
    style: 'dotted',
    thickness: 2,
    ignoreWhenScaling: true
});


// Paint entry signals with arrows
paint(entryLabels, {
    name: 'Entry Signals',
    style: 'labels_below',
    color: 'green',
    backgroundColor: 'green',
    fontSize: 14,
    verticalOffset: 15,
    ignoreWhenScaling: true
});


// Apply candle coloring if enabled
if (enableCandleColors) {
    color_candles(mappedCandleColor);
}


// ===== Register Signals =====
// Strategy: shifted entry day on the first five-minute bar
// Scan: unshifted daily breakout signal
register_signal(entrySignals, '5PivotBreakout_Strategy');
register_signal(mappedSignals_Day0, '5PivotBreakout_Scan');</code>