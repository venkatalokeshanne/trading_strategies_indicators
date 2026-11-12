<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Market Structure Breaks', 'price', {
    decimals: 'by_symbol',
    shortName: 'MSB'
});

// Input parameters with proper UI controls
const showZigZag = input.boolean('Show ZigZag Trend', true);
const showStructureLevels = input.boolean('Show Structure Levels', true);
const pivotDisplayType = input('Pivot Display Type', 'Zones', ['Dots', 'Lines', 'Zones']);
const showZones = input.boolean('Show Support/Resistance Zones', true);
const extendZonesToRight = input.boolean('Extend Zones to Right', true);
const swingLength = input('Swing Length', 10, { min: 5, max: 50 });
const lookbackBars = input('Lookback Bars', 50, { min: 20, max: 100 });
const minSwingStrength = input('Min Swing Strength', 0.5, { min: 0.1, max: 2.0 });
const signalCooldown = input('Signal Cooldown', 5, { min: 1, max: 20 });

// Color configuration
const COLORS = {
    zigzagUp: '#4CAF50',
    zigzagDown: '#F44336', 
    bullishBreak: '#00E676',
    bearishBreak: '#FF1744',
    structureLevels: '#9C27B0',
    pivotLines: '#9C27B0',
    resistanceZone: '#FF572220',
    supportZone: '#4CAF5020',
    swingHighs: '#FF6B6B',
    swingLows: '#4ECDC4'
};

// ═══════════════════════════════════════════════════════════════
// SWING POINT DETECTION
// ═══════════════════════════════════════════════════════════════

// Calculate swing highs and lows with strength filtering
const swingHighs = series_of(null);
const swingLows = series_of(null);

for (let i = swingLength; i < close.length - swingLength; i++) {
    let isSwingHigh = true;
    let isSwingLow = true;
    
    // Check if current point is highest/lowest in the swing range
    for (let j = i - swingLength; j <= i + swingLength; j++) {
        if (j === i) continue;
        
        if (high[j] >= high[i]) isSwingHigh = false;
        if (low[j] <= low[i]) isSwingLow = false;
    }
    
    // Apply strength filtering
    if (isSwingHigh) {
        const swingRange = high[i] - low[i];
        const avgRange = (high[i] + high[i-1] + high[i-2]) / 3 - (low[i] + low[i-1] + low[i-2]) / 3;
        if (swingRange >= avgRange * minSwingStrength) {
            swingHighs[i] = high[i];
        }
    }
    
    if (isSwingLow) {
        const swingRange = high[i] - low[i];
        const avgRange = (high[i] + high[i-1] + high[i-2]) / 3 - (low[i] + low[i-1] + low[i-2]) / 3;
        if (swingRange >= avgRange * minSwingStrength) {
            swingLows[i] = low[i];
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// ZIGZAG TREND LINES (SIMPLIFIED)
// ═══════════════════════════════════════════════════════════════

const zigzagUpLine = series_of(null);
const zigzagDownLine = series_of(null);

if (showZigZag) {
    // Improved ZigZag that connects all swing points in sequence
    let lastSwingIndex = -1;
    let lastSwingPrice = 0;
    let lastSwingType = '';
    
    for (let i = 0; i < close.length; i++) {
        let currentSwingPrice = null;
        let currentSwingType = '';
        
        // Check for any swing point at current index
        if (swingHighs[i] !== null) {
            currentSwingPrice = swingHighs[i];
            currentSwingType = 'high';
        } else if (swingLows[i] !== null) {
            currentSwingPrice = swingLows[i];
            currentSwingType = 'low';
        }
        
        // If we found a swing point and have a previous swing point
        if (currentSwingPrice !== null && lastSwingIndex >= 0) {
            // Determine if this is an uptrend or downtrend
            const isUptrend = currentSwingPrice > lastSwingPrice;
            const targetSeries = isUptrend ? zigzagUpLine : zigzagDownLine;
            
            // Draw line between the two swing points
            for (let j = lastSwingIndex; j <= i; j++) {
                if (i > lastSwingIndex) {
                    const progress = (j - lastSwingIndex) / (i - lastSwingIndex);
                    targetSeries[j] = lastSwingPrice + (currentSwingPrice - lastSwingPrice) * progress;
                }
            }
        }
        
        // Update last swing point if we found one
        if (currentSwingPrice !== null) {
            lastSwingIndex = i;
            lastSwingPrice = currentSwingPrice;
            lastSwingType = currentSwingType;
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// STRUCTURE BREAK DETECTION
// ═══════════════════════════════════════════════════════════════

const structureBreakBullish = series_of(null);
const structureBreakBearish = series_of(null);
const structureLevels = series_of(null); // Purple dots - always show
const resistanceZoneTop = series_of(null);
const resistanceZoneBottom = series_of(null);
const supportZoneTop = series_of(null);
const supportZoneBottom = series_of(null);

let lastBullishSignal = -signalCooldown;
let lastBearishSignal = -signalCooldown;

// Create zones for every purple dot using series
const pivotZoneTop1 = series_of(null);
const pivotZoneBottom1 = series_of(null);
const pivotZoneTop2 = series_of(null);
const pivotZoneBottom2 = series_of(null);
const pivotZoneTop3 = series_of(null);
const pivotZoneBottom3 = series_of(null);
const pivotZoneTop4 = series_of(null);
const pivotZoneBottom4 = series_of(null);
const pivotZoneTop5 = series_of(null);
const pivotZoneBottom5 = series_of(null);
const pivotZoneTop6 = series_of(null);
const pivotZoneBottom6 = series_of(null);
const pivotZoneTop7 = series_of(null);
const pivotZoneBottom7 = series_of(null);
const pivotZoneTop8 = series_of(null);
const pivotZoneBottom8 = series_of(null);

// Real-time structure break detection
for (let candleIndex = lookbackBars + swingLength; candleIndex < close.length; candleIndex++) {
    
    // Find most recent swing high within lookback period
    let recentSwingHigh = null;
    let recentSwingHighIndex = -1;
    
    for (let lookback = 1; lookback <= lookbackBars; lookback++) {
        const checkIndex = candleIndex - lookback;
        if (checkIndex >= 0 && swingHighs[checkIndex] !== null) {
            recentSwingHigh = swingHighs[checkIndex];
            recentSwingHighIndex = checkIndex;
            break;
        }
    }
    
    // Check for bullish structure break (price breaks above recent swing high)
    if (recentSwingHigh !== null && 
        close[candleIndex] > recentSwingHigh && 
        candleIndex - lastBullishSignal >= signalCooldown) {
        
        // Volume confirmation logic
        let volumeConfirmed = true;
        if (volume && volume[candleIndex] !== null) {
            // Simple volume check without MA
            let volumeSum = 0;
            let volumeCount = 0;
            if (candleIndex > 20) {
                for (let v = candleIndex - 20; v < candleIndex; v++) {
                    volumeSum += volume[v];
                    volumeCount++;
                }
                const avgVolume = volumeSum / volumeCount;
                volumeConfirmed = volume[candleIndex] > avgVolume * 0.8;
            } else {
                volumeConfirmed = true;
            }
        }
        
        if (volumeConfirmed) {
            structureBreakBullish[candleIndex] = high[candleIndex];
            lastBullishSignal = candleIndex;
            
            // Always create pivot levels for purple dots
            structureLevels[candleIndex] = recentSwingHigh;
            
            // Create pivot zone directly for every purple dot (if pivot display is enabled)
            if (pivotDisplayType === 'Zones') {
                const zoneWidth = recentSwingHigh * 0.002; // 0.2% zone width
                
                // Extend zone from this point to the right edge
                for (let extend = candleIndex; extend < close.length; extend++) {
                    // Use next available zone series
                    if (pivotZoneTop1[extend] === null) {
                        pivotZoneTop1[extend] = recentSwingHigh + zoneWidth;
                        pivotZoneBottom1[extend] = recentSwingHigh - zoneWidth;
                    } else if (pivotZoneTop2[extend] === null) {
                        pivotZoneTop2[extend] = recentSwingHigh + zoneWidth;
                        pivotZoneBottom2[extend] = recentSwingHigh - zoneWidth;
                    } else if (pivotZoneTop3[extend] === null) {
                        pivotZoneTop3[extend] = recentSwingHigh + zoneWidth;
                        pivotZoneBottom3[extend] = recentSwingHigh - zoneWidth;
                    } else if (pivotZoneTop4[extend] === null) {
                        pivotZoneTop4[extend] = recentSwingHigh + zoneWidth;
                        pivotZoneBottom4[extend] = recentSwingHigh - zoneWidth;
                    } else if (pivotZoneTop5[extend] === null) {
                        pivotZoneTop5[extend] = recentSwingHigh + zoneWidth;
                        pivotZoneBottom5[extend] = recentSwingHigh - zoneWidth;
                    } else if (pivotZoneTop6[extend] === null) {
                        pivotZoneTop6[extend] = recentSwingHigh + zoneWidth;
                        pivotZoneBottom6[extend] = recentSwingHigh - zoneWidth;
                    } else if (pivotZoneTop7[extend] === null) {
                        pivotZoneTop7[extend] = recentSwingHigh + zoneWidth;
                        pivotZoneBottom7[extend] = recentSwingHigh - zoneWidth;
                    } else if (pivotZoneTop8[extend] === null) {
                        pivotZoneTop8[extend] = recentSwingHigh + zoneWidth;
                        pivotZoneBottom8[extend] = recentSwingHigh - zoneWidth;
                    }
                }
            }
            
            // Create resistance zone around broken level (only if zones enabled)
            if (showZones) {
                const zoneWidth = recentSwingHigh * 0.002; // 0.2% zone width
                for (let extend = candleIndex; extend < close.length; extend++) {
                    resistanceZoneTop[extend] = recentSwingHigh + zoneWidth;
                    resistanceZoneBottom[extend] = recentSwingHigh - zoneWidth;
                }
            }
        }
    }
    
    // Find most recent swing low within lookback period
    let recentSwingLow = null;
    let recentSwingLowIndex = -1;
    
    for (let lookback = 1; lookback <= lookbackBars; lookback++) {
        const checkIndex = candleIndex - lookback;
        if (checkIndex >= 0 && swingLows[checkIndex] !== null) {
            recentSwingLow = swingLows[checkIndex];
            recentSwingLowIndex = checkIndex;
            break;
        }
    }
    
    // Check for bearish structure break (price breaks below recent swing low)
    if (recentSwingLow !== null && 
        close[candleIndex] < recentSwingLow && 
        candleIndex - lastBearishSignal >= signalCooldown) {
        
        // Volume confirmation logic
        let volumeConfirmed = true;
        if (volume && volume[candleIndex] !== null) {
            // Simple volume check without MA
            let volumeSum = 0;
            let volumeCount = 0;
            if (candleIndex > 20) {
                for (let v = candleIndex - 20; v < candleIndex; v++) {
                    volumeSum += volume[v];
                    volumeCount++;
                }
                const avgVolume = volumeSum / volumeCount;
                volumeConfirmed = volume[candleIndex] > avgVolume * 0.8;
            } else {
                volumeConfirmed = true;
            }
        }
        
        if (volumeConfirmed) {
            structureBreakBearish[candleIndex] = low[candleIndex];
            lastBearishSignal = candleIndex;
            
            // Always create pivot levels for purple dots
            structureLevels[candleIndex] = recentSwingLow;
            
            // Create pivot zone directly for every purple dot (if pivot display is enabled)
            if (pivotDisplayType === 'Zones') {
                const zoneWidth = recentSwingLow * 0.002; // 0.2% zone width
                
                // Extend zone from this point to the right edge
                for (let extend = candleIndex; extend < close.length; extend++) {
                    // Use next available zone series
                    if (pivotZoneTop1[extend] === null) {
                        pivotZoneTop1[extend] = recentSwingLow + zoneWidth;
                        pivotZoneBottom1[extend] = recentSwingLow - zoneWidth;
                    } else if (pivotZoneTop2[extend] === null) {
                        pivotZoneTop2[extend] = recentSwingLow + zoneWidth;
                        pivotZoneBottom2[extend] = recentSwingLow - zoneWidth;
                    } else if (pivotZoneTop3[extend] === null) {
                        pivotZoneTop3[extend] = recentSwingLow + zoneWidth;
                        pivotZoneBottom3[extend] = recentSwingLow - zoneWidth;
                    } else if (pivotZoneTop4[extend] === null) {
                        pivotZoneTop4[extend] = recentSwingLow + zoneWidth;
                        pivotZoneBottom4[extend] = recentSwingLow - zoneWidth;
                    } else if (pivotZoneTop5[extend] === null) {
                        pivotZoneTop5[extend] = recentSwingLow + zoneWidth;
                        pivotZoneBottom5[extend] = recentSwingLow - zoneWidth;
                    } else if (pivotZoneTop6[extend] === null) {
                        pivotZoneTop6[extend] = recentSwingLow + zoneWidth;
                        pivotZoneBottom6[extend] = recentSwingLow - zoneWidth;
                    } else if (pivotZoneTop7[extend] === null) {
                        pivotZoneTop7[extend] = recentSwingLow + zoneWidth;
                        pivotZoneBottom7[extend] = recentSwingLow - zoneWidth;
                    } else if (pivotZoneTop8[extend] === null) {
                        pivotZoneTop8[extend] = recentSwingLow + zoneWidth;
                        pivotZoneBottom8[extend] = recentSwingLow - zoneWidth;
                    }
                }
            }
            
            // Create support zone around broken level (only if zones enabled)
            if (showZones) {
                const zoneWidth = recentSwingLow * 0.002; // 0.2% zone width
                for (let extend = candleIndex; extend < close.length; extend++) {
                    supportZoneTop[extend] = recentSwingLow + zoneWidth;
                    supportZoneBottom[extend] = recentSwingLow - zoneWidth;
                }
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// PAINT PIVOT ZONES (CREATED INLINE ABOVE)
// ═══════════════════════════════════════════════════════════════

// Paint all the pivot zones we created
if (pivotDisplayType === 'Zones') {
    fill(paint(pivotZoneTop1, { hidden: true }), paint(pivotZoneBottom1, { hidden: true }), '#9C27B050', undefined, 'Pivot Zone 1');
    fill(paint(pivotZoneTop2, { hidden: true }), paint(pivotZoneBottom2, { hidden: true }), '#9C27B050', undefined, 'Pivot Zone 2');
    fill(paint(pivotZoneTop3, { hidden: true }), paint(pivotZoneBottom3, { hidden: true }), '#9C27B050', undefined, 'Pivot Zone 3');
    fill(paint(pivotZoneTop4, { hidden: true }), paint(pivotZoneBottom4, { hidden: true }), '#9C27B050', undefined, 'Pivot Zone 4');
    fill(paint(pivotZoneTop5, { hidden: true }), paint(pivotZoneBottom5, { hidden: true }), '#9C27B050', undefined, 'Pivot Zone 5');
    fill(paint(pivotZoneTop6, { hidden: true }), paint(pivotZoneBottom6, { hidden: true }), '#9C27B050', undefined, 'Pivot Zone 6');
    fill(paint(pivotZoneTop7, { hidden: true }), paint(pivotZoneBottom7, { hidden: true }), '#9C27B050', undefined, 'Pivot Zone 7');
    fill(paint(pivotZoneTop8, { hidden: true }), paint(pivotZoneBottom8, { hidden: true }), '#9C27B050', undefined, 'Pivot Zone 8');
}

// Zones are created at their original size without adjustment

// ═══════════════════════════════════════════════════════════════
// ENHANCED VISUALIZATION
// ═══════════════════════════════════════════════════════════════

// Paint ZigZag trend lines first (background)
if (showZigZag) {
    paint(zigzagUpLine, 'ZigZag Up', COLORS.zigzagUp);
    paint(zigzagDownLine, 'ZigZag Down', COLORS.zigzagDown);
}

// Paint support and resistance zones
if (showZones) {
    fill(
        paint(resistanceZoneTop, { hidden: true }),
        paint(resistanceZoneBottom, { hidden: true }),
        COLORS.resistanceZone,
        undefined,
        'Resistance Zones'
    );
    
    fill(
        paint(supportZoneTop, { hidden: true }),
        paint(supportZoneBottom, { hidden: true }),
        COLORS.supportZone,
        undefined,
        'Support Zones'
    );
}

// Always paint purple dots regardless of display type
paint(structureLevels, 'Pivot Levels', COLORS.structureLevels);

// Paint swing points for reference
paint(swingHighs, 'Swing Highs', COLORS.swingHighs);
paint(swingLows, 'Swing Lows', COLORS.swingLows);

// Paint structure breaks with prominent styling
paint(structureBreakBullish, 'Bullish Structure Break', COLORS.bullishBreak);
paint(structureBreakBearish, 'Bearish Structure Break', COLORS.bearishBreak);</code>