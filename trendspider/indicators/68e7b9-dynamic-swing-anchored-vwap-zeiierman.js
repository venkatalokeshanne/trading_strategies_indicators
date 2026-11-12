<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Dynamic Swing Anchored VWAP (Zeiierman)', { 
    mainColorInheritFrom: 'text',
    // Short name for display in compact areas
    shortName: 'Dynamic Swing Anchored VWAP (Zeiierman)'
});

// Inputs
const prd = input.number('Swing Period', 30, { min: 2, max: 500 });
const baseAPT = input.number('Adaptive Price Tracking', 20, { min: 1, max: 300 });
const useAdapt = input.boolean('Adapt APT by ATR ratio', false);
const volBias = input.number('Volatility Bias', 10.0, { min: 0.1, max: 100 });
const highS = input.color('Swing High Color', 'lime');
const lowS = input.color('Swing Low Color', 'red');
const upColor = input.color('VWAP Up Color', 'lime');
const downColor = input.color('VWAP Down Color', 'red');

// Find pivot highs and lows
const pivotHigh = pivot_high(high, prd, prd);
const pivotLow = pivot_low(low, prd, prd);

// Get indexes of pivot points
const pivotHighIndexes = indexed_points_of(pivotHigh);
const pivotLowIndexes = indexed_points_of(pivotLow);

// Combine and sort all pivot points by index
const allPivots = [
    ...pivotHighIndexes.map(p => ({ ...p, type: 'high' })),
    ...pivotLowIndexes.map(p => ({ ...p, type: 'low' }))
];
allPivots.sort((a, b) => a.candleIndex - b.candleIndex);

// Filter pivots to ensure strict alternation, keeping the most extreme if consecutive same type
const filteredPivots = [];
let lastPivot = null;

for (const pivot of allPivots) {
    if (filteredPivots.length === 0) {
        filteredPivots.push(pivot);
        lastPivot = pivot;
    } else {
        if (pivot.type !== lastPivot.type) {
            filteredPivots.push(pivot);
            lastPivot = pivot;
        } else {
            // Same type: update to the more extreme pivot
            if (pivot.type === 'high') {
                if (pivot.value > lastPivot.value) {
                    filteredPivots[filteredPivots.length - 1] = pivot;
                    lastPivot = pivot;
                }
            } else {
                if (pivot.value < lastPivot.value) {
                    filteredPivots[filteredPivots.length - 1] = pivot;
                    lastPivot = pivot;
                }
            }
        }
    }
}

// ATR calculation for adaptation
const atrLen = 50;
const myAtr = atr(high, low, close, atrLen);
const atrAvg = ema(myAtr, atrLen);

// Calculate adaptive APT
const aptSeries = for_every(myAtr, atrAvg, (_atr, _avg) => {
    const ratio = _avg > 0 ? _atr / _avg : 1.0;
    const aptRaw = useAdapt ? baseAPT / Math.pow(ratio, volBias) : baseAPT;
    const aptClamped = Math.max(5.0, Math.min(300.0, aptRaw));
    return Math.round(aptClamped);
});

// Calculate VWAP lines between pivots
const vwapUp = series_of(null);
const vwapDown = series_of(null);
const swingHighLabels = series_of(null);
const swingLowLabels = series_of(null);

let lastHighPrice = null;
let lastLowPrice = null;

for (let i = 0; i < filteredPivots.length; i++) {
    const pivot = filteredPivots[i];
    const startIdx = pivot.candleIndex;
    
    // VWAP continues until the next pivot appears (no cross detection)
    const endIdx = i < filteredPivots.length - 1 ? filteredPivots[i + 1].candleIndex : close.length - 1;
    
    const isHigh = pivot.type === 'high';
    const direction = isHigh ? -1 : 1;
    
    // Determine swing label
    let swingLabel = '';
    if (isHigh) {
        if (lastHighPrice !== null) {
            swingLabel = pivot.value > lastHighPrice ? 'HH' : 'LH';
        }
        lastHighPrice = pivot.value;
    } else {
        if (lastLowPrice !== null) {
            swingLabel = pivot.value > lastLowPrice ? 'HL' : 'LL';
        }
        lastLowPrice = pivot.value;
    }
    
    // Initialize VWAP calculation starting from high or low
    const anchorPrice = isHigh ? high[startIdx] : low[startIdx];
    let myP = anchorPrice * volume[startIdx];
    let myVol = volume[startIdx];
    
    // Calculate VWAP for each bar in the range until the next pivot
    for (let j = startIdx; j <= endIdx && j < close.length; j++) {
        const apt = aptSeries[j];
        const alpha = 1.0 - Math.exp(-Math.log(2.0) / Math.max(1.0, apt));
        
        const pxv = hlc3[j] * volume[j];
        const v = volume[j];
        
        myP = (1.0 - alpha) * myP + alpha * pxv;
        myVol = (1.0 - alpha) * myVol + alpha * v;
        
        const vwapValue = myVol > 0 ? myP / myVol : null;
        
        if (direction > 0) {
            vwapUp[j] = vwapValue;
        } else {
            vwapDown[j] = vwapValue;
        }
        
        // Place labels at the pivot points with proper positioning
        if (j === startIdx && swingLabel) {
            if (isHigh) {
                swingHighLabels[j] = swingLabel;
            } else {
                swingLowLabels[j] = swingLabel;
            }
        }
    }
}

// Paint VWAP lines independently
paint(vwapUp, { color: upColor, style: 'line', name: 'Dynamic VWAP Up'});
paint(vwapDown, { color: downColor, style: 'line', name: 'Dynamic VWAP Down'});

// Generate colors for high labels: HH gets red, LH gets orange
const highLabelColors = for_every(swingHighLabels, (_label) => {
    if (!_label) return null;
    return _label === 'HH' ? 'red' : 'orange';
});

// Paint high labels with dynamic colors
paint(swingHighLabels, { 
    style: 'labels_above', 
    color: highLabelColors, 
    name: 'Swing High Labels'
});

// Generate colors for low labels: LL gets green, HL gets lime
const lowLabelColors = for_every(swingLowLabels, (_label) => {
    if (!_label) return null;
    return _label === 'LL' ? 'green' : 'lime';
});

// Paint low labels with dynamic colors
paint(swingLowLabels, { 
    style: 'labels_below', 
    color: lowLabelColors, 
    name: 'Swing Low Labels'
});
</code>