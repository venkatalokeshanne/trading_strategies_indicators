<code x-ref="code" class="hljs" data-clipboard-text>// ============================================================================
// VOLATILITY REGIME CLASSIFIER (VRC)
// Multi-estimator volatility analysis with regime detection
// Version: 3.0 - Risk-Based Position Sizing Framework
// ============================================================================

describe_indicator('Volatility Regime Classifier', 'lower', {
  shortName: 'VRC',
  version: '3.0',
  description: 'Advanced volatility structure with regime classification, VCP detection, and risk-based position sizing'
});

// ============================================================================
// INPUTS
// ============================================================================

// Volatility Calculation Parameters
const volPeriod = input.number('Volatility Period', 20, {min: 10, max: 50});
const volLookback = input.number('Regime Lookback', 50, {min: 20, max: 100});
const smoothing = input.number('Smoothing Period', 5, {min: 1, max: 10});

// Regime Classification Parameters
const trendThreshold = input.number('Trend Threshold', 1.5, {min: 1.0, max: 3.0, step: 0.1});
const meanRevThreshold = input.number('Mean Reversion Threshold', 0.7, {min: 0.3, max: 1.0, step: 0.05});
const regimeConfidence = input.number('Min Regime Confidence', 65, {min: 50, max: 90});

// VCP Detection Parameters
const vcpContractionThreshold = input.number('VCP Contraction %', 60, {min: 40, max: 80});
const vcpMinPeriods = input.number('VCP Min Periods', 10, {min: 5, max: 20});
const vcpMaxPeriods = input.number('VCP Max Periods', 40, {min: 20, max: 60});

// Expansion/Contraction Parameters
const expansionThreshold = input.number('Expansion Threshold', 1.3, {min: 1.1, max: 2.0, step: 0.1});
const contractionThreshold = input.number('Contraction Threshold', 0.7, {min: 0.3, max: 0.9, step: 0.05});

// Risk Management Parameters (NEW)
const elevatedRiskZScore = input.number('Elevated Risk Z-Score', 1.5, {min: 1.0, max: 2.0, step: 0.1});
const highRiskZScore = input.number('High Risk Z-Score', 2.0, {min: 1.5, max: 2.5, step: 0.1});
const extremeRiskZScore = input.number('Extreme Risk Z-Score', 2.5, {min: 2.0, max: 3.5, step: 0.1});
const zScoreHysteresis = input.number('Z-Score Exit Hysteresis', 0.3, {min: 0.2, max: 1.0, step: 0.1});

// Position Sizing Multipliers (NEW)
const elevatedRiskSize = input.number('Elevated Risk Size %', 50, {min: 25, max: 75, step: 5});
const highRiskSize = input.number('High Risk Size %', 25, {min: 10, max: 50, step: 5});
const extremeRiskSize = input.number('Extreme Risk Size %', 10, {min: 5, max: 25, step: 5});

// Display Options
const showParkinson = input.boolean('Show Parkinson Vol', true);
const showGarmanKlass = input.boolean('Show Garman-Klass Vol', true);
const showYangZhang = input.boolean('Show Yang-Zhang Vol', true);
const showComposite = input.boolean('Show Composite Vol', true);
const showRegimeBands = input.boolean('Show Regime Bands', true);
const showVolatilityBands = input.boolean('Show Volatility Bands', false);
const showVolZScore = input.boolean('Show Vol Z-Score', false);
const showZScoreRefs = input.boolean('Show Z-Score References', false);
const showRiskZones = input.boolean('Show Risk Zones', true);

// ============================================================================
// COLOR PALETTE - Synthwave/Volatility Theme
// ============================================================================

const COLORS = {
  // Regime colors
  LOW_VOL: '#00FF00',           // Green - low volatility
  NORMAL_VOL: '#FFD700',        // Gold - normal volatility
  HIGH_VOL: '#FF6347',          // Red - high volatility
  EXTREME_VOL: '#FF0000',       // Bright red - extreme volatility
  
  // Regime types
  TRENDING: '#00FFFF',          // Cyan - trending regime
  MEAN_REVERTING: '#FF00FF',    // Magenta - mean reverting
  TRANSITIONAL: '#FFFF00',      // Yellow - transitional
  CHOPPY: '#FF6347',            // Red - choppy/undefined
  
  // Vol state
  EXPANDING: '#FF1493',         // Deep pink - expanding
  CONTRACTING: '#00CED1',       // Turquoise - contracting
  STABLE: '#9370DB',            // Purple - stable
  
  // VCP
  VCP_ACTIVE: '#00FF00',        // Green - VCP in progress
  VCP_BREAKOUT: '#00FFFF',      // Cyan - VCP breakout
  
  // Risk Levels (NEW)
  RISK_NORMAL: '#00FF00',       // Green - normal risk
  RISK_ELEVATED: '#FFD700',     // Gold - elevated risk
  RISK_HIGH: '#FFA500',         // Orange - high risk
  RISK_EXTREME: '#FF0000',      // Red - extreme risk
  RISK_CAPITULATION: '#FF00FF', // Magenta - possible capitulation
  
  // Dashboard
  PANEL_BG: '#1A1A2EDD',        // Deep space
  TEXT: '#FFFFFF',
  
  // Estimators
  PARKINSON: '#00CED1',
  GARMAN_KLASS: '#9370DB',
  YANG_ZHANG: '#FF69B4',
  COMPOSITE: '#00FF00'
};

// ============================================================================
// MATHEMATICAL FUNCTIONS
// ============================================================================

function calcSMA(data, period, idx) {
  if (idx < period - 1) return data[idx];
  let total = 0;
  for (let i = 0; i < period; i++) {
    total += data[idx - i];
  }
  return total / period;
}

function calcEMA(data, period, idx, prevEMA) {
  if (idx === 0) return data[0];
  const alpha = 2 / (period + 1);
  return alpha * data[idx] + (1 - alpha) * (prevEMA || data[idx]);
}

function calcStdDev(data, period, idx) {
  if (idx < period - 1) return 0;
  const mean = calcSMA(data, period, idx);
  let sumSquaredDiff = 0;
  for (let i = 0; i < period; i++) {
    const diff = data[idx - i] - mean;
    sumSquaredDiff += diff * diff;
  }
  return Math.sqrt(sumSquaredDiff / period);
}

function calcPercentile(data, period, idx, percentile) {
  if (idx < period - 1) return data[idx];
  const window = [];
  for (let i = 0; i < period; i++) {
    window.push(data[idx - i]);
  }
  window.sort(function(a, b) { return a - b; });
  const index = Math.floor(window.length * percentile);
  return window[index];
}

// ============================================================================
// VOLATILITY ESTIMATORS
// ============================================================================

/**
 * Parkinson's Volatility (High-Low Range Estimator)
 * More efficient than close-to-close, uses intraday range
 * Assumes no overnight gaps
 */
function calcParkinsonVolatility(high, low, period, idx) {
  if (idx < period - 1) return 0;
  
  let sumLogRatioSquared = 0;
  for (let i = 0; i < period; i++) {
    const h = high[idx - i];
    const l = low[idx - i];
    if (l > 0 && h > 0) {
      const logRatio = Math.log(h / l);
      sumLogRatioSquared += logRatio * logRatio;
    }
  }
  
  // Parkinson constant: 1/(4*ln(2))
  const parkinsonConstant = 1 / (4 * Math.log(2));
  const varianceVal = parkinsonConstant * (sumLogRatioSquared / period);
  
  // Annualized volatility (assuming 252 trading days)
  return Math.sqrt(varianceVal * 252) * 100;
}

/**
 * Garman-Klass Volatility (OHLC Estimator)
 * Most efficient unbiased estimator using all OHLC data
 * Assumes no overnight gaps and zero drift
 */
function calcGarmanKlassVolatility(open, high, low, close, period, idx) {
  if (idx < period - 1) return 0;
  
  let sumVariance = 0;
  for (let i = 0; i < period; i++) {
    const o = open[idx - i];
    const h = high[idx - i];
    const l = low[idx - i];
    const c = close[idx - i];
    
    if (l > 0 && h > 0 && o > 0 && c > 0) {
      const hlTerm = 0.5 * Math.pow(Math.log(h / l), 2);
      const ocTerm = (2 * Math.log(2) - 1) * Math.pow(Math.log(c / o), 2);
      sumVariance += hlTerm - ocTerm;
    }
  }
  
  const varianceVal = sumVariance / period;
  return Math.sqrt(varianceVal * 252) * 100;
}

/**
 * Yang-Zhang Volatility (Overnight + Intraday Components)
 * Most robust estimator, accounts for opening gaps
 * Handles drift and overnight jumps
 */
function calcYangZhangVolatility(open, high, low, close, period, idx) {
  if (idx < period - 1) return 0;
  
  // Opening jump volatility
  let sumOpenJump = 0;
  let sumOpenJumpSq = 0;
  
  for (let i = 1; i < period; i++) {
    const prevClose = close[idx - i];
    const currOpen = open[idx - i + 1];
    if (prevClose > 0 && currOpen > 0) {
      const jump = Math.log(currOpen / prevClose);
      sumOpenJump += jump;
      sumOpenJumpSq += jump * jump;
    }
  }
  
  const meanOpenJump = sumOpenJump / (period - 1);
  const openVariance = (sumOpenJumpSq / (period - 1)) - (meanOpenJump * meanOpenJump);
  
  // Close-to-close volatility
  let sumClose = 0;
  let sumCloseSq = 0;
  
  for (let i = 1; i < period; i++) {
    const prevClose = close[idx - i];
    const currClose = close[idx - i + 1];
    if (prevClose > 0 && currClose > 0) {
      const ret = Math.log(currClose / prevClose);
      sumClose += ret;
      sumCloseSq += ret * ret;
    }
  }
  
  const meanClose = sumClose / (period - 1);
  const closeVariance = (sumCloseSq / (period - 1)) - (meanClose * meanClose);
  
  // Rogers-Satchell volatility (intraday)
  let sumRS = 0;
  for (let i = 0; i < period; i++) {
    const o = open[idx - i];
    const h = high[idx - i];
    const l = low[idx - i];
    const c = close[idx - i];
    
    if (o > 0 && h > 0 && l > 0 && c > 0) {
      const rs = Math.log(h / c) * Math.log(h / o) + Math.log(l / c) * Math.log(l / o);
      sumRS += rs;
    }
  }
  
  const rsVariance = sumRS / period;
  
  // Yang-Zhang combines all components with optimal weights
  const k = 0.34 / (1.34 + (period + 1) / (period - 1));
  const yzVariance = openVariance + k * closeVariance + (1 - k) * rsVariance;
  
  return Math.sqrt(Math.max(0, yzVariance) * 252) * 100;
}

/**
 * Composite Volatility (Weighted Average of Estimators)
 */
function calcCompositeVolatility(parkinson, garmanKlass, yangZhang) {
  // Weighted average: Yang-Zhang gets highest weight (most robust)
  // Garman-Klass second (efficient with OHLC)
  // Parkinson third (simple but useful)
  return (yangZhang * 0.5 + garmanKlass * 0.3 + parkinson * 0.2);
}

// ============================================================================
// REGIME CLASSIFICATION
// ============================================================================

/**
 * Calculate Variance Ratio for regime detection
 * Ratio > 1: Trending
 * Ratio < 1: Mean reverting
 * Ratio ≈ 1: Random walk
 */
function calcVarianceRatio(prices, shortPeriod, longPeriod, idx) {
  if (idx < longPeriod) return 1;
  
  // Short-period variance
  let shortVar = 0;
  for (let i = 1; i < shortPeriod; i++) {
    const ret = (prices[idx - i + 1] - prices[idx - i]) / prices[idx - i];
    shortVar += ret * ret;
  }
  shortVar = shortVar / (shortPeriod - 1);
  
  // Long-period variance
  let longVar = 0;
  const ratio = Math.floor(longPeriod / shortPeriod);
  for (let i = 1; i < ratio; i++) {
    const start = idx - i * shortPeriod;
    const end = idx - (i - 1) * shortPeriod;
    if (start >= 0 && end < prices.length) {
      const ret = (prices[end] - prices[start]) / prices[start];
      longVar += ret * ret;
    }
  }
  longVar = longVar / (ratio - 1);
  
  // Variance ratio
  if (shortVar === 0) return 1;
  return longVar / (shortVar * ratio);
}

/**
 * Classify market regime based on multiple factors
 * Returns regime type, confidence, and Z-score for risk assessment
 */
function classifyRegime(varianceRatio, vol, volMA, volStdDev, trendThresh, meanRevThresh) {
  const volZScore = volStdDev > 0 ? (vol - volMA) / volStdDev : 0;
  
  let regime = 'transitional';
  let confidence = 50;
  
  // Trending regime: high variance ratio + expanding volatility
  if (varianceRatio > trendThresh) {
    regime = 'trending';
    confidence = Math.min(90, 50 + (varianceRatio - trendThresh) * 20);
    if (volZScore > 0.5) confidence += 10;
  }
  // Mean reverting: low variance ratio + contracting volatility
  else if (varianceRatio < meanRevThresh) {
    regime = 'mean_reverting';
    confidence = Math.min(90, 50 + (meanRevThresh - varianceRatio) * 30);
    if (volZScore < -0.5) confidence += 10;
  }
  // Transitional: variance ratio near 1
  else {
    confidence = 50 + Math.abs(volZScore) * 10;
    
    // Check if choppy (high vol + no clear trend)
    if (volZScore > 1.5) {
      regime = 'choppy';
      confidence = Math.min(85, confidence + 15);
    }
  }
  
  return {
    regime: regime,
    confidence: Math.min(95, confidence),
    varianceRatio: varianceRatio,
    volZScore: volZScore
  };
}

// ============================================================================
// RISK ASSESSMENT (NEW)
// ============================================================================

/**
 * Assess risk level and position sizing based on Z-score
 * Returns risk level, position size multiplier, and status
 */
function assessRisk(zScore, elevatedThresh, highThresh, extremeThresh, elevatedSize, highSize, extremeSize) {
  const absZ = Math.abs(zScore);
  
  let riskLevel = 'NORMAL';
  let positionSize = 100;
  let riskColor = COLORS.RISK_NORMAL;
  let riskEmoji = '✅';
  
  if (absZ >= extremeThresh) {
    riskLevel = 'EXTREME';
    positionSize = extremeSize;
    riskColor = COLORS.RISK_EXTREME;
    riskEmoji = '🔥';
  } else if (absZ >= highThresh) {
    riskLevel = 'HIGH';
    positionSize = highSize;
    riskColor = COLORS.RISK_HIGH;
    riskEmoji = '⚠️';
  } else if (absZ >= elevatedThresh) {
    riskLevel = 'ELEVATED';
    positionSize = elevatedSize;
    riskColor = COLORS.RISK_ELEVATED;
    riskEmoji = '⚡';
  }
  
  // Special case: Extreme negative Z-score (low volatility)
  if (zScore < -extremeThresh) {
    riskLevel = 'LOW VOL';
    positionSize = 100;
    riskColor = COLORS.RISK_NORMAL;
    riskEmoji = '💤';
  }
  
  return {
    level: riskLevel,
    positionSize: positionSize,
    color: riskColor,
    emoji: riskEmoji,
    zScore: zScore
  };
}

// ============================================================================
// VCP (VOLATILITY CONTRACTION PATTERN) DETECTION
// ============================================================================

/**
 * Detect Volatility Contraction Pattern (Mark Minervini style)
 * Identifies periods where volatility contracts before expansion
 */
function detectVCP(volatility, period, idx, minPeriods, maxPeriods, contractionThreshold) {
  if (idx < maxPeriods) {
    return {
      isVCP: false,
      contractionPercent: 0,
      periodLength: 0,
      quality: 0
    };
  }
  
  // Find recent high volatility
  let maxVol = 0;
  for (let i = minPeriods; i <= maxPeriods; i++) {
    if (volatility[idx - i] > maxVol) {
      maxVol = volatility[idx - i];
    }
  }
  
  // Calculate current volatility as percentage of recent high
  const currentVol = volatility[idx];
  const contractionPercent = maxVol > 0 ? ((maxVol - currentVol) / maxVol) * 100 : 0;
  
  // Count consecutive periods of contraction
  let contractionLength = 0;
  for (let i = 0; i < maxPeriods; i++) {
    if (volatility[idx - i] < volatility[idx - i - 1]) {
      contractionLength++;
    } else {
      break;
    }
  }
  
  // VCP detected if significant contraction over min periods
  const isVCP = contractionPercent >= contractionThreshold && 
                contractionLength >= minPeriods;
  
  // Quality score based on contraction depth and consistency
  let quality = 0;
  if (isVCP) {
    quality = Math.min(100, contractionPercent + (contractionLength * 2));
  }
  
  return {
    isVCP: isVCP,
    contractionPercent: contractionPercent,
    periodLength: contractionLength,
    quality: quality
  };
}

// ============================================================================
// DATA SERIES INITIALIZATION
// ============================================================================

const parkinsonVol = series_of(0);
const garmanKlassVol = series_of(0);
const yangZhangVol = series_of(0);
const compositeVol = series_of(0);
const smoothedVol = series_of(0);

const volMA = series_of(0);
const volStdDev = series_of(0);
const upperBand = series_of(0);
const lowerBand = series_of(0);

const varianceRatio = series_of(1);
const regimeType = [];
const regimeConfidenceScore = series_of(50);
const regimeZScore = series_of(0);

// Risk assessment series (NEW)
const riskLevel = [];
const positionSizePercent = series_of(100);
const riskColor = [];

const vcpActive = series_of(false);
const vcpQuality = series_of(0);
const vcpContraction = series_of(0);

const volState = [];  // 'expanding', 'contracting', 'stable'
const volPercentile = series_of(50);

// ============================================================================
// MAIN CALCULATIONS
// ============================================================================

// Calculate volatility estimators
for (let i = 0; i < close.length; i++) {
  if (i >= volPeriod - 1) {
    parkinsonVol[i] = calcParkinsonVolatility(high, low, volPeriod, i);
    garmanKlassVol[i] = calcGarmanKlassVolatility(open, high, low, close, volPeriod, i);
    yangZhangVol[i] = calcYangZhangVolatility(open, high, low, close, volPeriod, i);
    compositeVol[i] = calcCompositeVolatility(parkinsonVol[i], garmanKlassVol[i], yangZhangVol[i]);
  } else {
    parkinsonVol[i] = 0;
    garmanKlassVol[i] = 0;
    yangZhangVol[i] = 0;
    compositeVol[i] = 0;
  }
}

// Smooth composite volatility
let prevEMA = compositeVol[0];
for (let i = 0; i < close.length; i++) {
  smoothedVol[i] = calcEMA(compositeVol, smoothing, i, prevEMA);
  prevEMA = smoothedVol[i];
}

// Calculate volatility statistics and bands
for (let i = 0; i < close.length; i++) {
  if (i >= volLookback) {
    volMA[i] = calcSMA(smoothedVol, volLookback, i);
    volStdDev[i] = calcStdDev(smoothedVol, volLookback, i);
    upperBand[i] = volMA[i] + (volStdDev[i] * 2);
    lowerBand[i] = Math.max(0, volMA[i] - (volStdDev[i] * 2));
    volPercentile[i] = calcPercentile(smoothedVol, volLookback, i, 0.5);
  } else {
    volMA[i] = smoothedVol[i];
    volStdDev[i] = 0;
    upperBand[i] = smoothedVol[i];
    lowerBand[i] = smoothedVol[i];
    volPercentile[i] = smoothedVol[i];
  }
}

// Calculate variance ratio and classify regime
for (let i = 0; i < close.length; i++) {
  if (i >= volLookback) {
    varianceRatio[i] = calcVarianceRatio(close, volPeriod, volLookback, i);
    
    const classification = classifyRegime(
      varianceRatio[i],
      smoothedVol[i],
      volMA[i],
      volStdDev[i],
      trendThreshold,
      meanRevThreshold
    );
    
    regimeType[i] = classification.regime;
    regimeConfidenceScore[i] = classification.confidence;
    regimeZScore[i] = classification.volZScore;
    
    // NEW: Assess risk and position sizing
    const risk = assessRisk(
      classification.volZScore,
      elevatedRiskZScore,
      highRiskZScore,
      extremeRiskZScore,
      elevatedRiskSize,
      highRiskSize,
      extremeRiskSize
    );
    
    riskLevel[i] = risk.level;
    positionSizePercent[i] = risk.positionSize;
    riskColor[i] = risk.color;
    
  } else {
    varianceRatio[i] = 1;
    regimeType[i] = 'transitional';
    regimeConfidenceScore[i] = 50;
    regimeZScore[i] = 0;
    riskLevel[i] = 'NORMAL';
    positionSizePercent[i] = 100;
    riskColor[i] = COLORS.RISK_NORMAL;
  }
}

// Detect volatility state (expanding/contracting/stable)
for (let i = 1; i < close.length; i++) {
  const volChange = smoothedVol[i] / smoothedVol[i - 1];
  
  if (volChange > expansionThreshold) {
    volState[i] = 'expanding';
  } else if (volChange < contractionThreshold) {
    volState[i] = 'contracting';
  } else {
    volState[i] = 'stable';
  }
}
volState[0] = 'stable';

// Detect VCP patterns
for (let i = 0; i < close.length; i++) {
  if (i >= vcpMaxPeriods) {
    const vcp = detectVCP(
      smoothedVol,
      volPeriod,
      i,
      vcpMinPeriods,
      vcpMaxPeriods,
      vcpContractionThreshold
    );
    
    vcpActive[i] = vcp.isVCP;
    vcpQuality[i] = vcp.quality;
    vcpContraction[i] = vcp.contractionPercent;
  }
}

// ============================================================================
// VISUALIZATION
// ============================================================================

// Individual estimators
if (showParkinson) {
  paint(parkinsonVol, {
    name: 'Parkinson Vol',
    color: COLORS.PARKINSON,
    style: 'line',
    thickness: 1,
    opacity: 0.6
  });
}

if (showGarmanKlass) {
  paint(garmanKlassVol, {
    name: 'Garman-Klass Vol',
    color: COLORS.GARMAN_KLASS,
    style: 'line',
    thickness: 1,
    opacity: 0.6
  });
}

if (showYangZhang) {
  paint(yangZhangVol, {
    name: 'Yang-Zhang Vol',
    color: COLORS.YANG_ZHANG,
    style: 'line',
    thickness: 1,
    opacity: 0.6
  });
}

// Composite volatility with regime-aware coloring
if (showComposite) {
  const compositeColors = [];
  
  for (let i = 0; i < smoothedVol.length; i++) {
    const regime = regimeType[i];
    const state = volState[i];
    const risk = riskLevel[i];
    
    // Priority: Risk level colors for extreme states, then regime colors
    if (risk === 'EXTREME' || risk === 'HIGH') {
      compositeColors[i] = riskColor[i];
    } else if (vcpActive[i]) {
      compositeColors[i] = COLORS.VCP_ACTIVE;
    } else if (regime === 'trending') {
      compositeColors[i] = COLORS.TRENDING;
    } else if (regime === 'mean_reverting') {
      compositeColors[i] = COLORS.MEAN_REVERTING;
    } else if (regime === 'choppy') {
      compositeColors[i] = COLORS.CHOPPY;
    } else if (state === 'expanding') {
      compositeColors[i] = COLORS.EXPANDING;
    } else if (state === 'contracting') {
      compositeColors[i] = COLORS.CONTRACTING;
    } else {
      compositeColors[i] = COLORS.STABLE;
    }
  }
  
  paint(smoothedVol, {
    name: 'Composite Vol',
    colors: compositeColors,
    thickness: 3,
    opacity: 1
  });
}

// Volatility bands
if (showVolatilityBands) {
  paint(upperBand, {
    name: 'Upper Band',
    color: COLORS.HIGH_VOL,
    style: 'line',
    thickness: 1,
    opacity: 0.4
  });
  
  paint(lowerBand, {
    name: 'Lower Band',
    color: COLORS.LOW_VOL,
    style: 'line',
    thickness: 1,
    opacity: 0.4
  });
}

// Z-Score line with risk-based coloring
if (showVolZScore) {
  const zScoreColors = [];
  
  for (let i = 0; i < regimeZScore.length; i++) {
    zScoreColors[i] = riskColor[i];
  }
  
  paint(regimeZScore, {
    name: 'Vol Z-Score',
    colors: zScoreColors,
    style: 'line',
    thickness: 2,
    opacity: 0.8
  });
}

// Z-Score reference lines with risk zones
if (showZScoreRefs && showVolZScore) {
  // Create constant series for each reference level
  const extremeRiskLine = series_of(extremeRiskZScore);
  const extremeLowLine = series_of(-extremeRiskZScore);
  const highRiskLine = series_of(highRiskZScore);
  const highRiskLowLine = series_of(-highRiskZScore);
  const elevatedRiskLine = series_of(elevatedRiskZScore);
  const elevatedRiskLowLine = series_of(-elevatedRiskZScore);
  const zeroLine = series_of(0);
  
  // Paint extreme risk levels (solid lines)
  paint(extremeRiskLine, {
    name: `Extreme Risk (+${extremeRiskZScore}σ)`,
    color: COLORS.RISK_EXTREME,
    style: 'line',
    thickness: 2,
    opacity: 0.7
  });
  
  paint(extremeLowLine, {
    name: `Extreme Low Vol (-${extremeRiskZScore}σ)`,
    color: COLORS.RISK_NORMAL,
    style: 'line',
    thickness: 2,
    opacity: 0.7
  });
  
  // Paint high risk levels (dotted)
  paint(highRiskLine, {
    name: `High Risk (+${highRiskZScore}σ)`,
    color: COLORS.RISK_HIGH,
    style: 'dotted',
    thickness: 1,
    opacity: 0.6
  });
  
  // Paint elevated risk levels (dotted)
  paint(elevatedRiskLine, {
    name: `Elevated Risk (+${elevatedRiskZScore}σ)`,
    color: COLORS.RISK_ELEVATED,
    style: 'dotted',
    thickness: 1,
    opacity: 0.5
  });
  
  // Paint zero line
  paint(zeroLine, {
    name: 'Z-Score Zero',
    color: COLORS.TEXT,
    style: 'line',
    thickness: 1,
    opacity: 0.3
  });
}

// Regime bands (reference lines)
if (showRegimeBands) {
  // Calculate dynamic reference levels
  let avgVol = 0;
  let count = 0;
  for (let i = Math.max(0, close.length - volLookback); i < close.length; i++) {
    avgVol += smoothedVol[i];
    count++;
  }
  avgVol = count > 0 ? avgVol / count : 20;
  
  horizontal_line(avgVol * 1.5, {
    name: 'High Vol',
    color: COLORS.HIGH_VOL,
    style: 'dotted',
    thickness: 1,
    opacity: 0.5
  });
  
  horizontal_line(avgVol, {
    name: 'Normal Vol',
    color: COLORS.NORMAL_VOL,
    style: 'line',
    thickness: 1,
    opacity: 0.3
  });
  
  horizontal_line(avgVol * 0.5, {
    name: 'Low Vol',
    color: COLORS.LOW_VOL,
    style: 'dotted',
    thickness: 1,
    opacity: 0.5
  });
}

// ============================================================================
// SIGNAL DETECTION
// ============================================================================

const volExpansion = series_of(false);
const volContraction = series_of(false);
const extremeVolatility = series_of(false);
const lowVolatility = series_of(false);
const regimeTrending = series_of(false);
const regimeMeanReverting = series_of(false);
const regimeChoppy = series_of(false);
const vcpDetected = series_of(false);
const vcpBreakout = series_of(false);
const highConfidenceRegime = series_of(false);

// NEW: Risk-based signals (position sizing alerts)
const elevatedRiskEntered = series_of(false);
const highRiskEntered = series_of(false);
const extremeRiskEntered = series_of(false);
const riskNormalized = series_of(false);
const possibleCapitulation = series_of(false);
const premiumCompressionZone = series_of(false);
const volAwakening = series_of(false);

for (let i = volLookback + 1; i < close.length; i++) {
  // Volatility expansion
  if (volState[i] === 'expanding' && volState[i-1] !== 'expanding') {
    volExpansion[i] = true;
  }
  
  // Volatility contraction
  if (volState[i] === 'contracting' && volState[i-1] !== 'contracting') {
    volContraction[i] = true;
  }
  
  // Extreme volatility
  if (smoothedVol[i] > upperBand[i] && smoothedVol[i-1] <= upperBand[i-1]) {
    extremeVolatility[i] = true;
  }
  
  // Low volatility
  if (smoothedVol[i] < lowerBand[i] && smoothedVol[i-1] >= lowerBand[i-1]) {
    lowVolatility[i] = true;
  }
  
  // Regime changes
  if (regimeType[i] === 'trending' && regimeType[i-1] !== 'trending' && 
      regimeConfidenceScore[i] > regimeConfidence) {
    regimeTrending[i] = true;
  }
  
  if (regimeType[i] === 'mean_reverting' && regimeType[i-1] !== 'mean_reverting' && 
      regimeConfidenceScore[i] > regimeConfidence) {
    regimeMeanReverting[i] = true;
  }
  
  if (regimeType[i] === 'choppy' && regimeType[i-1] !== 'choppy') {
    regimeChoppy[i] = true;
  }
  
  // High confidence regime
  if (regimeConfidenceScore[i] > 75 && regimeConfidenceScore[i-1] <= 75) {
    highConfidenceRegime[i] = true;
  }
  
  // VCP detection
  if (vcpActive[i] && !vcpActive[i-1] && vcpQuality[i] > 60) {
    vcpDetected[i] = true;
  }
  
  // VCP breakout (volatility expansion after contraction)
  if (vcpActive[i-1] && !vcpActive[i] && volState[i] === 'expanding') {
    vcpBreakout[i] = true;
  }
  
  // ============================================================================
  // NEW: RISK-BASED SIGNALS (Position Sizing Framework)
  // ============================================================================
  
  const currentRisk = riskLevel[i];
  const prevRisk = riskLevel[i-1];
  const currentZ = regimeZScore[i];
  const prevZ = regimeZScore[i-1];
  
  // Entering elevated risk zone
  if (currentRisk === 'ELEVATED' && prevRisk === 'NORMAL') {
    elevatedRiskEntered[i] = true;
  }
  
  // Entering high risk zone
  if (currentRisk === 'HIGH' && (prevRisk === 'NORMAL' || prevRisk === 'ELEVATED')) {
    highRiskEntered[i] = true;
  }
  
  // Entering extreme risk zone (possible capitulation setup)
  if (currentRisk === 'EXTREME' && prevRisk !== 'EXTREME') {
    extremeRiskEntered[i] = true;
    
    // Check if mean reverting regime + thin structure = capitulation candidate
    if (regimeType[i] === 'mean_reverting' && regimeConfidenceScore[i] > 60) {
      possibleCapitulation[i] = true;
    }
  }
  
  // Risk normalizing (hysteresis applied)
  const exitThreshold = elevatedRiskZScore - zScoreHysteresis;
  if (Math.abs(currentZ) < exitThreshold && Math.abs(prevZ) >= exitThreshold) {
    // Confirm we were actually in elevated risk recently
    let wasElevated = false;
    for (let j = 1; j <= 5; j++) {
      if (i - j >= 0 && Math.abs(regimeZScore[i-j]) >= elevatedRiskZScore) {
        wasElevated = true;
        break;
      }
    }
    if (wasElevated) {
      riskNormalized[i] = true;
    }
  }
  
  // Extreme low volatility (premium compression)
  if (currentZ < -extremeRiskZScore && prevZ >= -extremeRiskZScore) {
    premiumCompressionZone[i] = true;
  }
  
  // Volatility awakening from extreme low
  if (currentZ > -(extremeRiskZScore - zScoreHysteresis) && 
      prevZ <= -(extremeRiskZScore - zScoreHysteresis)) {
    // Confirm we were actually in extreme low state
    let wasExtremeLow = false;
    for (let j = 1; j <= 5; j++) {
      if (i - j >= 0 && regimeZScore[i-j] < -extremeRiskZScore) {
        wasExtremeLow = true;
        break;
      }
    }
    if (wasExtremeLow) {
      volAwakening[i] = true;
    }
  }
}

// ============================================================================
// REGISTER SIGNALS
// ============================================================================

// Volatility State Signals
register_signal(volExpansion, '📈 Volatility EXPANDING');
register_signal(volContraction, '📉 Volatility CONTRACTING');
register_signal(extremeVolatility, '⚠️ EXTREME Volatility');
register_signal(lowVolatility, '😴 LOW Volatility Zone');

// Regime Signals
register_signal(regimeTrending, '🎯 TRENDING Regime Detected');
register_signal(regimeMeanReverting, '🔄 MEAN REVERTING Regime');
register_signal(regimeChoppy, '⚠️ CHOPPY Market Warning');
register_signal(highConfidenceRegime, '✅ High Confidence Regime');

// VCP Signals
register_signal(vcpDetected, '🎪 VCP Pattern Detected');
register_signal(vcpBreakout, '🚀 VCP BREAKOUT');

// NEW: Risk-Based Position Sizing Signals
register_signal(elevatedRiskEntered, `⚡ ELEVATED RISK - Size Down to ${elevatedRiskSize}%`);
register_signal(highRiskEntered, `⚠️ HIGH RISK - Size Down to ${highRiskSize}%`);
register_signal(extremeRiskEntered, `🔥 EXTREME RISK - Size Down to ${extremeRiskSize}%`);
register_signal(possibleCapitulation, '💥 POSSIBLE CAPITULATION - High Risk/High Reward Setup');
register_signal(riskNormalized, '✅ Risk NORMALIZING - Resume Standard Sizing');
register_signal(premiumCompressionZone, '💤 PREMIUM COMPRESSION - Optimal Selling Environment');
register_signal(volAwakening, '⚡ Vol AWAKENING - Directional Move Likely');

// ============================================================================
// DASHBOARD
// ============================================================================

const lastIdx = close.length - 1;

const currentVol = smoothedVol[lastIdx];
const currentMA = volMA[lastIdx];
const currentRegime = regimeType[lastIdx];
const currentConfidence = regimeConfidenceScore[lastIdx];
const currentState = volState[lastIdx];
const currentVR = varianceRatio[lastIdx];
const currentVCP = vcpActive[lastIdx];
const currentVCPQuality = vcpQuality[lastIdx];
const currentZScore = regimeZScore[lastIdx];
const currentRiskLevel = riskLevel[lastIdx];
const currentPositionSize = positionSizePercent[lastIdx];
const currentRiskColor = riskColor[lastIdx];

// Volatility level classification
let volLevel = 'NORMAL';
let volColor = COLORS.NORMAL_VOL;

const volRatio = currentMA > 0 ? currentVol / currentMA : 1;

if (currentVol > upperBand[lastIdx]) {
  volLevel = 'EXTREME';
  volColor = COLORS.EXTREME_VOL;
} else if (volRatio > 1.3) {
  volLevel = 'HIGH';
  volColor = COLORS.HIGH_VOL;
} else if (currentVol < lowerBand[lastIdx]) {
  volLevel = 'LOW';
  volColor = COLORS.LOW_VOL;
}

// Regime color
let regimeColor = COLORS.TRANSITIONAL;
if (currentRegime === 'trending') regimeColor = COLORS.TRENDING;
else if (currentRegime === 'mean_reverting') regimeColor = COLORS.MEAN_REVERTING;
else if (currentRegime === 'choppy') regimeColor = COLORS.CHOPPY;

// State emoji
let stateEmoji = '◆';
if (currentState === 'expanding') stateEmoji = '📈';
else if (currentState === 'contracting') stateEmoji = '📉';

// Risk emoji
let riskEmoji = '✅';
if (currentRiskLevel === 'EXTREME') riskEmoji = '🔥';
else if (currentRiskLevel === 'HIGH') riskEmoji = '⚠️';
else if (currentRiskLevel === 'ELEVATED') riskEmoji = '⚡';
else if (currentRiskLevel === 'LOW VOL') riskEmoji = '💤';

// Trading recommendation - now risk-aware
let recommendation = 'NEUTRAL';
let recColor = COLORS.TEXT;

if (currentRegime === 'choppy') {
  recommendation = 'AVOID';
  recColor = COLORS.CHOPPY;
} else if (currentVCP) {
  recommendation = 'VCP - STANDBY';
  recColor = COLORS.VCP_ACTIVE;
} else if (currentRegime === 'trending' && currentConfidence > 70) {
  if (currentRiskLevel === 'EXTREME' || currentRiskLevel === 'HIGH') {
    recommendation = `DIRECTIONAL - ${currentPositionSize}% SIZE`;
    recColor = COLORS.TRENDING;
  } else {
    recommendation = 'DIRECTIONAL';
    recColor = COLORS.TRENDING;
  }
} else if (currentRegime === 'mean_reverting' && currentConfidence > 70) {
  if (currentRiskLevel === 'EXTREME') {
    recommendation = `MEAN REV - ${currentPositionSize}% SIZE`;
    recColor = COLORS.RISK_CAPITULATION;
  } else if (currentRiskLevel === 'HIGH') {
    recommendation = `MEAN REV - ${currentPositionSize}% SIZE`;
    recColor = COLORS.MEAN_REVERTING;
  } else if (currentRiskLevel === 'ELEVATED') {
    recommendation = `MEAN REV - ${currentPositionSize}% SIZE`;
    recColor = COLORS.MEAN_REVERTING;
  } else if (volLevel === 'LOW' || currentRiskLevel === 'LOW VOL') {
    recommendation = 'SELL PREMIUM';
    recColor = COLORS.LOW_VOL;
  } else {
    recommendation = 'MEAN REV';
    recColor = COLORS.MEAN_REVERTING;
  }
}

const dashboardRows = [
  {
    cells: [{
      text: '📊 VOLATILITY REGIME',
      color: COLORS.COMPOSITE,
      textAlign: 'center',
      fontWeight: 'bold',
      fontSize: 12
    }]
  },
  {
    cells: [{
      text: `Vol: ${currentVol.toFixed(1)}% (${volLevel})`,
      color: volColor,
      textAlign: 'center',
      fontSize: 10
    }]
  },
  {
    cells: [{
      text: `${stateEmoji} ${currentState.toUpperCase()}`,
      color: COLORS.TEXT,
      textAlign: 'center',
      fontSize: 10
    }]
  },
  {
    cells: [{
      text: `${riskEmoji} Risk: ${currentRiskLevel}`,
      color: currentRiskColor,
      textAlign: 'center',
      fontSize: 10,
      fontWeight: 'bold'
    }]
  },
  {
    cells: [{
      text: `Z: ${currentZScore.toFixed(2)}σ`,
      color: currentRiskColor,
      textAlign: 'center',
      fontSize: 9
    }]
  },
  {
    cells: [{
      text: `Position Size: ${currentPositionSize}%`,
      color: currentPositionSize < 50 ? COLORS.RISK_EXTREME : COLORS.RISK_NORMAL,
      textAlign: 'center',
      fontSize: 10,
      fontWeight: currentPositionSize < 50 ? 'bold' : 'normal'
    }]
  },
  {
    cells: [{
      text: `Regime: ${currentRegime.toUpperCase()}`,
      color: regimeColor,
      textAlign: 'center',
      fontSize: 9
    }]
  },
  {
    cells: [{
      text: `Confidence: ${currentConfidence.toFixed(0)}%`,
      color: currentConfidence > 70 ? COLORS.LOW_VOL : COLORS.TEXT,
      textAlign: 'center',
      fontSize: 9
    }]
  },
  {
    cells: [{
      text: `VR: ${currentVR.toFixed(2)}`,
      color: COLORS.TEXT,
      textAlign: 'center',
      fontSize: 9
    }]
  }
];

// Add VCP info if active
if (currentVCP) {
  dashboardRows.push({
    cells: [{
      text: `🎪 VCP: ${currentVCPQuality.toFixed(0)}% Quality`,
      color: COLORS.VCP_ACTIVE,
      textAlign: 'center',
      fontSize: 9,
      fontWeight: 'bold'
    }]
  });
}

// Add capitulation warning if extreme risk + mean reverting
if (currentRiskLevel === 'EXTREME' && currentRegime === 'mean_reverting' && currentConfidence > 60) {
  dashboardRows.push({
    cells: [{
      text: '💥 CAPITULATION?',
      color: COLORS.RISK_CAPITULATION,
      textAlign: 'center',
      fontSize: 9,
      fontWeight: 'bold'
    }]
  });
}

// Add trading recommendation
dashboardRows.push({
  cells: [{
    text: `→ ${recommendation}`,
    color: recColor,
    textAlign: 'center',
    fontSize: 10,
    fontWeight: 'bold'
  }]
});

paint_overlay('VRC_Panel',
  {position: 'center_right'},
  {
    background: COLORS.PANEL_BG,
    border: `2px solid ${currentRiskColor}`,
    borderRadius: 4,
    rows: dashboardRows
  }
);</code>