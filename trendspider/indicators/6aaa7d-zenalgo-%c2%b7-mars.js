<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('ZenAlgo · Mars', 'lower', { decimals: 2, shortName: 'MARS', mainColorInheritFrom: 'Mars' });

const sourceSettings = input.group('Source');
const preset = sourceSettings.select('Preset', 'Traditional', ['Traditional', 'Fast', 'Custom']);
const customRsiLength = sourceSettings.number('Custom RSI length', 14, { min: 1, max: 200 });
const customMaLength = sourceSettings.number('Custom MA length', 14, { min: 1, max: 200 });
const customSignalLength = sourceSettings.number('Custom signal length', 9, { min: 1, max: 200 });
const rsiLength = preset === 'Custom' ? Math.round(customRsiLength) : preset === 'Fast' ? 7 : 14;
const maLength = preset === 'Custom' ? Math.round(customMaLength) : preset === 'Fast' ? 7 : 14;
const signalLength = preset === 'Custom' ? Math.round(customSignalLength) : preset === 'Fast' ? 3 : 9;

const divergenceSettings = input.group('Divergences');
const pivotLeft = Math.round(divergenceSettings.number('Pivot left', 5, { min: 1, max: 50 }));
const pivotRight = Math.round(divergenceSettings.number('Pivot right', 5, { min: 1, max: 50 }));
const minRangeInput = Math.round(divergenceSettings.number('Minimum pivot range', 5, { min: 1, max: 500 }));
const maxRangeInput = Math.round(divergenceSettings.number('Maximum pivot range', 60, { min: 2, max: 500 }));
const minRange = Math.min(minRangeInput, maxRangeInput - 1);
const maxRange = Math.max(maxRangeInput, minRange + 1);
const divergenceHistory = divergenceSettings.select('Divergence placement', 'Confirmation', ['Confirmation', 'Pivot history']);

const biasSettings = input.group('Bias');
const biasLookback = Math.round(biasSettings.number('Signal bias smoothing', 1, { min: 1, max: 200 }));
const zoneLookback = Math.round(biasSettings.number('Zone lookback', 100, { min: 1, max: 1000 }));
const normalBiasRatio = biasSettings.number('Bias ratio', 1.2, { min: 1, max: 10 });
const fullBiasRatio = Math.max(normalBiasRatio, biasSettings.number('Full bias ratio', 1.8, { min: 1, max: 10 }));

const visualSettings = input.group('Appearance');
const appearance = visualSettings.select('Detail', 'Signature', ['Minimal', 'Signature']);
const bullColor = visualSettings.color('Bullish color', '#3FC0DC');
const bearColor = visualSettings.color('Bearish color', '#A477FF');
const showConfirmationLabels = visualSettings.boolean('Confirmation labels', true);
const showDashboard = visualSettings.boolean('Dashboard', false);
const showTimeframes = visualSettings.boolean('Timeframe matrix', true);
const showSignalLegend = visualSettings.boolean('Signal legend', false);
const dashboardPosition = visualSettings.select('Dashboard position', 'bottom_left', ['top_right', 'bottom_right', 'top_left', 'bottom_left']);
const dashboardSize = visualSettings.select('Dashboard size', 'Compact', ['Compact', 'Comfortable']);
const muted = '#8E9CB3';
const warningColor = '#F5BE70';
const surface = '#101827';
const tinycolor = library('tinycolor2');
const alphaColor = (color, alpha) => tinycolor(color).setAlpha(alpha).toRgbString();
const empty = () => Array(close.length).fill(null);
const finite = value => typeof value === 'number' && Number.isFinite(value);

function averageSeries(values, length, exponential = false) {
    const result = Array(values.length).fill(null);
    let total = 0;
    let previous = null;
    const queue = [];
    const alpha = 2 / (length + 1);
    for (let index = 0; index < values.length; index++) {
        const value = values[index];
        if (!finite(value)) continue;
        if (exponential) {
            previous = previous === null ? value : alpha * value + (1 - alpha) * previous;
            result[index] = previous;
        } else {
            queue.push(value);
            total += value;
            if (queue.length > length) total -= queue.shift();
            if (queue.length === length) result[index] = total / length;
        }
    }
    return result;
}

function wilderRsi(values, length) {
    const result = Array(values.length).fill(null);
    let gain = 0;
    let loss = 0;
    let count = 0;
    let previous = null;
    for (let index = 0; index < values.length; index++) {
        if (!finite(values[index])) continue;
        if (previous === null) { previous = values[index]; continue; }
        const change = values[index] - previous;
        previous = values[index];
        const up = Math.max(change, 0);
        const down = Math.max(-change, 0);
        if (count < length) {
            gain += up;
            loss += down;
            count++;
            if (count < length) continue;
            gain /= length;
            loss /= length;
        } else {
            gain = (gain * (length - 1) + up) / length;
            loss = (loss * (length - 1) + down) / length;
        }
        result[index] = loss === 0 ? 100 : gain === 0 ? 0 : 100 - 100 / (1 + gain / loss);
    }
    return result;
}

function findDivergences(oscillator, lows, highs, left, right, minimum, maximum) {
    const events = [];
    let previousLow = null;
    let previousHigh = null;
    for (let confirmation = left + right; confirmation < oscillator.length; confirmation++) {
        const pivot = confirmation - right;
        const value = oscillator[pivot];
        if (!finite(value)) continue;
        let isLow = true;
        let isHigh = true;
        for (let index = pivot - left; index <= confirmation; index++) {
            if (index === pivot) continue;
            const other = oscillator[index];
            if (!finite(other)) { isLow = false; isHigh = false; break; }
            if (index < pivot ? other < value : other <= value) isLow = false;
            if (index < pivot ? other > value : other >= value) isHigh = false;
        }
        for (const side of ['low', 'high']) {
            if (side === 'low' ? !isLow : !isHigh) continue;
            const previous = side === 'low' ? previousLow : previousHigh;
            const price = side === 'low' ? lows : highs;
            if (previous !== null && finite(price[pivot]) && finite(price[previous])) {
                const barsSincePrevious = pivot - previous - 1;
                if (barsSincePrevious >= minimum && barsSincePrevious <= maximum) {
                    const priceChange = price[pivot] - price[previous];
                    const oscillatorChange = value - oscillator[previous];
                    let type = null;
                    if (side === 'low' && priceChange < 0 && oscillatorChange > 0) type = 'regularBull';
                    if (side === 'low' && priceChange > 0 && oscillatorChange < 0) type = 'hiddenBull';
                    if (side === 'high' && priceChange > 0 && oscillatorChange < 0) type = 'regularBear';
                    if (side === 'high' && priceChange < 0 && oscillatorChange > 0) type = 'hiddenBear';
                    if (type) events.push({ type, pivot, previous, confirmation });
                }
            }
            if (side === 'low') previousLow = pivot;
            else previousHigh = pivot;
        }
    }
    return events;
}

function sessionVwap() {
    const result = empty();
    let session = null;
    let weighted = 0;
    let totalVolume = 0;
    let completeSession = false;
    for (let index = 0; index < close.length; index++) {
        const start = bar_at(time[index], 'D', current.is_ext_hours ? current.ext_session : current.session).sessionStartsAt;
        if (start !== session) {
            completeSession = session !== null || time[index] === start;
            session = start;
            weighted = 0;
            totalVolume = 0;
        }
        if (finite(volume[index]) && volume[index] > 0 && finite(high[index]) && finite(low[index]) && finite(close[index])) {
            weighted += (high[index] + low[index] + close[index]) / 3 * volume[index];
            totalVolume += volume[index];
        }
        if (completeSession && totalVolume > 0) result[index] = weighted / totalVolume;
    }
    return result;
}

const marsRsi = wilderRsi(close, rsiLength);
const mars = averageSeries(marsRsi, maLength);
const signal = averageSeries(mars, signalLength, true);
const bias = averageSeries(mars, biasLookback);
const spread = mars.map((value, index) => finite(value) && finite(signal[index]) ? value - signal[index] : null);
const dailyVwap = sessionVwap();
const directionColors = mars.map((value, index) => finite(value) && finite(signal[index]) ? value >= signal[index] ? bullColor : bearColor : muted);
const histogramColors = spread.map((value, index) => {
    if (!finite(value)) return muted;
    const rising = finite(spread[index - 1]) && value > spread[index - 1];
    return alphaColor(value > 0 ? bullColor : bearColor, rising ? 1 : 0.4);
});
const flags = {};
for (const name of ['crossUp', 'crossDown', 'regularBull', 'hiddenBull', 'regularBear', 'hiddenBear', 'strongBull', 'strongBear', 'warningBull', 'warningBear', 'launchBull', 'launchBear']) {
    flags[name] = Array(close.length).fill(false);
}
for (let index = 1; index < close.length; index++) {
    if (![mars[index], mars[index - 1], signal[index], signal[index - 1]].every(finite)) continue;
    flags.crossUp[index] = mars[index] > signal[index] && mars[index - 1] <= signal[index - 1];
    flags.crossDown[index] = mars[index] < signal[index] && mars[index - 1] >= signal[index - 1];
    const hasVwap = finite(dailyVwap[index]) && finite(volume[index]) && volume[index] > 0;
    flags.launchBull[index] = hasVwap && mars[index] > 50 && mars[index - 1] <= 50 && spread[index] > spread[index - 1] && close[index] > dailyVwap[index];
    flags.launchBear[index] = hasVwap && mars[index] < 50 && mars[index - 1] >= 50 && spread[index] < spread[index - 1] && close[index] < dailyVwap[index];
}
const divergences = findDivergences(mars, low, high, pivotLeft, pivotRight, minRange, maxRange);
for (const event of divergences) flags[event.type][event.confirmation] = true;
for (let index = 0; index < close.length; index++) {
    flags.strongBull[index] = finite(bias[index]) && bias[index] > 50 && flags.hiddenBull[index];
    flags.strongBear[index] = finite(bias[index]) && bias[index] < 50 && flags.hiddenBear[index];
    flags.warningBull[index] = finite(bias[index]) && bias[index] < 50 && flags.regularBull[index];
    flags.warningBear[index] = finite(bias[index]) && bias[index] > 50 && flags.regularBear[index];
}

const decoration = { hideInLegend: true, hideInScriptEditor: true, editorHidden: true };
const signature = appearance === 'Signature';
paint(Array(close.length).fill(100), { name: 'Scale top', color: '#00000000', ...decoration });
paint(Array(close.length).fill(0), { name: 'Scale bottom', color: '#00000000', ...decoration });
const upperLine = paint(Array(close.length).fill(70), { name: 'Upper zone', color: '#A477FF55', thickness: 1, ...decoration });
const lowerLine = paint(Array(close.length).fill(30), { name: 'Lower zone', color: '#3FC0DC55', thickness: 1, ...decoration });
fill(upperLine, lowerLine, '#6E65C9', signature ? 0.055 : 0, 'Mars atmosphere');
paint(Array(close.length).fill(50), { name: 'Equilibrium', color: '#8E9CB344', style: 'dotted', thickness: 1, ...decoration });
paint(spread.map(value => finite(value) ? { high: Math.max(50, 50 + value * (preset === 'Fast' ? 3 : 1)), low: Math.min(50, 50 + value * (preset === 'Fast' ? 3 : 1)) } : null), {
    name: 'Momentum histogram', style: 'columnrange', color: histogramColors, ...decoration
});
paint(signature ? mars : empty(), { name: 'Mars halo', color: directionColors.map(color => alphaColor(color, 0.09)), thickness: 9, ...decoration });
const marsLine = paint(mars, { name: 'Mars', color: directionColors, thickness: 3, lastValueLabelEnabled: true });
const signalLine = paint(signal, { name: 'Signal', color: directionColors, thickness: 1, lastValueLabelEnabled: true });
color_cloud(mars, signal, bullColor, bearColor, 'Bull momentum ribbon', 'Bear momentum ribbon', signature ? 0.16 : 0);

const divergenceBullPoints = empty();
const divergenceBearPoints = empty();
for (const event of divergences) {
    const index = divergenceHistory === 'Pivot history' ? event.pivot : event.confirmation;
    (event.type.endsWith('Bull') ? divergenceBullPoints : divergenceBearPoints)[index] = mars[index];
}
const bullPointsLine = paint(divergenceBullPoints, { name: 'Bullish divergence', color: bullColor, style: 'dotted', thickness: 3, ...decoration });
const bearPointsLine = paint(divergenceBearPoints, { name: 'Bearish divergence', color: bearColor, style: 'dotted', thickness: 3, ...decoration });
for (const event of divergences.slice(-80)) {
    const bullish = event.type.endsWith('Bull');
    const index = divergenceHistory === 'Pivot history' ? event.pivot : event.confirmation;
    paint_label_at_line(bullish ? bullPointsLine : bearPointsLine, index, event.type.startsWith('regular') ? 'R' : 'H', {
        color: bullish ? bullColor : bearColor, background_color: surface, border_color: bullish ? bullColor : bearColor,
        border_width: 1, border_radius: 3, vertical_align: bullish ? 'bottom' : 'top'
    });
}
paint(flags.crossUp.map((active, index) => active ? mars[index] : null), { name: 'Bullish crossover', style: 'dotted', marker: 'circle', color: bullColor, thickness: 3, ...decoration });
paint(flags.crossDown.map((active, index) => active ? mars[index] : null), { name: 'Bearish crossover', style: 'dotted', marker: 'circle', color: bearColor, thickness: 3, ...decoration });
paint(flags.strongBull.map(active => active ? 10 : null), { name: 'Strong bull marker', style: 'dotted', marker: 'diamond', color: bullColor, thickness: 5, ...decoration });
paint(flags.strongBear.map(active => active ? 90 : null), { name: 'Strong bear marker', style: 'dotted', marker: 'diamond', color: bearColor, thickness: 5, ...decoration });
paint(flags.warningBull.map(active => active ? 10 : null), { name: 'Bull warning marker', style: 'dotted', marker: 'triangle', color: warningColor, thickness: 4, ...decoration });
paint(flags.warningBear.map(active => active ? 90 : null), { name: 'Bear warning marker', style: 'dotted', marker: 'triangle-down', color: warningColor, thickness: 4, ...decoration });
paint(flags.launchBull.map(active => active ? 4 : null), { name: 'Bull launch marker', style: 'dotted', marker: 'triangle', color: bullColor, thickness: 4, ...decoration });
paint(flags.launchBear.map(active => active ? 96 : null), { name: 'Bear launch marker', style: 'dotted', marker: 'triangle-down', color: bearColor, thickness: 4, ...decoration });
const bullConfirmationLine = paint(flags.launchBull.map((active, index) => showConfirmationLabels && (active || flags.strongBull[index]) ? 18 : null), {
    name: 'Bull confirmation anchor', style: 'dotted', color: '#00000000', thickness: 1, ignoreWhenScaling: true, ...decoration
});
const bearConfirmationLine = paint(flags.launchBear.map((active, index) => showConfirmationLabels && (active || flags.strongBear[index]) ? 82 : null), {
    name: 'Bear confirmation anchor', style: 'dotted', color: '#00000000', thickness: 1, ignoreWhenScaling: true, ...decoration
});
const confirmationLabels = [];
if (showConfirmationLabels) {
    for (let index = 0; index < close.length; index++) {
        if (flags.launchBull[index] || flags.strongBull[index]) confirmationLabels.push({ index, bullish: true, launch: flags.launchBull[index] });
        if (flags.launchBear[index] || flags.strongBear[index]) confirmationLabels.push({ index, bullish: false, launch: flags.launchBear[index] });
    }
}
for (const event of confirmationLabels.slice(-80)) {
    const color = event.bullish ? bullColor : bearColor;
    paint_label_at_line(event.bullish ? bullConfirmationLine : bearConfirmationLine, event.index, `${event.launch ? 'MARS' : 'H'} ${event.bullish ? '↑' : '↓'}`, {
        color, background_color: surface, border_color: color, border_width: 1, border_radius: 3,
        vertical_align: event.bullish ? 'top' : 'bottom'
    });
}

register_signal(flags.crossUp, 'Mars crossed above Signal');
register_signal(flags.crossDown, 'Mars crossed below Signal');
register_signal(flags.regularBull, 'Regular bullish divergence confirmed');
register_signal(flags.hiddenBull, 'Hidden bullish divergence confirmed');
register_signal(flags.regularBear, 'Regular bearish divergence confirmed');
register_signal(flags.hiddenBear, 'Hidden bearish divergence confirmed');
register_signal(flags.strongBull, 'Strong bull');
register_signal(flags.strongBear, 'Strong bear');
register_signal(flags.warningBull, 'Bullish warning');
register_signal(flags.warningBear, 'Bearish warning');
register_signal(flags.launchBull, 'Bull launch with session VWAP');
register_signal(flags.launchBear, 'Bear launch with session VWAP');

const last = close.length - 1;
const fmt = value => finite(value) ? value.toFixed(1) : '—';
const zoneSample = mars.slice(Math.max(0, close.length - zoneLookback)).filter(finite);
const zones = {
    above70: zoneSample.filter(value => value > 70).length,
    above50: zoneSample.filter(value => value > 50).length,
    below50: zoneSample.filter(value => value < 50).length,
    below30: zoneSample.filter(value => value < 30).length
};
const trendBias = zoneSample.length === 0 ? 'WARMING UP' : zones.above50 > fullBiasRatio * zones.below50 ? 'FULL BULL' : zones.below50 > fullBiasRatio * zones.above50 ? 'FULL BEAR' : zones.above50 > normalBiasRatio * zones.below50 ? 'BULL' : zones.below50 > normalBiasRatio * zones.above50 ? 'BEAR' : 'BALANCED';
const biasColor = trendBias.includes('BULL') ? bullColor : trendBias.includes('BEAR') ? bearColor : muted;
const rising = finite(mars[last]) && finite(mars[last - 1]) ? mars[last] > mars[last - 1] ? 'RISING' : mars[last] < mars[last - 1] ? 'FALLING' : 'FLAT' : 'WARMING UP';
const cell = (text, color = '#E6EDF7', extra = {}) => ({ text, color, padding: '5px 9px', ...extra });
const rows = [];
if (showDashboard) {
    rows.push({ cells: [cell('ZENALGO / MARS', '#E6EDF7', { colspan: 4, fontSize: '12px', fontWeight: '700', letterSpacing: '3px', padding: '12px 10px', borderBottom: '1px solid #FFFFFF14' })] });
    rows.push({ cells: [cell(trendBias, biasColor, { colspan: 2, fontSize: dashboardSize === 'Compact' ? '18px' : '24px', fontWeight: '700' }), cell(rising, muted, { colspan: 2, textAlign: 'right', fontSize: '10px' })] });
    rows.push({ cells: [cell('MARS', muted), cell(fmt(mars[last]), directionColors[last]), cell('SIGNAL', muted), cell(fmt(signal[last]), '#D8E2F0')] });
    const bullShare = zoneSample.length ? Math.round(zones.above50 / zoneSample.length * 100) : 0;
    rows.push({ cells: [cell(zoneSample.length ? `${bullShare}% above 50 · ${zoneSample.length} bars` : 'Waiting for history', muted, { colspan: 4, fontSize: '10px', borderBottom: `3px solid ${biasColor}` })] });
    if (signature) {
        rows.push({ cells: [cell('>70', bearColor), cell(String(zones.above70)), cell('<30', bullColor), cell(String(zones.below30))] });
    }
}

const timeframeSpecs = [['1', '1m'], ['5', '5m'], ['15', '15m'], ['60', '1h'], ['240', '4h'], ['D', '1D']];
const timeframeRows = showDashboard && showTimeframes ? await Promise.all(timeframeSpecs.map(async ([resolution, label]) => {
    try {
        const chartType = ['heikinashi', 'rainfall'].includes(current.chart_type) ? current.chart_type : 'candles';
        const data = String(current.resolution) === resolution ? { close } : await request.history(current.ticker, resolution, { chart_type: chartType, ext_session: current.is_ext_hours });
        if (!data || data.error || !Array.isArray(data.close)) return { label, error: true };
        const values = wilderRsi(data.close, rsiLength);
        const averages = averageSeries(values, rsiLength);
        const index = data.close.length - 1;
        return { label, rsi: values[index], ma: averages[index] };
    } catch (error) {
        return { label, error: true };
    }
})) : [];
if (showDashboard && showTimeframes) {
    rows.push({ cells: [cell('TF · LIVE', muted), cell('RSI', muted), cell('MA', muted), cell('TREND', muted)] });
    for (const item of timeframeRows) {
        const ready = !item.error && finite(item.rsi) && finite(item.ma);
        const trend = ready ? item.rsi > item.ma ? 'RISING' : item.rsi < item.ma ? 'FALLING' : 'FLAT' : 'N/A';
        const color = trend === 'RISING' ? bullColor : trend === 'FALLING' ? bearColor : muted;
        rows.push({ cells: [cell(item.label, '#D8E2F0'), cell(fmt(item.rsi)), cell(fmt(item.ma), muted), cell(trend, color, { fontSize: '10px' })] });
    }
}
if (showDashboard) {
    const vwapStatus = finite(dailyVwap[last]) ? 'VWAP ACTIVE' : 'VWAP N/A';
    rows.push({ cells: [cell(`${preset.toUpperCase()} · ${vwapStatus}`, muted, { colspan: 4, fontSize: '9px', paddingTop: '10px', borderTop: '1px solid #FFFFFF14' })] });
    rows.push({ cells: [cell(divergenceHistory === 'Pivot history' ? `R / H drawn ${pivotRight} bars back after confirmation` : `R reversal · H continuation · confirmed +${pivotRight}`, muted, { colspan: 4, fontSize: '9px' })] });
    if (showSignalLegend) {
        for (const [text, color] of [
            ['R · Regular divergence / potential reversal', muted],
            ['H · Hidden divergence / potential continuation', muted],
            ['MARS ↑ / ↓ · Cross 50 + momentum + VWAP', muted],
            ['H ↑ / ↓ · Hidden divergence aligned with bias', muted],
            ['◆ · Strong continuation condition', muted],
            ['Amber ▲ / ▼ · Divergence opposing bias', warningColor]
        ]) rows.push({ cells: [cell(text, color, { colspan: 4, fontSize: '10px' })] });
    }
}
for (const position of ['top_right', 'bottom_right', 'top_left', 'bottom_left']) {
    const active = showDashboard && dashboardPosition === position;
    paint_overlay(`Mars dashboard ${position}`, { position, parent: 'chart', order: 'above_all' }, active ? {
        fontFamily: 'Arial, sans-serif', fontSize: dashboardSize === 'Compact' ? '11px' : '12px',
        background: 'linear-gradient(145deg, #111C2CF2, #101321F2)', border: '1px solid #586B8A55',
        borderRadius: '10px', borderSpacing: '0', boxShadow: '0 10px 32px #00000033',
        overflow: 'hidden', rows
    } : { rows: [] });
}
</code>