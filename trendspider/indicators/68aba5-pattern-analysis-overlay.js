<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Pattern Analysis Overlay');

const myFontSize = input.number('Font Size', 12, { min: 8, max: 30 });
const showTrendlines = input.boolean('Show Trendlines', true);
const showTargets = input.boolean('Show Price Targets', true);
const showLevels = input.boolean('Show Pattern Levels', true);
const patternSensitivity = input.number('Pattern Sensitivity', 0.6, { min: 0.1, max: 1.0 });

// === Pattern Statistics Database
const PATTERN_STATS = {
    'Ascending Triangle': { avg: 8.2, success: 72, duration: 21, direction: '↗', color: '#4CAF50' },
    'Descending Triangle': { avg: -6.8, success: 68, duration: 18, direction: '↘', color: '#F44336' },
    'Symmetrical Triangle': { avg: 5.4, success: 64, duration: 25, direction: '↕', color: '#FF9800' },
    'Head & Shoulders': { avg: -9.2, success: 78, duration: 35, direction: '↘', color: '#9C27B0' },
    'Inverse H&S': { avg: 11.4, success: 74, duration: 32, direction: '↗', color: '#2196F3' },
    'Double Top': { avg: -7.6, success: 71, duration: 28, direction: '↘', color: '#E91E63' },
    'Double Bottom': { avg: 9.8, success: 69, duration: 26, direction: '↗', color: '#00BCD4' },
    'Rising Channel': { avg: 6.3, success: 58, duration: 42, direction: '↗', color: '#4CAF50' },
    'Falling Channel': { avg: -4.9, success: 56, duration: 38, direction: '↘', color: '#F44336' },
    'Horizontal Channel': { avg: 1.8, success: 52, duration: 35, direction: '→', color: '#9E9E9E' },
    'Rising Wedge': { avg: -5.2, success: 63, duration: 22, direction: '↘', color: '#FF5722' },
    'Falling Wedge': { avg: 7.8, success: 67, duration: 24, direction: '↗', color: '#00BCD4' },
    'Broadening Ascending': { avg: 4.1, success: 55, duration: 40, direction: '↗', color: '#FF9800' },
    'Broadening Descending': { avg: -3.8, success: 53, duration: 38, direction: '↘', color: '#FF5722' },
    'Broadening Symmetrical': { avg: 2.3, success: 48, duration: 45, direction: '↕', color: '#9C27B0' },
    'Uptrend': { avg: 12.5, success: 65, duration: 60, direction: '↗', color: '#4CAF50' },
    'Downtrend': { avg: -8.7, success: 62, duration: 45, direction: '↘', color: '#F44336' },
    'Sideways': { avg: 2.1, success: 45, duration: 30, direction: '→', color: '#9E9E9E' }
};

const STAGE_DESCRIPTIONS = {
    'Ascending Triangle': ['Formation', 'Testing Resistance', 'Breakout Prep', 'Initial Breakout', 'Breakout Retest', 'Confirmed Breakout'],
    'Descending Triangle': ['Formation', 'Testing Support', 'Breakdown Prep', 'Initial Breakdown', 'Breakdown Retest', 'Confirmed Breakdown'],
    'Symmetrical Triangle': ['Formation', 'Convergence', 'Apex Approach', 'Initial Breakout', 'Breakout Retest', 'Confirmed Breakout'],
    'Head & Shoulders': ['Left Shoulder', 'Head Formation', 'Right Shoulder', 'Initial Breakdown', 'Breakdown Retest', 'Confirmed Breakdown'],
    'Inverse H&S': ['Left Shoulder', 'Head Formation', 'Right Shoulder', 'Initial Breakout', 'Breakout Retest', 'Confirmed Breakout'],
    'Double Top': ['First Peak', 'Retest Peak', 'Neckline Test', 'Initial Breakdown', 'Breakdown Retest', 'Confirmed Breakdown'],
    'Double Bottom': ['First Trough', 'Retest Trough', 'Neckline Test', 'Initial Breakout', 'Breakout Retest', 'Confirmed Breakout'],
    'Rising Channel': ['Formation', 'Trend Development', 'Maturity', 'Initial Breakout', 'Breakout Retest', 'Confirmed Breakout'],
    'Falling Channel': ['Formation', 'Trend Development', 'Maturity', 'Initial Breakdown', 'Breakdown Retest', 'Confirmed Breakdown'],
    'Horizontal Channel': ['Formation', 'Range Development', 'Consolidation', 'Initial Breakout', 'Breakout Retest', 'Confirmed Breakout'],
    'Rising Wedge': ['Formation', 'Convergence', 'Apex Approach', 'Initial Breakdown', 'Breakdown Retest', 'Confirmed Breakdown'],
    'Falling Wedge': ['Formation', 'Convergence', 'Apex Approach', 'Initial Breakout', 'Breakout Retest', 'Confirmed Breakout'],
    'Broadening Ascending': ['Formation', 'Expansion', 'Volatility Peak', 'Initial Resolution', 'Resolution Retest', 'Confirmed Resolution'],
    'Broadening Descending': ['Formation', 'Expansion', 'Volatility Peak', 'Initial Resolution', 'Resolution Retest', 'Confirmed Resolution'],
    'Broadening Symmetrical': ['Formation', 'Expansion', 'Volatility Peak', 'Initial Resolution', 'Resolution Retest', 'Confirmed Resolution'],
    'Uptrend': ['Early Stage', 'Building Momentum', 'Acceleration', 'Strong Trend', 'Powerful Trend', 'Confirmed Breakout'],
    'Downtrend': ['Early Stage', 'Building Momentum', 'Acceleration', 'Strong Decline', 'Powerful Decline', 'Confirmed Breakdown'],
    'Sideways': ['Range Formation', 'Consolidation', 'Coiling', 'Breakout Prep', 'Testing Boundaries', 'Range Bound']
};

// === Color scheme
const BG = '#1e1e1e';
const STRIPE1 = '#2a2a2a';
const STRIPE2 = '#333333';
const HEADER_BG = '#0d47a1';

// === Swing point detection
const swingLength = 10;
const lookbackBars = 50;
const swingHighs = series_of(null);
const swingLows = series_of(null);

for (let i = swingLength; i < close.length - swingLength; i++) {
    let isSwingHigh = true;
    let isSwingLow = true;
    
    for (let j = i - swingLength; j <= i + swingLength; j++) {
        if (j === i) continue;
        if (high[j] >= high[i]) isSwingHigh = false;
        if (low[j] <= low[i]) isSwingLow = false;
    }
    
    if (isSwingHigh) swingHighs[i] = high[i];
    if (isSwingLow) swingLows[i] = low[i];
}

// === Find recent swing points
let high1Index = -1, high1Price = 0;
let high2Index = -1, high2Price = 0;
let high3Index = -1, high3Price = 0;
let low1Index = -1, low1Price = 0;
let low2Index = -1, low2Price = 0;
let low3Index = -1, low3Price = 0;
let highCount = 0, lowCount = 0;

for (let i = Math.max(0, close.length - lookbackBars); i < close.length; i++) {
    if (swingHighs[i] !== null) {
        high3Index = high2Index;
        high3Price = high2Price;
        high2Index = high1Index;
        high2Price = high1Price;
        high1Index = i;
        high1Price = swingHighs[i];
        highCount++;
    }
    if (swingLows[i] !== null) {
        low3Index = low2Index;
        low3Price = low2Price;
        low2Index = low1Index;
        low2Price = low1Price;
        low1Index = i;
        low1Price = swingLows[i];
        lowCount++;
    }
}

// === Pattern Detection Logic
let detectedPattern = '';
let patternStrength = 0;
let currentStage = 1;
let completionPrice = 0;
let targetPrice = 0;
let stopLoss = 0;
let failureTarget = 0;
let breakoutPrice = 0;
let breakdownPrice = 0;
let daysInPattern = 0;
let holdAboveLevel = 0;
let nextTarget = 0;

// Ensure we have enough data to analyze
if (close.length < 20) {
    detectedPattern = 'Insufficient Data';
    patternStrength = 0;
} else if (highCount >= 2 && lowCount >= 2) {
    const highSlope = high1Index > high2Index ? (high1Price - high2Price) / (high1Index - high2Index) : 0;
    const lowSlope = low1Index > low2Index ? (low1Price - low2Price) / (low1Index - low2Index) : 0;
    
    // Get current price early for pattern detection
    const currentPrice = close[close.length - 1];
    
    // Calculate days in pattern (from earliest swing point to current)
    const patternStartIndex = Math.min(high2Index, low2Index);
    daysInPattern = close.length - 1 - patternStartIndex;
    
    // Triangle Patterns - HIGHEST PRIORITY - Check first
    if (detectedPattern === '' && highCount >= 2 && lowCount >= 2) {
        // Symmetrical Triangle - converging lines (opposing slopes)
        const slopeSum = highSlope + lowSlope;
        const convergenceStrength = Math.abs(highSlope) + Math.abs(lowSlope);
        
        // More sensitive detection: opposing slopes with reasonable convergence
        if (highSlope < -0.0003 && lowSlope > 0.0003 && 
            Math.abs(slopeSum) < convergenceStrength * 0.6 && // Slopes roughly balance
            convergenceStrength > 0.001) { // Minimum slope strength
            
            detectedPattern = 'Symmetrical Triangle';
            patternStrength = Math.min(convergenceStrength * 600, 1.0);
            
            // Check if price has broken out of triangle bounds
            const upperBound = high2Price + highSlope * (close.length - 1 - high2Index);
            const lowerBound = low2Price + lowSlope * (close.length - 1 - low2Index);
            
            if (currentPrice > upperBound * 1.05) {
                currentStage = 6; // Confirmed breakout
                holdAboveLevel = upperBound; // Hold above breakout level
                nextTarget = currentPrice * 1.15; // Next target 15% higher
            } else if (currentPrice > upperBound * 1.02) {
                currentStage = 5; // Breakout retest
                holdAboveLevel = upperBound;
            } else if (currentPrice > upperBound) {
                currentStage = 4; // Initial breakout
                holdAboveLevel = upperBound;
            } else if (currentPrice < lowerBound * 0.95) {
                currentStage = 6; // Confirmed breakdown
            } else if (currentPrice < lowerBound * 0.98) {
                currentStage = 5; // Breakdown retest
            } else if (currentPrice < lowerBound) {
                currentStage = 4; // Initial breakdown
            } else {
                // Still within triangle
                const convergencePoint = (high2Price - low2Price) / (Math.abs(highSlope) + Math.abs(lowSlope));
                const timeToConvergence = convergencePoint - (close.length - 1 - Math.max(high2Index, low2Index));
                if (timeToConvergence > 10) currentStage = 1;
                else if (timeToConvergence > 5) currentStage = 2;
                else currentStage = 3;
            }
        } else if (highSlope < -0.0003 && Math.abs(lowSlope) < 0.0003) {
            // Descending Triangle - falling highs, flat lows
            detectedPattern = 'Descending Triangle';
            patternStrength = Math.abs(highSlope) * 1000;
            currentStage = Math.abs(highSlope) > 0.01 ? 2 : 3;
        } else if (Math.abs(highSlope) < 0.0003 && lowSlope > 0.0003) {
            // Ascending Triangle - flat highs, rising lows
            detectedPattern = 'Ascending Triangle';
            patternStrength = Math.abs(lowSlope) * 1000;
            currentStage = Math.abs(lowSlope) > 0.01 ? 2 : 3;
        }
    }
    
    // Channel Patterns - Only if no triangle detected
    if (detectedPattern === '' && Math.abs(highSlope - lowSlope) < 0.0005 && Math.abs(highSlope) > 0.001) {
        if (highSlope > 0.001 && lowSlope > 0.001) {
            detectedPattern = 'Rising Channel';
            patternStrength = (highSlope + lowSlope) * 500;
        } else if (highSlope < -0.001 && lowSlope < -0.001) {
            detectedPattern = 'Falling Channel';
            patternStrength = Math.abs(highSlope + lowSlope) * 500;
        }
    }
    
    // Horizontal Channel - Only if no other pattern detected
    if (detectedPattern === '' && Math.abs(highSlope) < 0.0005 && Math.abs(lowSlope) < 0.0005 && 
        highCount >= 2 && lowCount >= 2) {
        const range = Math.abs(high1Price - low1Price);
        if (range / currentPrice > 0.02) { // At least 2% range
            detectedPattern = 'Horizontal Channel';
            patternStrength = 0.7;
            currentStage = 2;
        }
    }
    
    // Wedge Patterns - Only if no pattern detected
    if (detectedPattern === '' && Math.abs(highSlope) > 0.001 && Math.abs(lowSlope) > 0.001) {
        const convergenceRate = Math.abs(highSlope + lowSlope);
        if (convergenceRate > 0.002) {
            if (highSlope > 0.001 && lowSlope > 0.001 && highSlope > lowSlope) {
                detectedPattern = 'Rising Wedge';
                patternStrength = convergenceRate * 400;
                currentStage = highSlope > 0.01 ? 2 : 3;
            } else if (highSlope < -0.001 && lowSlope < -0.001 && Math.abs(lowSlope) > Math.abs(highSlope)) {
                detectedPattern = 'Falling Wedge';
                patternStrength = convergenceRate * 400;
                currentStage = Math.abs(lowSlope) > 0.01 ? 2 : 3;
            }
        }
    }
    
    // Broadening Patterns (Diverging lines) - Lower priority
    if (detectedPattern === '' && Math.abs(highSlope) > 0.001 && Math.abs(lowSlope) > 0.001) {
        const divergenceRate = Math.abs(highSlope - lowSlope);
        if (divergenceRate > 0.003) {
            if (highSlope > 0.001 && lowSlope < -0.001) {
                detectedPattern = 'Broadening Ascending';
                patternStrength = divergenceRate * 300;
                currentStage = 2;
            } else if (highSlope < -0.001 && lowSlope > 0.001) {
                // Don't detect as broadening if it could be a symmetrical triangle
                if (divergenceRate > 0.01) { // Only if significantly diverging
                    detectedPattern = 'Broadening Descending';
                    patternStrength = divergenceRate * 300;
                    currentStage = 2;
                }
            } else if ((highSlope > 0.001 && lowSlope > 0.001) || (highSlope < -0.001 && lowSlope < -0.001)) {
                if (divergenceRate > Math.abs((highSlope + lowSlope) / 2)) {
                    detectedPattern = 'Broadening Symmetrical';
                    patternStrength = divergenceRate * 300;
                    currentStage = 2;
                }
            }
        }
    }
    
    // Double Top/Bottom Patterns - ONLY if no triangle pattern detected
    if (detectedPattern === '' && highCount >= 2 && high2Index >= 0 && high1Index >= 0) {
        const priceDiff = Math.abs(high1Price - high2Price);
        const avgPrice = (high1Price + high2Price) / 2;
        const timeDiff = high1Index - high2Index;
        
        // Look for similar highs with reasonable time separation
        if (priceDiff / avgPrice < 0.05 && timeDiff > 5) { // Within 5% and at least 5 bars apart
            detectedPattern = 'Double Top';
            patternStrength = 0.8;
            
            // Check if we've broken below the valley between peaks
            const valleyLow = Math.min(low1Price, low2Price);
            if (currentPrice < valleyLow) {
                currentStage = 4; // Initial breakdown
            } else if (currentPrice < avgPrice * 0.97) {
                currentStage = 3; // Neckline test
            } else {
                currentStage = 2; // Retest peak
            }
        }
    }
    
    if (detectedPattern === '' && lowCount >= 2 && low2Index >= 0 && low1Index >= 0) {
        const priceDiff = Math.abs(low1Price - low2Price);
        const avgPrice = (low1Price + low2Price) / 2;
        const timeDiff = low1Index - low2Index;
        
        // Look for similar lows with reasonable time separation
        if (priceDiff / avgPrice < 0.05 && timeDiff > 5) { // Within 5% and at least 5 bars apart
            detectedPattern = 'Double Bottom';
            patternStrength = 0.8;
            
            // Check if we've broken above the peak between troughs
            const peakHigh = Math.max(high1Price, high2Price);
            if (currentPrice > peakHigh * 1.02) {
                currentStage = 6; // Confirmed breakout
            } else if (currentPrice > peakHigh) {
                currentStage = 4; // Initial breakout
            } else if (currentPrice > avgPrice * 1.03) {
                currentStage = 3; // Neckline test
            } else {
                currentStage = 2; // Retest trough
            }
        }
    }
    
    // Head & Shoulders Patterns - Enhanced Detection
    if (highCount >= 3 && high3Index >= 0 && high2Index >= 0 && high1Index >= 0) {
        // Check if middle high is the head (highest) and shoulders are similar
        const leftShoulder = high3Price;
        const head = high2Price;
        const rightShoulder = high1Price;
        
        if (head > leftShoulder && head > rightShoulder) {
            const shoulderDiff = Math.abs(leftShoulder - rightShoulder);
            const shoulderAvg = (leftShoulder + rightShoulder) / 2;
            const headHeight = head - shoulderAvg;
            
            // Shoulders should be similar (within 10%) and head significantly higher
            if (shoulderDiff / shoulderAvg < 0.1 && headHeight / shoulderAvg > 0.05) {
                detectedPattern = 'Head & Shoulders';
                patternStrength = headHeight / head;
                currentStage = 3;
            }
        }
    }
    
    if (lowCount >= 3 && low3Index >= 0 && low2Index >= 0 && low1Index >= 0) {
        // Check if middle low is the head (lowest) and shoulders are similar
        const leftShoulder = low3Price;
        const head = low2Price;
        const rightShoulder = low1Price;
        
        if (head < leftShoulder && head < rightShoulder) {
            const shoulderDiff = Math.abs(leftShoulder - rightShoulder);
            const shoulderAvg = (leftShoulder + rightShoulder) / 2;
            const headDepth = shoulderAvg - head;
            
            // Shoulders should be similar (within 10%) and head significantly lower
            if (shoulderDiff / shoulderAvg < 0.1 && headDepth / shoulderAvg > 0.05) {
                detectedPattern = 'Inverse H&S';
                patternStrength = headDepth / shoulderAvg;
                currentStage = 3;
            }
        }
    }
    
    // === Pattern Priority System - Check for most specific patterns first
    // Priority: Triangle/Double patterns > Head & Shoulders > Channels/Wedges > Broadening > Trends
}

// === Fallback trend analysis - ALWAYS run to ensure we have something to display
if (detectedPattern === '' && close.length >= 20) {
    const currentClose = close[close.length - 1];
    const past20 = close[close.length - 20];
    const past10 = close[close.length - 10];
    const change20 = (currentClose - past20) / past20;
    const change10 = (currentClose - past10) / past10;
    
    if (change20 > 0.05) {
        detectedPattern = 'Uptrend';
        patternStrength = Math.min(change20 * 5, 1.0);
        // ALL uptrends with significant gains should be Stage 6
        if (change20 > 0.20) currentStage = 6; // Confirmed breakout (>20% gain)
        else if (change20 > 0.15) currentStage = 5; // Powerful trend (>15% gain)
        else if (change20 > 0.10) currentStage = 4; // Strong trend (>10% gain)
        else if (change20 > 0.08) currentStage = 3; // Acceleration (>8% gain)
        else if (change20 > 0.06) currentStage = 2; // Building momentum
        else currentStage = 1; // Early stage
    } else if (change20 < -0.05) {
        detectedPattern = 'Downtrend';
        patternStrength = Math.min(Math.abs(change20) * 5, 1.0);
        // ALL downtrends with significant declines should be Stage 6
        if (Math.abs(change20) > 0.20) currentStage = 6; // Confirmed breakdown (>20% decline)
        else if (Math.abs(change20) > 0.15) currentStage = 5; // Powerful decline (>15% decline)
        else if (Math.abs(change20) > 0.10) currentStage = 4; // Strong decline (>10% decline)
        else if (Math.abs(change20) > 0.08) currentStage = 3; // Acceleration (>8% decline)
        else if (Math.abs(change20) > 0.06) currentStage = 2; // Building momentum
        else currentStage = 1; // Early stage
    } else {
        detectedPattern = 'Sideways';
        patternStrength = 0.6;
        currentStage = 2;
        
        // For sideways, calculate range and set dual targets
        let recentHigh = 0;
        let recentLow = 999999;
        for (let i = Math.max(0, close.length - 20); i < close.length; i++) {
            if (close[i] > recentHigh) recentHigh = close[i];
            if (close[i] < recentLow) recentLow = close[i];
        }
        breakoutPrice = recentHigh;
        breakdownPrice = recentLow;
        completionPrice = recentHigh; // Default to upside break
        stopLoss = recentLow;
        failureTarget = (recentHigh + recentLow) / 2; // Middle of range
        daysInPattern = 20; // Default lookback for sideways
    }
}

// === Calculate targets and completion requirements + Check for breakouts
const currentPrice = close.length > 0 ? close[close.length - 1] : 0;

// Only proceed if we have valid data
if (currentPrice > 0 && detectedPattern !== '' && PATTERN_STATS[detectedPattern]) {
    const stats = PATTERN_STATS[detectedPattern];
    targetPrice = currentPrice * (1 + stats.avg / 100);
    
    // Check if pattern has already broken out (Stage 4)
    
    if (detectedPattern === 'Ascending Triangle') {
        const resistanceLevel = highCount >= 2 ? Math.max(high1Price, high2Price) : high1Price;
        const supportLevel = lowCount >= 1 ? low1Price : currentPrice * 0.95;
        
        breakoutPrice = resistanceLevel;
        breakdownPrice = supportLevel;
        completionPrice = resistanceLevel; // Primary expectation
        stopLoss = supportLevel;
        failureTarget = supportLevel * 0.95; // Pattern failure below support
        
        // Check for breakout above resistance
        if (currentPrice > resistanceLevel * 1.1) {
            currentStage = 6; // Confirmed breakout
        } else if (currentPrice > resistanceLevel * 1.02) {
            currentStage = 5; // Breakout retest phase
        } else if (currentPrice > resistanceLevel) {
            currentStage = 4; // Initial breakout
        } else if (currentPrice < supportLevel) {
            // Pattern failed - breakdown instead
            currentStage = 4; // Skip to breakdown
            completionPrice = breakdownPrice;
        }
    } else if (detectedPattern === 'Descending Triangle') {
        completionPrice = lowCount >= 2 ? Math.min(low1Price, low2Price) : low1Price;
        stopLoss = highCount >= 1 ? high1Price : currentPrice * 1.05;
        // Check for breakdown below support
        if (currentPrice < completionPrice * 0.9) { // 10% below support
            currentStage = 6; // Confirmed breakdown
        } else if (currentPrice < completionPrice * 0.98) { // 2% below support
            currentStage = 5; // Breakdown retest phase
        } else if (currentPrice < completionPrice) {
            currentStage = 4; // Initial breakdown
        }
    } else if (detectedPattern === 'Symmetrical Triangle') {
        const resistanceLevel = highCount >= 2 ? Math.max(high1Price, high2Price) : high1Price;
        const supportLevel = lowCount >= 2 ? Math.min(low1Price, low2Price) : low1Price;
        
        breakoutPrice = resistanceLevel;
        breakdownPrice = supportLevel;
        completionPrice = currentPrice > (resistanceLevel + supportLevel) / 2 ? resistanceLevel : supportLevel;
        stopLoss = currentPrice > (resistanceLevel + supportLevel) / 2 ? supportLevel : resistanceLevel;
        
        // Pattern failure is breaking below support after upside breakout, or above resistance after downside breakout
        if (currentPrice > (resistanceLevel + supportLevel) / 2) {
            // Currently bullish - failure is break below support
            failureTarget = supportLevel * 0.95;
        } else {
            // Currently bearish - failure is break above resistance  
            failureTarget = resistanceLevel * 1.05;
        }
        
        // Check for breakout in either direction
        if (currentPrice > resistanceLevel * 1.1 || currentPrice < supportLevel * 0.9) {
            currentStage = 6; // Confirmed breakout
        } else if (currentPrice > resistanceLevel * 1.02 || currentPrice < supportLevel * 0.98) {
            currentStage = 5; // Breakout retest phase
        } else if (currentPrice > resistanceLevel || currentPrice < supportLevel) {
            currentStage = 4; // Initial breakout
        }
    } else if (detectedPattern === 'Double Top') {
        // Find the valley (neckline) between the two peaks
        const leftPeakIndex = high2Index;  // Earlier peak
        const rightPeakIndex = high1Index; // Later peak
        let valleyLow = currentPrice;
        
        // Find the lowest point between the two peaks
        for (let i = leftPeakIndex + 1; i < rightPeakIndex; i++) {
            if (low[i] < valleyLow) {
                valleyLow = low[i];
            }
        }
        
        const neckline = valleyLow;
        completionPrice = neckline;
        targetPrice = neckline * (1 + PATTERN_STATS[detectedPattern].avg / 100);
        nextTarget = targetPrice * 0.85; // Next target 15% further down
        stopLoss = Math.max(high1Price, high2Price);
        failureTarget = Math.max(high1Price, high2Price) * 1.02; // Pattern fails if price goes back above peaks
        
        // Check for breakdown below neckline
        if (currentPrice < neckline * 0.9) {
            currentStage = 6; // Confirmed breakdown
        } else if (currentPrice < neckline * 0.98) {
            currentStage = 5; // Breakdown retest phase
        } else if (currentPrice < neckline) {
            currentStage = 4; // Initial breakdown
        }
    } else if (detectedPattern === 'Double Bottom') {
        const neckline = highCount >= 2 ? Math.max(high1Price, high2Price) : currentPrice * 1.05;
        completionPrice = neckline;
        stopLoss = Math.min(low1Price, low2Price);
        // Check for breakout above neckline - THIS IS KEY FOR RKLB
        if (currentPrice > neckline * 2.0) { // 100% above neckline = confirmed breakout
            currentStage = 6; // Confirmed breakout
        } else if (currentPrice > neckline * 1.5) { // 50% above neckline = retest phase
            currentStage = 5; // Breakout retest phase
        } else if (currentPrice > neckline * 1.1) { // 10% above = initial breakout
            currentStage = 4; // Initial breakout
        }
    } else if (detectedPattern === 'Head & Shoulders') {
        const neckline = lowCount >= 2 ? Math.min(low1Price, low3Price) : currentPrice * 0.95;
        completionPrice = neckline;
        stopLoss = high2Price;
        // Check for breakdown below neckline
        if (currentPrice < neckline * 0.9) {
            currentStage = 6; // Confirmed breakdown
        } else if (currentPrice < neckline * 0.95) {
            currentStage = 5; // Breakdown retest phase
        } else if (currentPrice < neckline) {
            currentStage = 4; // Initial breakdown
        }
    } else if (detectedPattern === 'Inverse H&S') {
        const neckline = highCount >= 2 ? Math.max(high1Price, high3Price) : currentPrice * 1.05;
        completionPrice = neckline;
        stopLoss = low2Price;
        // Check for breakout above neckline
        if (currentPrice > neckline * 1.15) {
            currentStage = 6; // Confirmed breakout
        } else if (currentPrice > neckline * 1.05) {
            currentStage = 5; // Breakout retest phase
        } else if (currentPrice > neckline) {
            currentStage = 4; // Initial breakout
        }
    } else if (detectedPattern === 'Uptrend') {
        completionPrice = currentPrice * 1.05;
        stopLoss = lowCount >= 1 ? low1Price : currentPrice * 0.95;
    } else if (detectedPattern === 'Downtrend') {
        completionPrice = currentPrice * 0.95;
        stopLoss = highCount >= 1 ? high1Price : currentPrice * 1.05;
    } else if (detectedPattern === 'Rising Channel') {
        completionPrice = currentPrice * 1.03;
        stopLoss = low1Price;
    } else if (detectedPattern === 'Falling Channel') {
        completionPrice = currentPrice * 0.97;
        stopLoss = high1Price;
    } else if (detectedPattern === 'Horizontal Channel') {
        const midPoint = (high1Price + low1Price) / 2;
        completionPrice = currentPrice > midPoint ? high1Price * 1.01 : low1Price * 0.99;
        stopLoss = currentPrice > midPoint ? low1Price : high1Price;
    } else if (detectedPattern === 'Rising Wedge') {
        completionPrice = low1Price; // Bearish breakdown expected
        stopLoss = Math.max(high1Price, high2Price);
    } else if (detectedPattern === 'Falling Wedge') {
        completionPrice = high1Price; // Bullish breakout expected
        stopLoss = Math.min(low1Price, low2Price);
    } else if (detectedPattern === 'Broadening Ascending') {
        completionPrice = high1Price * 1.02;
        stopLoss = low1Price;
    } else if (detectedPattern === 'Broadening Descending') {
        completionPrice = low1Price * 0.98;
        stopLoss = high1Price;
    } else if (detectedPattern === 'Broadening Symmetrical') {
        const range = Math.abs(high1Price - low1Price);
        completionPrice = currentPrice + range * 0.5;
        stopLoss = currentPrice - range * 0.3;
    }
}

// === Build overlay table
const rows = [];

// Title row
rows.push({
    cells: [{
        colspan: 2,
        text: '📊 ' + constants.ticker + ' Pattern Analysis',
        fontWeight: 'bold',
        color: '#FFD700',
        textAlign: 'center',
        padding: '10px 15px',
        fontSize: myFontSize + 2,
        background: BG,
        border: '1px solid #FFD700'
    }]
});

// Always show something - even if no strong pattern
if (detectedPattern !== '' && (patternStrength >= patternSensitivity || detectedPattern === 'Uptrend' || detectedPattern === 'Downtrend' || detectedPattern === 'Sideways')) {
    const stats = PATTERN_STATS[detectedPattern];
    const confidence = Math.round(patternStrength * 100);
    const stages = STAGE_DESCRIPTIONS[detectedPattern] || ['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4'];
    const stageDesc = stages[Math.min(currentStage - 1, stages.length - 1)];
    
    // Pattern info
    rows.push({
        cells: [
            { text: 'Pattern:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
            { text: stats.direction + ' ' + detectedPattern + ' (' + confidence + '%)', padding: '6px 12px', color: stats.color, fontWeight: 'bold', background: STRIPE1 }
        ]
    });
    
    // Stage info
    rows.push({
        cells: [
            { text: 'Stage:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
            { text: currentStage + '/6 - ' + stageDesc, padding: '6px 12px', color: '#E0E0E0', background: STRIPE2 }
        ]
    });
    
    // Statistics
    rows.push({
        cells: [
            { text: 'Avg Return:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
            { text: (stats.avg > 0 ? '+' : '') + stats.avg + '%', padding: '6px 12px', color: stats.avg > 0 ? '#4CAF50' : '#F44336', fontWeight: 'bold', background: STRIPE1 }
        ]
    });
    
    rows.push({
        cells: [
            { text: 'Success Rate:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
            { text: stats.success + '%', padding: '6px 12px', color: stats.success > 65 ? '#4CAF50' : stats.success > 50 ? '#FF9800' : '#F44336', background: STRIPE2 }
        ]
    });
    
    // Price targets
    if (showTargets && targetPrice > 0) {
        const targetReturn = ((targetPrice - currentPrice) / currentPrice * 100);
        rows.push({
            cells: [
                { text: 'Price Target:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
                { text: '$' + targetPrice.toFixed(2) + ' (' + (targetReturn > 0 ? '+' : '') + targetReturn.toFixed(1) + '%)', padding: '6px 12px', color: targetReturn > 0 ? '#4CAF50' : '#F44336', fontWeight: 'bold', background: STRIPE1 }
            ]
        });
    }
    
    // Completion requirement OR hold above level for breakouts
    if (currentStage >= 4 && holdAboveLevel > 0) {
        // Already broken out - show hold level
        rows.push({
            cells: [
                { text: 'Hold Above:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
                { text: '$' + holdAboveLevel.toFixed(2) + ' (Support)', padding: '6px 12px', color: '#4CAF50', background: STRIPE2 }
            ]
        });
    } else if (completionPrice > 0) {
        const direction = completionPrice > currentPrice ? 'above' : 'below';
        rows.push({
            cells: [
                { text: 'Completion:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
                { text: 'Break ' + direction + ' $' + completionPrice.toFixed(2), padding: '6px 12px', color: '#00BCD4', background: STRIPE2 }
            ]
        });
    }
    
    // Next target after initial target is hit
    if (nextTarget > 0 && Math.abs(currentPrice - targetPrice) / targetPrice < 0.02) {
        const nextReturn = ((nextTarget - currentPrice) / currentPrice * 100);
        rows.push({
            cells: [
                { text: 'Next Target:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
                { text: '$' + nextTarget.toFixed(2) + ' (' + (nextReturn > 0 ? '+' : '') + nextReturn.toFixed(1) + '%)', padding: '6px 12px', color: '#9C27B0', background: STRIPE1 }
            ]
        });
    }
    
    // Risk level
    if (stopLoss > 0) {
        const riskPercent = Math.abs((stopLoss - currentPrice) / currentPrice * 100);
        rows.push({
            cells: [
                { text: 'Risk Level:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
                { text: '$' + stopLoss.toFixed(2) + ' (-' + riskPercent.toFixed(1) + '%)', padding: '6px 12px', color: '#FF5722', background: STRIPE1 }
            ]
        });
    }
    
    // Days in pattern
    if (daysInPattern > 0) {
        rows.push({
            cells: [
                { text: 'Days in Pattern:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
                { text: daysInPattern + ' days', padding: '6px 12px', color: '#9E9E9E', background: STRIPE2 }
            ]
        });
    }
    
    // Dual breakout/breakdown for consolidation patterns
    if ((detectedPattern === 'Symmetrical Triangle' || detectedPattern === 'Sideways' || detectedPattern === 'Horizontal Channel') && 
        breakoutPrice > 0 && breakdownPrice > 0) {
        
        const upPercent = ((breakoutPrice - currentPrice) / currentPrice * 100);
        const downPercent = ((breakdownPrice - currentPrice) / currentPrice * 100);
        
        rows.push({
            cells: [
                { text: 'Breakout Target:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
                { text: '$' + breakoutPrice.toFixed(2) + ' (' + (upPercent > 0 ? '+' : '') + upPercent.toFixed(1) + '%)', padding: '6px 12px', color: '#4CAF50', background: STRIPE1 }
            ]
        });
        
        rows.push({
            cells: [
                { text: 'Breakdown Target:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
                { text: '$' + breakdownPrice.toFixed(2) + ' (' + downPercent.toFixed(1) + '%)', padding: '6px 12px', color: '#F44336', background: STRIPE2 }
            ]
        });
    }
    
    // Pattern failure target
    if (failureTarget > 0 && failureTarget !== currentPrice) {
        const failPercent = ((failureTarget - currentPrice) / currentPrice * 100);
        rows.push({
            cells: [
                { text: 'Pattern Failure:', fontWeight: 'bold', padding: '6px 12px', color: 'lightgray', background: HEADER_BG },
                { text: '$' + failureTarget.toFixed(2) + ' (' + (failPercent > 0 ? '+' : '') + failPercent.toFixed(1) + '%)', padding: '6px 12px', color: '#FF9800', background: STRIPE1 }
            ]
        });
    }
    
} else {
    // No pattern detected
    rows.push({
        cells: [{
            colspan: 2,
            text: '🔍 No clear pattern detected - Increase sensitivity or wait for pattern development',
            color: '#9E9E9E',
            textAlign: 'center',
            padding: '10px 15px',
            background: STRIPE2
        }]
    });
}

// === Render overlay
paint_overlay('Pattern Analysis', { position: 'top_right', order: 'above_all' }, {
    fontSize: myFontSize,
    background: BG,
    border: '2px solid #FFD700',
    borderRadius: '8px',
    rows
});

// === Draw trendlines if enabled
if (showTrendlines) {
    const trendlineTop = series_of(null);
    const trendlineBottom = series_of(null);
    
    if (highCount >= 2 && high2Index >= 0 && high1Index >= 0) {
        const slope = (high1Price - high2Price) / (high1Index - high2Index);
        for (let i = high2Index; i < close.length; i++) {
            trendlineTop[i] = high2Price + slope * (i - high2Index);
        }
    }
    
    if (lowCount >= 2 && low2Index >= 0 && low1Index >= 0) {
        const slope = (low1Price - low2Price) / (low1Index - low2Index);
        for (let i = low2Index; i < close.length; i++) {
            trendlineBottom[i] = low2Price + slope * (i - low2Index);
        }
    }
    
    paint(trendlineTop, 'Resistance Line', '#F44336');
    paint(trendlineBottom, 'Support Line', '#4CAF50');
    paint(swingHighs, 'Swing Highs', '#FF5722');
    paint(swingLows, 'Swing Lows', '#00BCD4');
}

// === LEVEL LINES - Draw key price levels extending to the right ===
const completionLine = series_of(null);
const holdAboveLine = series_of(null);
const targetLine = series_of(null);
const nextTargetLine = series_of(null);
const failureLine = series_of(null);
const breakoutLine = series_of(null);
const breakdownLine = series_of(null);
const riskLine = series_of(null);

// Fill level lines with prices when pattern is detected AND levels are enabled
if (showLevels && detectedPattern !== '' && (patternStrength >= patternSensitivity || detectedPattern === 'Uptrend' || detectedPattern === 'Downtrend' || detectedPattern === 'Sideways')) {
    const currentIndex = close.length - 1;
    
    // Draw completion level (breakout trigger)
    if (completionPrice > 0 && currentStage < 4) {
        for (let i = Math.max(0, currentIndex - 5); i < close.length; i++) {
            completionLine[i] = completionPrice;
        }
    }
    
    // Draw hold-above level (critical support after breakout)
    if (holdAboveLevel > 0 && currentStage >= 4) {
        for (let i = Math.max(0, currentIndex - 5); i < close.length; i++) {
            holdAboveLine[i] = holdAboveLevel;
        }
    }
    
    // Draw primary target level - only if targets are enabled
    if (showTargets && targetPrice > 0) {
        for (let i = Math.max(0, currentIndex - 5); i < close.length; i++) {
            targetLine[i] = targetPrice;
        }
    }
    
    // Draw next target level (progressive targets) - only if targets are enabled
    if (showTargets && nextTarget > 0) {
        for (let i = Math.max(0, currentIndex - 5); i < close.length; i++) {
            nextTargetLine[i] = nextTarget;
        }
    }
    
    // Draw pattern failure level 
    if (failureTarget > 0) {
        for (let i = Math.max(0, currentIndex - 5); i < close.length; i++) {
            failureLine[i] = failureTarget;
        }
    }
    
    // Draw risk level (stop loss)
    if (stopLoss > 0) {
        for (let i = Math.max(0, currentIndex - 5); i < close.length; i++) {
            riskLine[i] = stopLoss;
        }
    }
    
    // Draw dual breakout/breakdown levels for consolidation patterns - only if targets are enabled
    if (showTargets && (detectedPattern === 'Symmetrical Triangle' || detectedPattern === 'Sideways' || detectedPattern === 'Horizontal Channel') && 
        breakoutPrice > 0 && breakdownPrice > 0) {
        
        for (let i = Math.max(0, currentIndex - 5); i < close.length; i++) {
            breakoutLine[i] = breakoutPrice;
            breakdownLine[i] = breakdownPrice;
        }
    }
}

// Paint the level lines
paint(completionLine, 'Completion Level', '#00BCD4');
paint(holdAboveLine, 'Hold Above (Support)', '#4CAF50');
paint(targetLine, 'Price Target', '#FF9800');
paint(nextTargetLine, 'Next Target', '#9C27B0');
paint(failureLine, 'Pattern Failure', '#FF5722');
paint(riskLine, 'Risk Level (Stop)', '#E91E63');
paint(breakoutLine, 'Breakout Target', '#66BB6A');
paint(breakdownLine, 'Breakdown Target', '#EF5350');</code>