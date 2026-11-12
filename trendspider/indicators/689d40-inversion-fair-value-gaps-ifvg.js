<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Inversion Fair Value Gaps (IFVG)', 'price', { shortName: 'IFVG' });

// =============================================================================


// Inputs
const disp_num = input.number('Show Last', 5, { min: 1, max: 100 });
const useWickRetest = input.boolean('Use Wick for Signals', false);
const atr_multi = input.number('ATR Multiplier', 0.25, { min: 0, max: 10, step: 0.25 });
const proj_len = input.number('Projection Bars', 50, { min: 0, max: 200 });

// Optional features
const showSeeds = input.boolean('Show Pre-Inversion Seeds?', false);
const showInversionDots = input.boolean('Show Inversion Points?', true);
const extendZones = input.boolean('Extend Active Zones?', true);
const showMidlines = input.boolean('Show Zone Midlines?', true);
// NEW: optional color mode that paints zones by supply/demand location relative to current price
const colorByLocation = input.boolean('Color Zones by Location (Above Price = Red, Below = Green)?', false);

// Session gap filtering (for stocks)
const filterSessionGaps = input.boolean('Filter Session Gaps?', true);
const sessionGapThreshold = input.number('Session Gap Threshold %', 0.1, { min: 0, max: 5, step: 0.1 });

// Colors
const green = '#08998150';  // Bullish color with transparency
const red = '#f2364550';    // Bearish color with transparency
const midCol = '#787b86';   // Midline color

// Data validation
if (!high || !low || !open || !close || close.length < 3) {
    console.error('Insufficient price data - need at least 3 bars');
}

// Body high/low calculations
const c_top = high.map((_, i) => {
    if (open[i] == null || close[i] == null) return null;
    return Math.max(open[i], close[i]);
});
const c_bot = low.map((_, i) => {
    if (open[i] == null || close[i] == null) return null;
    return Math.min(open[i], close[i]);
});

// ATR calculation
const atr200 = atr(200);
const minWidth = series_of(null);
let cumulativeRange = 0;

for (let i = 0; i < close.length; i++) {
    if (high[i] != null && low[i] != null && high[i] >= low[i]) {
        cumulativeRange += (high[i] - low[i]);
    }

    const atrValue = (atr200[i] !== null && atr200[i] !== undefined && atr200[i] > 0) ?
        atr200[i] :
        (cumulativeRange / (i + 1));

    minWidth[i] = Math.max(0, atrValue * atr_multi);
}

// Data structures
const BUFFER = 100;
let bulls = [];
let bears = [];
let bullInv = [];
let bearInv = [];

// Signal series
const bullRet = series_of(false);
const bearRet = series_of(false);
const inversionDots = series_of(null);

// Optional seed visualization
const seedTop = series_of(null);
const seedBot = series_of(null);

// Simple drawing approach - pre-allocate series for zones
const maxZones = Math.min(disp_num * 2, 15); // Reasonable limit
const preTopSeries = [];
const preBotSeries = [];
const postTopSeries = [];
const postBotSeries = [];
const midSeries = [];

// Initialize drawing series
for (let k = 0; k < maxZones; k++) {
    preTopSeries[k] = series_of(null);
    preBotSeries[k] = series_of(null);
    postTopSeries[k] = series_of(null);
    postBotSeries[k] = series_of(null);
    midSeries[k] = series_of(null);
}

// Debug counters
let debugCounters = {
    bullFVGsDetected: 0,
    bearFVGsDetected: 0,
    bullInversions: 0, // Originally bullish FVGs that inverted (moved to bullInv)
    bearInversions: 0, // Originally bearish FVGs that inverted (moved to bearInv)
    bullSignals: 0,
    bearSignals: 0,
    zonesInvalidated: 0,
    sessionGapsFiltered: 0
};

// Validation function
function validateFVG(fvg) {
    return fvg &&
        typeof fvg.left === 'number' && fvg.left >= 0 &&
        typeof fvg.top0 === 'number' && typeof fvg.bot0 === 'number' &&
        fvg.top0 > fvg.bot0 &&
        Math.abs(fvg.mid0 - (fvg.top0 + fvg.bot0) / 2) < 0.0001;
}

// Helper function to detect session gaps (overnight gaps in stocks)
function isSessionGap(currentBar, prevBar) {
    // If filtering is disabled, never consider it a session gap
    if (!filterSessionGaps) return false;

    // If open is significantly different from previous close, it's likely a session gap
    const gapThreshold = sessionGapThreshold / 100; // Convert percentage to decimal
    const prevClose = close[prevBar];
    const currentOpen = open[currentBar];

    if (prevClose == null || currentOpen == null) return false;

    const gapSize = Math.abs(currentOpen - prevClose) / prevClose;
    return gapSize > gapThreshold;
}

// Main processing loop
const dataLength = close.length;
for (let i = 2; i < dataLength; i++) {
    // Data validation
    if (high[i] == null || low[i] == null || close[i] == null || open[i] == null ||
        high[i - 1] == null || low[i - 1] == null || close[i - 1] == null ||
        high[i - 2] == null || low[i - 2] == null || close[i - 2] == null ||
        high[i] < low[i] || high[i - 1] < low[i - 1] || high[i - 2] < low[i - 2]) {
        continue;
    }

    try {
        // Skip FVG detection if there are session gaps in the 3-bar pattern
        // This prevents detecting overnight gaps as FVGs
        if (isSessionGap(i, i - 1) || isSessionGap(i - 1, i - 2)) {
            debugCounters.sessionGapsFiltered++;
            continue;
        }

        // FVG Detection
        // Only detect FVGs during continuous trading (no session gaps)
        const bullFVG = (low[i] > high[i - 2]) && (close[i - 1] > high[i - 2]);
        const bearFVG = (high[i] < low[i - 2]) && (close[i - 1] < low[i - 2]);

        const bullGapWidth = bullFVG ? Math.abs(low[i] - high[i - 2]) : 0;
        const bearGapWidth = bearFVG ? Math.abs(low[i - 2] - high[i]) : 0;
        const currentMinWidth = minWidth[i] || 0;

        const validBullFVG = bullFVG && bullGapWidth > currentMinWidth;
        const validBearFVG = bearFVG && bearGapWidth > currentMinWidth;
        


        // Optional: Mark seed FVGs
        if (showSeeds) {
            if (validBullFVG) { seedTop[i] = low[i]; seedBot[i] = high[i - 2]; }
            if (validBearFVG) { seedTop[i] = low[i - 2]; seedBot[i] = high[i]; }
        }

        // Create FVG objects
        if (validBullFVG) {
            const newFVG = {
                left: i - 1,
                top0: low[i],
                bot0: high[i - 2],
                mid0: (low[i] + high[i - 2]) / 2,
                dir: 1,
                state: 0,
                signaled: false,
                alive: false,
                endIndex: null,
                xIndex: null
            };

            if (validateFVG(newFVG)) {
                bulls.push(newFVG);
                debugCounters.bullFVGsDetected++;
            }
        }

        if (validBearFVG) {
            const newFVG = {
                left: i - 1,
                top0: low[i - 2],
                bot0: high[i],
                mid0: (low[i - 2] + high[i]) / 2,
                dir: -1,
                state: 0,
                signaled: false,
                alive: false,
                endIndex: null,
                xIndex: null
            };

            if (validateFVG(newFVG)) {
                bears.push(newFVG);
                debugCounters.bearFVGsDetected++;
            }
        }

        // Inversion Detection
        const currentCBot = c_bot[i];
        const currentCTop = c_top[i];

        // FVG Management - Move to inversion arrays
        // Bull FVG inversions - move to bullInv (originally bullish FVGs that will invert)
        for (let j = bulls.length - 1; j >= 0; j--) {
            const fvg = bulls[j];
            if (fvg.dir === 1 && currentCBot < fvg.bot0) {
                fvg.xIndex = i; // Mark inversion bar
                bullInv.push(bulls.splice(j, 1)[0]); // Move to inversion array
                debugCounters.bullInversions++;
                inversionDots[i] = fvg.mid0;
            }
        }

        // Bear FVG inversions - move to bearInv (originally bearish FVGs that will invert)
        for (let j = bears.length - 1; j >= 0; j--) {
            const fvg = bears[j];
            if (fvg.dir === -1 && currentCTop > fvg.top0) {
                fvg.xIndex = i; // Mark inversion bar
                bearInv.push(bears.splice(j, 1)[0]); // Move to inversion array
                debugCounters.bearInversions++;
                inversionDots[i] = fvg.mid0;
            }
        }

        // Inversion Management
        // Process bullInv array (originally bullish FVGs that inverted)
        for (let fvg of bullInv) {
            if (fvg.state === 0) {
                fvg.state = 1;
                fvg.dir = -1; // Flip to bearish after inversion
                fvg.alive = true;
                fvg.endIndex = null;
            }
            if (fvg.state >= 1) {
                // Extend the zone to current bar
            }
        }

        // Process bearInv array (originally bearish FVGs that inverted)
        for (let fvg of bearInv) {
            if (fvg.state === 0) {
                fvg.state = 1;
                fvg.dir = 1; // Flip to bullish after inversion
                fvg.alive = true;
                fvg.endIndex = null;
            }
            if (fvg.state >= 1) {
                // Extend the zone to current bar
            }
        }

        // Signal Generation
        if (i > 0) {
            // Bearish signals from bullInv (originally bullish FVGs, now bearish)
            for (let fvg of bullInv) {
                if (fvg.dir === -1 && fvg.state === 1 && !fvg.signaled) {
                    const currentClose = close[i];
                    const prevPrice = useWickRetest ? high[i - 1] : close[i - 1];

                    if (currentClose < fvg.bot0 &&
                        prevPrice >= fvg.bot0 &&
                        prevPrice < fvg.top0) {
                        bearRet[i] = true;
                        fvg.signaled = true;
                        debugCounters.bearSignals++;
                    }
                }
            }

            // Bullish signals from bearInv (originally bearish FVGs, now bullish)
            for (let fvg of bearInv) {
                if (fvg.dir === 1 && fvg.state === 1 && !fvg.signaled) {
                    const currentClose = close[i];
                    const prevPrice = useWickRetest ? low[i - 1] : close[i - 1];

                    if (currentClose > fvg.top0 &&
                        prevPrice <= fvg.top0 &&
                        prevPrice > fvg.bot0) {
                        bullRet[i] = true;
                        fvg.signaled = true;
                        debugCounters.bullSignals++;
                    }
                }
            }
        }

        // Post-inversion invalidation
        for (let j = bullInv.length - 1; j >= 0; j--) {
            const fvg = bullInv[j];

            if (fvg.state >= 1 && fvg.alive !== false) {
                const shouldInvalidate = (fvg.dir === -1 && currentCTop > fvg.top0) ||
                    (fvg.dir === 1 && currentCBot < fvg.bot0);
                if (shouldInvalidate) {
                    fvg.alive = false;
                    fvg.endIndex = i;
                    debugCounters.zonesInvalidated++;
                }
            }
        }

        for (let j = bearInv.length - 1; j >= 0; j--) {
            const fvg = bearInv[j];

            if (fvg.state >= 1 && fvg.alive !== false) {
                const shouldInvalidate = (fvg.dir === -1 && currentCTop > fvg.top0) ||
                    (fvg.dir === 1 && currentCBot < fvg.bot0);
                if (shouldInvalidate) {
                    fvg.alive = false;
                    fvg.endIndex = i;
                    debugCounters.zonesInvalidated++;
                }
            }
        }

        // Memory management
        if (bulls.length >= BUFFER) bulls.splice(0, bulls.length - BUFFER + 10);
        if (bears.length >= BUFFER) bears.splice(0, bears.length - BUFFER + 10);
        if (bullInv.length >= BUFFER) bullInv.splice(0, bullInv.length - BUFFER + 10);
        if (bearInv.length >= BUFFER) bearInv.splice(0, bearInv.length - BUFFER + 10);

    } catch (error) {
        console.warn('IFVG processing error at bar ' + i + ':', error);
        continue;
    }
}

// Drawing logic - fill series for recent zones
// Display zones from all arrays (original + inverted)
// We need to include both original arrays (bulls, bears) and inversion arrays (bullInv, bearInv)
const recentBulls = bulls
    .filter(z => z.xIndex !== undefined && z.xIndex !== null)
    .slice(-disp_num);

const recentBears = bears
    .filter(z => z.xIndex !== undefined && z.xIndex !== null)
    .slice(-disp_num);

const recentBullInv = bullInv
    .filter(z => z.xIndex !== undefined && z.xIndex !== null)
    .slice(-disp_num);

const recentBearInv = bearInv
    .filter(z => z.xIndex !== undefined && z.xIndex !== null)
    .slice(-disp_num);

const allZones = recentBulls.concat(recentBears, recentBullInv, recentBearInv).sort((a, b) => a.xIndex - b.xIndex);

// Fill drawing series
for (let i = 0; i < close.length; i++) {
    for (let k = 0; k < Math.min(allZones.length, maxZones); k++) {
        const zone = allZones[k];

        // Pre-inversion segment
        if (i >= zone.left && i <= zone.xIndex) {
            preTopSeries[k][i] = zone.top0;
            preBotSeries[k][i] = zone.bot0;
        }

        // Post-inversion segment
        let maxRight;
        if (zone.endIndex !== null && zone.endIndex !== undefined) {
            maxRight = zone.endIndex;
        } else if (extendZones && zone.alive !== false) {
            maxRight = Math.min(i + proj_len, close.length - 1);
        } else {
            maxRight = zone.xIndex;
        }

        if (i >= zone.xIndex && i <= maxRight) {
            postTopSeries[k][i] = zone.top0;
            postBotSeries[k][i] = zone.bot0;
        }

        // Midline
        if (showMidlines) {
            const totalRight = Math.max(zone.xIndex, maxRight);
            if (i >= zone.left && i <= totalRight) {
                midSeries[k][i] = zone.mid0;
            }
        }
    }
}

// Visual rendering
if (showSeeds) {
    const seedTopRef = paint(seedTop, { hidden: true, color: '#88888822' });
    const seedBotRef = paint(seedBot, { hidden: true, color: '#88888822' });
    fill(seedTopRef, seedBotRef, '#88888811');
}

// Paint zones
for (let k = 0; k < Math.min(allZones.length, maxZones); k++) {
    const zone = allZones[k];
    if (!zone) continue;



    // Color assignment based on zone.dir
    let preColor, postColor;
    if (colorByLocation) {
        // Override: color by location relative to current price
        const currentPrice = close[close.length - 1];
        const zoneAbovePrice = zone.bot0 > currentPrice;
        preColor = zoneAbovePrice ? red : green;
        postColor = zoneAbovePrice ? red : green;
    } else {
        // Standard logic: zone.dir determines colors
        // For non-inverted zones, use original direction
        // For inverted zones, use flipped direction (already stored in zone.dir)
        if (zone.dir === -1) {
            preColor = green;  // dir=-1 zones are green pre-inversion
            postColor = red;   // dir=-1 zones are red post-inversion
        } else {
            preColor = red;    // dir=1 zones are red pre-inversion
            postColor = green; // dir=1 zones are green post-inversion
        }
    }



    // Paint midline first
    if (showMidlines) {
        paint(midSeries[k], { color: midCol, style: 'dotted', thickness: 1 });
    }

    // Paint zone segments
    const preTopRef = paint(preTopSeries[k], { hidden: true, color: preColor });
    const preBotRef = paint(preBotSeries[k], { hidden: true, color: preColor });
    const postTopRef = paint(postTopSeries[k], { hidden: true, color: postColor });
    const postBotRef = paint(postBotSeries[k], { hidden: true, color: postColor });

    // Fill zones
    fill(preTopRef, preBotRef, preColor);
    fill(postTopRef, postBotRef, postColor);
}

// Optional: Show inversion dots
if (showInversionDots) {
    paint(inversionDots, { name: 'Inversion Points', color: midCol, style: 'dotted', thickness: 1 });
}

// Signal registration
register_signal(bearRet, 'Bearish IFVG Signal');
register_signal(bullRet, 'Bullish IFVG Signal');</code>