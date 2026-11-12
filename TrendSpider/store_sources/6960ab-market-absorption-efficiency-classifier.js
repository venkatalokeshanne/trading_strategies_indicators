<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Market Absorption & Efficiency Classifier', 'overlay', {
  shortName: 'MAEC'
});

// ============================================
// INPUTS
// ============================================
const absorptionWindow = input.number('Absorption Window', 20, {min: 10, max: 50});
const efficiencyPeriod = input.number('Efficiency Period', 14, {min: 5, max: 30});
const volumeMultiple = input.number('High Volume Multiple', 1.5, {min: 1.2, max: 3.0, step: 0.1});
const exhaustionVolumeMultiple = input.number('Exhaustion Volume Multiple', 2.5, {min: 2.0, max: 4.0, step: 0.1});
const showAbsorptionLevels = input.boolean('Show Absorption Levels', true);
const paintCandles = input.boolean('Paint Candles', true);
const showDivergences = input.boolean('Show Volume Divergences', true);
const purpleSequenceMin = input.number('Purple Sequence Minimum', 2, {min: 2, max: 5});

// ============================================
// PROFESSIONAL COLOR PALETTE
// ============================================
const COLORS = {
  DEMAND_ABSORPTION: '#00FF88',      // Green - Institutional accumulation
  SUPPLY_ABSORPTION: '#0B3D91',      // Navy - Institutional distribution
  EFFICIENT_UP: '#00A8E1',           // Light blue - Smooth uptrend
  EFFICIENT_DOWN: '#BF00FF',         // Purple - Reversal warning zone
  CONSOLIDATION: '#FF6B35',          // Orange - High volume balance
  EXHAUSTION: '#FF003F',             // Red - Extreme exhaustion (rare)
  NEUTRAL: '#A0A0A0'                 // Gray - No edge
};

// ============================================
// CORE CALCULATIONS
// ============================================

// Calculate Volume-Weighted Average Price for period
function calculateVWAP(startIdx, endIdx) {
  let sumPV = 0, sumV = 0;
  for (let i = startIdx; i <= endIdx && i < close.length; i++) {
    const typicalPrice = (high[i] + low[i] + close[i]) / 3;
    const vol = volume[i] || 0;
    sumPV += typicalPrice * vol;
    sumV += vol;
  }
  return sumV > 0 ? sumPV / sumV : close[endIdx];
}

// Calculate price movement efficiency
function calculateEfficiency(idx, period) {
  if (idx < period) return 0;
  
  // Net price movement
  const netMove = Math.abs(close[idx] - close[idx - period]);
  
  // Sum of absolute movements
  let totalMove = 0;
  for (let i = 1; i <= period; i++) {
    totalMove += Math.abs(close[idx - i + 1] - close[idx - i]);
  }
  
  return totalMove > 0 ? netMove / totalMove : 0;
}

// Calculate average volume
function calculateAverageVolume(idx, window) {
  if (idx < window) return volume[idx] || 0;
  let avgVolume = 0;
  for (let i = 1; i <= window; i++) {
    avgVolume += volume[idx - i] || 0;
  }
  return avgVolume / window;
}

// Calculate average range
function calculateAverageRange(idx, period) {
  if (idx < period) return high[idx] - low[idx];
  let avgRange = 0;
  for (let i = 1; i <= period; i++) {
    avgRange += high[idx - i] - low[idx - i];
  }
  return avgRange / period;
}

// Detect volume absorption patterns
function detectAbsorption(idx, window) {
  if (idx < window) return { type: 'none', strength: 0 };
  
  const avgVolume = calculateAverageVolume(idx, window);
  const currentVol = volume[idx] || 0;
  const isHighVolume = currentVol > avgVolume * volumeMultiple;
  
  // Price metrics
  const range = high[idx] - low[idx];
  const body = Math.abs(close[idx] - open[idx]);
  const upperWick = high[idx] - Math.max(close[idx], open[idx]);
  const lowerWick = Math.min(close[idx], open[idx]) - low[idx];
  
  const avgRange = calculateAverageRange(idx, Math.min(14, idx));
  
  // Absorption patterns
  if (isHighVolume) {
    // High volume with small range = absorption
    if (range < avgRange * 0.7) {
      // Determine direction by close position in range
      const closePosition = range > 0 ? (close[idx] - low[idx]) / range : 0.5;
      
      if (closePosition > 0.7) {
        return { type: 'bullish_absorption', strength: currentVol / avgVolume };
      } else if (closePosition < 0.3) {
        return { type: 'bearish_absorption', strength: currentVol / avgVolume };
      } else {
        return { type: 'churning', strength: currentVol / avgVolume };
      }
    }
    
    // High volume with rejection wicks
    if (lowerWick > body * 2 && lowerWick > upperWick * 2) {
      return { type: 'bullish_absorption', strength: currentVol / avgVolume };
    } else if (upperWick > body * 2 && upperWick > lowerWick * 2) {
      return { type: 'bearish_absorption', strength: currentVol / avgVolume };
    }
  }
  
  return { type: 'none', strength: 0 };
}

// Volume price analysis for divergences
function volumePriceAnalysis(idx, period) {
  if (idx < period) return { divergence: false, type: 'none' };
  
  // Check for divergence
  const recentPriceMove = close[idx] - close[idx - Math.floor(period/2)];
  const recentVolTrend = volume[idx] - volume[idx - Math.floor(period/2)];
  
  // Bullish divergence: price down, volume up
  if (recentPriceMove < 0 && recentVolTrend > 0) {
    return { divergence: true, type: 'bullish' };
  }
  
  // Bearish divergence: price up, volume down  
  if (recentPriceMove > 0 && recentVolTrend < 0) {
    return { divergence: true, type: 'bearish' };
  }
  
  return { divergence: false, type: 'none' };
}

// ============================================
// ENHANCED STATE DETERMINATION
// ============================================

function determineMarketState(idx, absorption, efficiency, vpAnalysis, avgVolume, avgRange) {
  const currentVol = volume[idx] || 0;
  const currentRange = high[idx] - low[idx];
  const bodySize = Math.abs(close[idx] - open[idx]);
  const priceDirection = close[idx] > open[idx] ? 1 : -1;
  
  // First priority: Absorption patterns (highest reliability)
  if (absorption.type === 'bullish_absorption') {
    return 'DEMAND_ABSORPTION';
  } else if (absorption.type === 'bearish_absorption') {
    return 'SUPPLY_ABSORPTION';
  } else if (absorption.type === 'churning') {
    return 'CONSOLIDATION';
  }
  
  // Second priority: Efficiency patterns
  if (efficiency > 0.7) {
    return priceDirection > 0 ? 'EFFICIENT_UP' : 'EFFICIENT_DOWN';
  }
  
  // Third priority: HIGHLY SELECTIVE exhaustion detection
  // Only mark exhaustion with multiple confirmations
  if (efficiency < 0.2 && // Very low efficiency
      currentVol > avgVolume * exhaustionVolumeMultiple && // Extreme volume
      bodySize < avgRange * 0.3 && // Tiny body relative to average
      currentRange > avgRange * 1.5 && // Large range (wicks)
      vpAnalysis.divergence) { // Must have volume divergence
    return 'EXHAUSTION';
  }
  
  return 'NEUTRAL';
}

// ============================================
// MAIN ANALYSIS LOOP WITH PURPLE SEQUENCE
// ============================================

const marketState = [];
const absorptionLevels = series_of(null);
const efficiencyRatio = series_of(0);
const volumeDivergence = series_of(false);
const purpleSequence = series_of(0);
const absorptionZones = [];

let purpleCount = 0;
let maxPurpleStreak = 0;

for (let i = 0; i < time.length; i++) {
  // Calculate metrics
  const efficiency = calculateEfficiency(i, efficiencyPeriod);
  efficiencyRatio[i] = efficiency;
  
  const absorption = detectAbsorption(i, absorptionWindow);
  const vpAnalysis = volumePriceAnalysis(i, efficiencyPeriod);
  const avgVolume = calculateAverageVolume(i, absorptionWindow);
  const avgRange = calculateAverageRange(i, 14);
  
  // Determine market state
  const state = determineMarketState(i, absorption, efficiency, vpAnalysis, avgVolume, avgRange);
  marketState[i] = state;
  
  // Track purple candle sequences (EFFICIENT_DOWN)
  if (state === 'EFFICIENT_DOWN') {
    purpleCount++;
    purpleSequence[i] = purpleCount;
    maxPurpleStreak = Math.max(maxPurpleStreak, purpleCount);
  } else {
    // Reset counter but check if we just ended a significant streak
    if (purpleCount >= purpleSequenceMin) {
      // Mark the bar after purple sequence ends as potential reversal
      purpleSequence[i] = -purpleCount; // Negative to indicate sequence just ended
    }
    purpleCount = 0;
  }
  
  // Mark volume divergences
  if (vpAnalysis.divergence && showDivergences) {
    volumeDivergence[i] = true;
  }
  
  // Track absorption zones for support/resistance levels
  if (absorption.type !== 'none' && absorption.strength > 2 && showAbsorptionLevels) {
    if (absorption.type === 'bullish_absorption') {
      absorptionZones.push({
        index: i,
        price: low[i],
        type: 'support',
        strength: absorption.strength
      });
    } else if (absorption.type === 'bearish_absorption') {
      absorptionZones.push({
        index: i,
        price: high[i],
        type: 'resistance',
        strength: absorption.strength
      });
    }
  }
}

// ============================================
// ABSORPTION LEVEL MANAGEMENT
// ============================================

// Keep only the 5 most recent strong absorption zones
absorptionZones.sort((a, b) => b.index - a.index);
const recentZones = absorptionZones.slice(0, 5);

// Create series for absorption levels
const supportLevel1 = series_of(null);
const supportLevel2 = series_of(null);
const resistanceLevel1 = series_of(null);
const resistanceLevel2 = series_of(null);

const supports = recentZones.filter(z => z.type === 'support');
const resistances = recentZones.filter(z => z.type === 'resistance');

// Draw horizontal lines from absorption points
if (supports.length > 0) {
  for (let i = supports[0].index; i < time.length; i++) {
    supportLevel1[i] = supports[0].price;
  }
}
if (supports.length > 1) {
  for (let i = supports[1].index; i < time.length; i++) {
    supportLevel2[i] = supports[1].price;
  }
}
if (resistances.length > 0) {
  for (let i = resistances[0].index; i < time.length; i++) {
    resistanceLevel1[i] = resistances[0].price;
  }
}
if (resistances.length > 1) {
  for (let i = resistances[1].index; i < time.length; i++) {
    resistanceLevel2[i] = resistances[1].price;
  }
}

// ============================================
// CANDLE PAINTING
// ============================================

if (paintCandles) {
  const candleColors = [];
  
  for (let i = 0; i < time.length; i++) {
    switch(marketState[i]) {
      case 'DEMAND_ABSORPTION':
        candleColors[i] = COLORS.DEMAND_ABSORPTION;
        break;
      case 'SUPPLY_ABSORPTION':
        candleColors[i] = COLORS.SUPPLY_ABSORPTION;
        break;
      case 'EFFICIENT_UP':
        candleColors[i] = COLORS.EFFICIENT_UP;
        break;
      case 'EFFICIENT_DOWN':
        candleColors[i] = COLORS.EFFICIENT_DOWN;
        break;
      case 'CONSOLIDATION':
        candleColors[i] = COLORS.CONSOLIDATION;
        break;
      case 'EXHAUSTION':
        candleColors[i] = COLORS.EXHAUSTION;
        break;
      default:
        candleColors[i] = null;
    }
  }
  
  color_candles(candleColors);
}

// ============================================
// PAINT ABSORPTION LEVELS
// ============================================

if (showAbsorptionLevels) {
  paint(supportLevel1, {
    name: 'Primary Support',
    color: COLORS.DEMAND_ABSORPTION,
    style: 'line',
    width: 2,
    opacity: 0.6
  });
  
  paint(supportLevel2, {
    name: 'Secondary Support',
    color: COLORS.DEMAND_ABSORPTION,
    style: 'dotted',
    width: 1,
    opacity: 0.4
  });
  
  paint(resistanceLevel1, {
    name: 'Primary Resistance',
    color: COLORS.SUPPLY_ABSORPTION,
    style: 'line',
    width: 2,
    opacity: 0.6
  });
  
  paint(resistanceLevel2, {
    name: 'Secondary Resistance',
    color: COLORS.SUPPLY_ABSORPTION,
    style: 'dotted',
    width: 1,
    opacity: 0.4
  });
}

// ============================================
// ENHANCED SIGNAL DETECTION
// ============================================

// State signals
const demandAbsorption = series_of(false);
const supplyAbsorption = series_of(false);
const efficientUp = series_of(false);
const efficientDown = series_of(false);
const consolidation = series_of(false);
const exhaustion = series_of(false);

// Enhanced purple sequence signals
const purpleWarning = series_of(false);
const purpleReversal = series_of(false);
const purpleExtreme = series_of(false);

// Transition signals
const efficiencyBreakout = series_of(false);
const absorptionBreakdown = series_of(false);

for (let i = 1; i < time.length; i++) {
  const currentState = marketState[i];
  const prevState = marketState[i-1];
  
  // State signals (persistent)
  demandAbsorption[i] = (currentState === 'DEMAND_ABSORPTION');
  supplyAbsorption[i] = (currentState === 'SUPPLY_ABSORPTION');
  efficientUp[i] = (currentState === 'EFFICIENT_UP');
  efficientDown[i] = (currentState === 'EFFICIENT_DOWN');
  consolidation[i] = (currentState === 'CONSOLIDATION');
  exhaustion[i] = (currentState === 'EXHAUSTION');
  
  // Enhanced purple sequence signals
  if (purpleSequence[i] === purpleSequenceMin) {
    purpleWarning[i] = true; // Minimum sequence reached
  }
  
  if (purpleSequence[i] >= purpleSequenceMin + 1) {
    purpleReversal[i] = true; // Strong reversal signal
  }
  
  if (purpleSequence[i] >= 4) {
    purpleExtreme[i] = true; // Extreme oversold/reversal
  }
  
  // Check if purple sequence just ended (potential reversal point)
  if (purpleSequence[i] < 0 && Math.abs(purpleSequence[i]) >= purpleSequenceMin) {
    purpleReversal[i] = true; // Mark reversal at sequence end
  }
  
  // Efficiency breakout (transition signal)
  if ((currentState === 'EFFICIENT_UP' || currentState === 'EFFICIENT_DOWN') &&
      efficiencyRatio[i] > 0.8 && efficiencyRatio[i-1] < 0.5) {
    efficiencyBreakout[i] = true;
  }
  
  // Absorption breakdown (transition signal)
  if (currentState === 'EXHAUSTION' && 
      (prevState === 'DEMAND_ABSORPTION' || prevState === 'SUPPLY_ABSORPTION')) {
    absorptionBreakdown[i] = true;
  }
}

// ============================================
// REGISTER SIGNALS WITH PROFESSIONAL DESCRIPTIONS
// ============================================

// State signals
register_signal(demandAbsorption, '🟢 GREEN CANDLE - Demand Absorption');
register_signal(supplyAbsorption, '🔵 NAVY CANDLE - Supply Absorption');
register_signal(efficientUp, '🔷 LIGHT BLUE CANDLE - Efficient Uptrend');
register_signal(efficientDown, '🟣 PURPLE CANDLE - Efficient Decline');
register_signal(consolidation, '🟠 ORANGE CANDLE - High Volume Consolidation');
register_signal(exhaustion, '🔴 RED CANDLE - Extreme Exhaustion');


// Transition signals
register_signal(efficiencyBreakout, '⚡ Efficiency Surge - Directional Acceleration');
register_signal(absorptionBreakdown, '💥 Absorption Failure - Support/Resistance Break');
register_signal(volumeDivergence, '📊 Volume/Price Divergence - Trend Inconsistency');
</code>