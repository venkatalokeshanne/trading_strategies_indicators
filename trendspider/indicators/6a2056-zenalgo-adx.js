<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('ZenAlgo - ADX', 'lower', {
    shortName: 'ZenAlgo - ADX',
    warmup: 500,
    mainColorInheritFrom: 'ADX'
});

const zenColorBullish = '#3FC0DC';
const zenColorBearish = '#7D0757';
const zenColorNeutral = '#25073B';
const zenColorBullishSoft = '#84DFF1';
const zenColorBearishSoft = '#B84794';
const zenColorSignal = '#72074f';

const len = input.number('Length', 7, { min: 1 });
const threshold = input.number('Threshold', 25, { min: 1 });
const adxSignalLength = input.number('ADX Signal Len', 3, { min: 1 });
const adxSignalType = input.select('ADX Signal MA', 'SMA', ['SMA', 'EMA']);
const enableDivergences = input.boolean('Enable Divergences', true);
const showLabels = input.boolean('Show Div Labels', true);
const plotOffset = input.number('Div Label Offset', 0.5, { min: 0 });
const showTable = input.boolean('Show Table', true);
const tableSize = input.select('Table Size', 'Small', ['Small', 'Normal', 'Large']);
const tablePosition = input.select('Table Position', 'Top-Right', ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right']);

function emptySeries(value = null) {
    return series_of(value);
}

function nvl(value, fallback = 0) {
    return value == null || Number.isNaN(value) ? fallback : value;
}

function movingAverage(source, length, type) {
    return type === 'EMA' ? ema(source, length) : sma(source, length);
}

function crossover(a, b, index) {
    return index > 0 && a[index] != null && b[index] != null && a[index - 1] != null && b[index - 1] != null && a[index] > b[index] && a[index - 1] <= b[index - 1];
}

function crossunder(a, b, index) {
    return index > 0 && a[index] != null && b[index] != null && a[index - 1] != null && b[index - 1] != null && a[index] < b[index] && a[index - 1] >= b[index - 1];
}

function crossoverValue(source, level, index) {
    return index > 0 && source[index] != null && source[index - 1] != null && source[index] > level && source[index - 1] <= level;
}

function crossunderValue(source, level, index) {
    return index > 0 && source[index] != null && source[index - 1] != null && source[index] < level && source[index - 1] >= level;
}

function constantWhen(condition, value) {
    return condition.map(active => active ? value : null);
}

function offsetMarker(condition, values, barsBack) {
    const result = emptySeries();
    for (let i = 0; i < close.length; i++) {
        if (!condition[i]) continue;
        const targetIndex = i - barsBack;
        if (targetIndex >= 0) result[targetIndex] = values[i];
    }
    return result;
}

function offsetSeries(values, barsBack) {
    const result = emptySeries();
    for (let i = 0; i < close.length; i++) {
        if (values[i] == null) continue;
        const targetIndex = i - barsBack;
        if (targetIndex >= 0) result[targetIndex] = values[i];
    }
    return result;
}

function valueWhenLatestSeries(condition, values) {
    const result = emptySeries();
    let latest = null;
    for (let i = 0; i < close.length; i++) {
        if (condition[i]) latest = values[i];
        result[i] = latest;
    }
    return result;
}

function minMaxOfSeries(seriesList) {
    let minValue = Infinity;
    let maxValue = -Infinity;
    for (const source of seriesList) {
        for (let i = 0; i < source.length; i++) {
            const value = source[i];
            if (value == null || Number.isNaN(value)) continue;
            minValue = Math.min(minValue, value);
            maxValue = Math.max(maxValue, value);
        }
    }
    if (minValue === Infinity || maxValue === -Infinity) return { minValue: 0, maxValue: 100 };
    return { minValue, maxValue };
}

function addLineSegment(target, startIndex, startValue, endIndex, endValue) {
    if (startIndex == null || endIndex == null || startValue == null || endValue == null || endIndex <= startIndex) return;
    const length = endIndex - startIndex;
    for (let i = startIndex; i <= endIndex; i++) {
        const progress = (i - startIndex) / length;
        target[i] = startValue + (endValue - startValue) * progress;
    }
}

function colorWithAlpha(hex, alpha) {
    const clean = hex.replace('#', '');
    const r = parseInt(clean.slice(0, 2), 16);
    const g = parseInt(clean.slice(2, 4), 16);
    const b = parseInt(clean.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

function adxBullColor(value) {
    if (value <= 20) return colorWithAlpha(zenColorBullish, 0.2);
    if (value <= 40) return colorWithAlpha(zenColorBullish, 0.4);
    if (value <= 60) return colorWithAlpha(zenColorBullish, 0.6);
    if (value <= 80) return colorWithAlpha(zenColorBullish, 0.8);
    return zenColorBullish;
}

function adxBearColor(value) {
    if (value <= 20) return colorWithAlpha(zenColorBearish, 0.2);
    if (value <= 40) return colorWithAlpha(zenColorBearish, 0.4);
    if (value <= 60) return colorWithAlpha(zenColorBearish, 0.6);
    if (value <= 80) return colorWithAlpha(zenColorBearish, 0.8);
    return zenColorBearish;
}

function diBullColor(value) {
    if (value <= 20) return colorWithAlpha(zenColorBullish, 0.2);
    if (value <= 30) return colorWithAlpha(zenColorBullish, 0.4);
    if (value <= 40) return colorWithAlpha(zenColorBullish, 0.6);
    if (value <= 50) return colorWithAlpha(zenColorBullish, 0.8);
    return zenColorBullish;
}

function diBearColor(value) {
    if (value <= 20) return colorWithAlpha(zenColorBearish, 0.2);
    if (value <= 30) return colorWithAlpha(zenColorBearish, 0.4);
    if (value <= 40) return colorWithAlpha(zenColorBearish, 0.6);
    if (value <= 50) return colorWithAlpha(zenColorBearish, 0.8);
    return zenColorBearish;
}

function topFractal(source, index) {
    return index >= 4 && source[index - 4] < source[index - 2] && source[index - 3] < source[index - 2] && source[index - 2] > source[index - 1] && source[index - 2] > source[index];
}

function bottomFractal(source, index) {
    return index >= 4 && source[index - 4] > source[index - 2] && source[index - 3] > source[index - 2] && source[index - 2] < source[index - 1] && source[index - 2] < source[index];
}

function strengthText(value) {
    if (value <= 20) return 'Weak';
    if (value <= 40) return 'Moderate';
    if (value <= 60) return 'Strong';
    if (value <= 80) return 'Very Strong';
    return 'Extreme';
}

function diStrengthText(value) {
    const distance = Math.abs(value - threshold);
    if (distance <= 5) return 'Weak';
    if (distance <= 15) return 'Moderate';
    return 'Strong';
}

function trendText(series, index) {
    if (index <= 0 || series[index] == null || series[index - 1] == null) return 'Neutral';
    if (series[index] > series[index - 1]) return 'Rising';
    if (series[index] < series[index - 1]) return 'Falling';
    return 'Neutral';
}

function powerDynamicsText(index) {
    const adxNow = adxValue[index];
    if (index <= 0 || adxNow == null || diPlus[index] == null || diMinus[index] == null || diValue[index] == null) return 'Neutral';
    const adxRising = adxNow > adxValue[index - 1];
    const adxFalling = adxNow < adxValue[index - 1];
    const plusRising = diPlus[index] > diPlus[index - 1];
    const minusRising = diMinus[index] > diMinus[index - 1];
    const power = strengthText(adxNow);
    if (adxFalling && minusRising && diValue[index] <= threshold) return `${power} Bears are losing power`;
    if (adxRising && minusRising && diValue[index] <= threshold) return `${power} Bears are gaining power`;
    if (adxFalling && plusRising && diValue[index] > threshold) return `${power} Bulls are losing power`;
    if (adxRising && plusRising && diValue[index] > threshold) return `${power} Bulls are gaining power`;
    return 'Neutral';
}

const trueRange = emptySeries();
const directionalMovementPlus = emptySeries();
const directionalMovementMinus = emptySeries();
for (let i = 0; i < close.length; i++) {
    const prevClose = i > 0 ? close[i - 1] : 0;
    const prevHigh = i > 0 ? high[i - 1] : 0;
    const prevLow = i > 0 ? low[i - 1] : 0;
    trueRange[i] = Math.max(high[i] - low[i], Math.abs(high[i] - prevClose), Math.abs(low[i] - prevClose));
    directionalMovementPlus[i] = high[i] - prevHigh > prevLow - low[i] ? Math.max(high[i] - prevHigh, 0) : 0;
    directionalMovementMinus[i] = prevLow - low[i] > high[i] - prevHigh ? Math.max(prevLow - low[i], 0) : 0;
}

const smoothedTrueRange = emptySeries();
const smoothedDirectionalMovementPlus = emptySeries();
const smoothedDirectionalMovementMinus = emptySeries();
for (let i = 0; i < close.length; i++) {
    smoothedTrueRange[i] = nvl(smoothedTrueRange[i - 1]) - (nvl(smoothedTrueRange[i - 1]) / len) + trueRange[i];
    smoothedDirectionalMovementPlus[i] = nvl(smoothedDirectionalMovementPlus[i - 1]) - (nvl(smoothedDirectionalMovementPlus[i - 1]) / len) + directionalMovementPlus[i];
    smoothedDirectionalMovementMinus[i] = nvl(smoothedDirectionalMovementMinus[i - 1]) - (nvl(smoothedDirectionalMovementMinus[i - 1]) / len) + directionalMovementMinus[i];
}

const diPlus = smoothedDirectionalMovementPlus.map((value, i) => smoothedTrueRange[i] !== 0 ? value / smoothedTrueRange[i] * 100 : null);
const diMinus = smoothedDirectionalMovementMinus.map((value, i) => smoothedTrueRange[i] !== 0 ? value / smoothedTrueRange[i] * 100 : null);
const dx = diPlus.map((value, i) => value != null && diMinus[i] != null && value + diMinus[i] !== 0 ? Math.abs(value - diMinus[i]) / (value + diMinus[i]) * 100 : null);
const adxValue = sma(dx, len);
const diValue = diPlus.map((value, i) => value != null && diMinus[i] != null ? 25 + (value - diMinus[i]) : null);
const adxSignalMA = movingAverage(adxValue, adxSignalLength, adxSignalType);

const adxBullishCross = adxValue.map((value, i) => crossover(adxValue, adxSignalMA, i));
const adxBearishCross = adxValue.map((value, i) => crossunder(adxValue, adxSignalMA, i));
const bullishDiCrossAbove = diValue.map((value, i) => crossoverValue(diValue, 25, i) && value > 25);
const bearishDiCrossBelow = diValue.map((value, i) => crossunderValue(diValue, 25, i) && value < 25);
const bullishSignal = diPlus.map((value, i) => crossover(diPlus, diMinus, i) && value > diMinus[i] && adxValue[i] > threshold && value > diPlus[i - 1] && adxValue[i] > adxValue[i - 1]);
const bearishSignal = diMinus.map((value, i) => crossover(diMinus, diPlus, i) && value > diPlus[i] && adxValue[i] > threshold && value > diMinus[i - 1] && adxValue[i] > adxValue[i - 1]);

const adxLineColor = adxValue.map((value, i) => diValue[i] >= 25 ? adxBullColor(value || 0) : adxBearColor(value || 0));
const diLineColor = adxValue.map((value, i) => diValue[i] > threshold ? diBullColor(value || 0) : diBearColor(value || 0));
const diHistogramRange = diValue.map(value => value == null ? null : {
    high: Math.max(value, threshold),
    low: Math.min(value, threshold),
});
const indicatorRange = minMaxOfSeries([diValue, adxValue, adxSignalMA]);
const markerPadding = Math.max(2, (indicatorRange.maxValue - indicatorRange.minValue) * 0.04);
const bottomMarker = indicatorRange.minValue - markerPadding;
const topMarker = indicatorRange.maxValue + markerPadding;

paint(diHistogramRange, { name: 'DI Histogram', style: 'columnrange', color: diLineColor, thickness: 8 });
paint(diValue, { name: 'DI Line', style: 'line', color: diLineColor, thickness: 2 });
const adxPaint = paint(adxValue, { name: 'ADX', style: 'line', color: adxLineColor, thickness: 3 });
paint(adxSignalMA, { name: 'ADX Signal MA', style: 'line', color: zenColorSignal, thickness: 2 });

paint(horizontal_line(threshold), { name: 'Threshold', style: 'line', color: 'rgba(255,255,255,0.35)', thickness: 1 });
paint(horizontal_line(70), { name: '70', style: 'line', color: 'rgba(255,255,255,0.16)', thickness: 1 });
paint(horizontal_line(80), { name: '80', style: 'line', color: 'rgba(255,255,255,0.16)', thickness: 1 });
paint(horizontal_line(90), { name: '90', style: 'line', color: 'rgba(255,255,255,0.16)', thickness: 1 });
paint(horizontal_line(100), { name: '100', style: 'line', color: 'rgba(255,255,255,0.16)', thickness: 1 });

const fill70 = paint(horizontal_line(70), { name: 'Fill 70 Base', hidden: true, style: 'line', color: '#3A0D32' });
const fill80 = paint(horizontal_line(80), { name: 'Fill 80 Base', hidden: true, style: 'line', color: '#5A144C' });
const fill90 = paint(horizontal_line(90), { name: 'Fill 90 Base', hidden: true, style: 'line', color: '#7D1B69' });
const fill100 = paint(horizontal_line(100), { name: 'Fill 100 Base', hidden: true, style: 'line', color: '#7D1B69' });
fill(fill70, fill80, '#3A0D32');
fill(fill80, fill90, '#5A144C');
fill(fill90, fill100, '#7D1B69');

paint(offsetMarker(adxBullishCross, adxValue, 1), { name: 'ADX Bullish Cross', style: 'dotted', color: adxValue.map((value, i) => diValue[i] <= 25 ? adxBearColor(value || 0) : adxBullColor(value || 0)), thickness: 4 });
paint(offsetMarker(adxBearishCross, adxValue, 1), { name: 'ADX Bearish Cross', style: 'dotted', color: adxValue.map((value, i) => diValue[i] >= 25 ? adxBearColor(value || 0) : adxBullColor(value || 0)), thickness: 4 });
paint(constantWhen(bullishDiCrossAbove, bottomMarker), { name: 'DI Cross Above 25', style: 'dotted', color: adxValue.map(value => adxBullColor(value || 0)), thickness: 6 });
paint(constantWhen(bearishDiCrossBelow, topMarker), { name: 'DI Cross Below 25', style: 'dotted', color: adxValue.map(value => adxBearColor(value || 0)), thickness: 6 });

const isFractalTopDI = diValue.map((value, i) => topFractal(diValue, i));
const isFractalBotDI = diValue.map((value, i) => bottomFractal(diValue, i));
const regularBearishDivDI = emptySeries(false);
const hiddenBearishDivDI = emptySeries(false);
const regularBullishDivDI = emptySeries(false);
const hiddenBullishDivDI = emptySeries(false);
const regularBearLine = emptySeries();
const hiddenBearLine = emptySeries();
const regularBullLine = emptySeries();
const hiddenBullLine = emptySeries();
const regularBearLabelAnchor = emptySeries();
const hiddenBearLabelAnchor = emptySeries();
const regularBullLabelAnchor = emptySeries();
const hiddenBullLabelAnchor = emptySeries();
let previousTopIndex = null;
let previousTopDI = null;
let previousTopHigh = null;
let previousBottomIndex = null;
let previousBottomDI = null;
let previousBottomLow = null;
for (let i = 4; i < close.length; i++) {
    if (isFractalTopDI[i]) {
        const pivotIndex = i - 2;
        const pivotDI = diValue[pivotIndex];
        const pivotHigh = high[pivotIndex];
        const regularBearish = enableDivergences && previousTopDI != null && previousTopHigh != null && pivotHigh > previousTopHigh && pivotDI < previousTopDI;
        const hiddenBearish = enableDivergences && previousTopDI != null && previousTopHigh != null && pivotHigh < previousTopHigh && pivotDI > previousTopDI;
        regularBearishDivDI[pivotIndex] = regularBearish;
        hiddenBearishDivDI[pivotIndex] = hiddenBearish;
        if (regularBearish) {
            addLineSegment(regularBearLine, previousTopIndex, previousTopDI, pivotIndex, pivotDI);
            if (diValue[i - 1] != null) regularBearLabelAnchor[pivotIndex] = diValue[i - 1] + plotOffset;
        }
        if (hiddenBearish) {
            addLineSegment(hiddenBearLine, previousTopIndex, previousTopDI, pivotIndex, pivotDI);
            if (diValue[i - 1] != null) hiddenBearLabelAnchor[pivotIndex] = diValue[i - 1] + plotOffset;
        }
        previousTopIndex = pivotIndex;
        previousTopDI = pivotDI;
        previousTopHigh = pivotHigh;
    }
    if (isFractalBotDI[i]) {
        const pivotIndex = i - 2;
        const pivotDI = diValue[pivotIndex];
        const pivotLow = low[pivotIndex];
        const regularBullish = enableDivergences && previousBottomDI != null && previousBottomLow != null && pivotLow < previousBottomLow && pivotDI > previousBottomDI;
        const hiddenBullish = enableDivergences && previousBottomDI != null && previousBottomLow != null && pivotLow > previousBottomLow && pivotDI < previousBottomDI;
        regularBullishDivDI[pivotIndex] = regularBullish;
        hiddenBullishDivDI[pivotIndex] = hiddenBullish;
        if (regularBullish) {
            addLineSegment(regularBullLine, previousBottomIndex, previousBottomDI, pivotIndex, pivotDI);
            if (diValue[i - 1] != null) regularBullLabelAnchor[pivotIndex] = diValue[i - 1] - plotOffset;
        }
        if (hiddenBullish) {
            addLineSegment(hiddenBullLine, previousBottomIndex, previousBottomDI, pivotIndex, pivotDI);
            if (diValue[i - 1] != null) hiddenBullLabelAnchor[pivotIndex] = diValue[i - 1] - plotOffset;
        }
        previousBottomIndex = pivotIndex;
        previousBottomDI = pivotDI;
        previousBottomLow = pivotLow;
    }
}

const regularBearDivPaint = paint(regularBearLine, { name: 'Regular Bearish Divergences DI', style: 'line', color: zenColorBearish, thickness: 2 });
const hiddenBearDivPaint = paint(hiddenBearLine, { name: 'Hidden Bearish Divergences DI', style: 'line', color: zenColorBearishSoft, thickness: 2 });
const regularBullDivPaint = paint(regularBullLine, { name: 'Regular Bullish Divergences DI', style: 'line', color: zenColorBullish, thickness: 2 });
const hiddenBullDivPaint = paint(hiddenBullLine, { name: 'Hidden Bullish Divergences DI', style: 'line', color: zenColorBullishSoft, thickness: 2 });
const regularBearLabelPaint = paint(regularBearLabelAnchor, { name: 'Regular Bear Div Label Anchor', style: 'dotted', color: 'rgba(0,0,0,0)', thickness: 1, hideInLegend: true });
const hiddenBearLabelPaint = paint(hiddenBearLabelAnchor, { name: 'Hidden Bear Div Label Anchor', style: 'dotted', color: 'rgba(0,0,0,0)', thickness: 1, hideInLegend: true });
const regularBullLabelPaint = paint(regularBullLabelAnchor, { name: 'Regular Bull Div Label Anchor', style: 'dotted', color: 'rgba(0,0,0,0)', thickness: 1, hideInLegend: true });
const hiddenBullLabelPaint = paint(hiddenBullLabelAnchor, { name: 'Hidden Bull Div Label Anchor', style: 'dotted', color: 'rgba(0,0,0,0)', thickness: 1, hideInLegend: true });
for (let i = 0; i < close.length; i++) {
    if (showLabels && regularBearLabelAnchor[i] != null) paint_label_at_line(regularBearLabelPaint, i, 'R', { color: 'white', background_color: zenColorBearish, vertical_align: 'top' });
    if (showLabels && hiddenBearLabelAnchor[i] != null) paint_label_at_line(hiddenBearLabelPaint, i, 'H', { color: 'white', background_color: zenColorBearishSoft, vertical_align: 'top' });
    if (showLabels && regularBullLabelAnchor[i] != null) paint_label_at_line(regularBullLabelPaint, i, 'R', { color: 'black', background_color: zenColorBullish, vertical_align: 'bottom' });
    if (showLabels && hiddenBullLabelAnchor[i] != null) paint_label_at_line(hiddenBullLabelPaint, i, 'H', { color: 'black', background_color: zenColorBullishSoft, vertical_align: 'bottom' });
}

const bullishAdxDiPlus = adxValue.map((value, i) => i > 0 && value > adxValue[i - 1] && diPlus[i] > diPlus[i - 1] && diValue[i] > 25);
const bearishAdxDiMinus = adxValue.map((value, i) => i > 0 && value > adxValue[i - 1] && diMinus[i] > diMinus[i - 1] && diValue[i] < 25);
paint(bullishAdxDiPlus.map((value, i) => value && adxValue[i] <= 20 ? bottomMarker : null), { name: 'Rising Bull DI Weak', style: 'dotted', color: adxLineColor, thickness: 3 });
paint(bullishAdxDiPlus.map((value, i) => value && adxValue[i] > 20 && adxValue[i] <= 40 ? bottomMarker : null), { name: 'Rising Bull DI Moderate', style: 'dotted', color: adxLineColor, thickness: 3 });
paint(bullishAdxDiPlus.map((value, i) => value && adxValue[i] > 40 && adxValue[i] <= 60 ? bottomMarker : null), { name: 'Rising Bull DI Strong', style: 'dotted', color: adxLineColor, thickness: 5 });
paint(bullishAdxDiPlus.map((value, i) => value && adxValue[i] > 60 && adxValue[i] <= 80 ? bottomMarker : null), { name: 'Rising Bull DI Very Strong', style: 'dotted', color: adxLineColor, thickness: 7 });
paint(bullishAdxDiPlus.map((value, i) => value && adxValue[i] > 80 ? bottomMarker : null), { name: 'Rising Bull DI Extreme', style: 'dotted', color: adxLineColor, thickness: 9 });
paint(bearishAdxDiMinus.map((value, i) => value && adxValue[i] <= 20 ? topMarker : null), { name: 'Rising Bear DI Weak', style: 'dotted', color: adxLineColor, thickness: 3 });
paint(bearishAdxDiMinus.map((value, i) => value && adxValue[i] > 20 && adxValue[i] <= 40 ? topMarker : null), { name: 'Rising Bear DI Moderate', style: 'dotted', color: adxLineColor, thickness: 3 });
paint(bearishAdxDiMinus.map((value, i) => value && adxValue[i] > 40 && adxValue[i] <= 60 ? topMarker : null), { name: 'Rising Bear DI Strong', style: 'dotted', color: adxLineColor, thickness: 5 });
paint(bearishAdxDiMinus.map((value, i) => value && adxValue[i] > 60 && adxValue[i] <= 80 ? topMarker : null), { name: 'Rising Bear DI Very Strong', style: 'dotted', color: adxLineColor, thickness: 7 });
paint(bearishAdxDiMinus.map((value, i) => value && adxValue[i] > 80 ? topMarker : null), { name: 'Rising Bear DI Extreme', style: 'dotted', color: adxLineColor, thickness: 9 });

if (showTable) {
    const last = close.length - 1;
    const fontSize = tableSize === 'Small' ? '12px' : tableSize === 'Large' ? '16px' : '14px';
    const position = tablePosition === 'Top-Left' ? 'top_left'
        : tablePosition === 'Bottom-Left' ? 'bottom_left'
        : tablePosition === 'Bottom-Right' ? 'bottom_right'
        : 'top_right';
    const adxCellColor = diValue[last] >= 25 ? adxBullColor(adxValue[last] || 0) : adxBearColor(adxValue[last] || 0);
    const diCellColor = diValue[last] > threshold ? diBullColor(adxValue[last] || 0) : diBearColor(adxValue[last] || 0);
    const legendCell = text => ({
        text,
        color: 'white',
        backgroundColor: 'transparent',
        fontSize,
        textAlign: 'center',
        padding: '2px 6px',
    });
    const valueCell = (text, backgroundColor) => ({
        text,
        color: 'white',
        backgroundColor,
        fontSize,
        textAlign: 'center',
        padding: '2px 6px',
    });
    paint_overlay('ADX DI Table', { position, offset_y: 25, order: 'above_all' }, {
        rows: [
            { cells: [legendCell('ADX'), valueCell((adxValue[last] || 0).toFixed(1), adxCellColor)] },
            { cells: [legendCell('ADX'), valueCell(strengthText(adxValue[last] || 0), adxCellColor)] },
            { cells: [legendCell('ADX'), valueCell(trendText(adxValue, last), adxCellColor)] },
            { cells: [legendCell('DI'), valueCell((diValue[last] || 0).toFixed(1), diCellColor)] },
            { cells: [legendCell('DI'), valueCell(diStrengthText(diValue[last] || 0), diCellColor)] },
            { cells: [legendCell('DI'), valueCell(trendText(diValue, last), diCellColor)] },
            { cells: [legendCell('Dynamics'), valueCell(powerDynamicsText(last), diValue[last] <= threshold ? adxBearColor(adxValue[last] || 0) : diCellColor)] },
        ],
    });
}

register_signal(bullishSignal, 'ADX Bullish DI Cross');
register_signal(bearishSignal, 'ADX Bearish DI Cross');
register_signal(adxBullishCross, 'ADX Bullish Signal Cross');
register_signal(adxBearishCross, 'ADX Bearish Signal Cross');
</code>