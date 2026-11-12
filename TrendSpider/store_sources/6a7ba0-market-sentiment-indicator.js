<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Market Sentiment Indicator', 'lower');

// ============================================================
// INPUTS (identical to the original, nothing added)
// ============================================================
const volumePeriod    = input.number('Volume SMA Period', 20, { min: 1 });
const oscillatorType  = input.select('Oscillator Type', 'RSI', ['RSI', 'Stochastic', 'Stochastic RSI']);
const oscillatorPeriod = input.number('Oscillator Period', 14, { min: 1 });
const bullishColor    = input.color('Bullish Color', '#4ade80');
const bearishColor    = input.color('Bearish Color', '#f0616d');
const neutralColor    = input.color('Neutral Color', '#7d8799');

// ============================================================
// COLOR HELPERS (display only, no effect on the score)
// ============================================================
function clamp255(n) { return Math.max(0, Math.min(255, Math.round(n))); }

function hex2(n) {
    const s = clamp255(n).toString(16);
    return s.length < 2 ? '0' + s : s;
}

function toRgb(hexStr, fallback) {
    if (typeof hexStr !== 'string') return fallback;
    let h = hexStr.trim();
    if (h.charAt(0) !== '#') return fallback;
    h = h.substring(1);
    if (h.length === 3) {
        h = h.charAt(0) + h.charAt(0) + h.charAt(1) + h.charAt(1) + h.charAt(2) + h.charAt(2);
    }
    if (h.length !== 6) return fallback;
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    if (isNaN(r) || isNaN(g) || isNaN(b)) return fallback;
    return [r, g, b];
}

function rgbToHex(c) { return '#' + hex2(c[0]) + hex2(c[1]) + hex2(c[2]); }

function mixRgb(c1, c2, t) {
    const u = Math.max(0, Math.min(1, t));
    return [c1[0] + (c2[0] - c1[0]) * u, c1[1] + (c2[1] - c1[1]) * u, c1[2] + (c2[2] - c1[2]) * u];
}

const BULL_RGB = toRgb(bullishColor, [74, 222, 128]);
const BEAR_RGB = toRgb(bearishColor, [240, 97, 109]);
const NEUT_RGB = toRgb(neutralColor, [125, 135, 153]);

const BULL_HEX = rgbToHex(BULL_RGB);
const BEAR_HEX = rgbToHex(BEAR_RGB);
const NEUT_HEX = rgbToHex(NEUT_RGB);

function scoreToColor(v) {
    const s = Math.max(0, Math.min(100, v));
    if (s >= 50) return rgbToHex(mixRgb(NEUT_RGB, BULL_RGB, (s - 50) / 50));
    return rgbToHex(mixRgb(NEUT_RGB, BEAR_RGB, (50 - s) / 50));
}

// ============================================================
// ORIGINAL MATH, UNCHANGED
// ============================================================
const volumeSMA = sma(volume, volumePeriod);

const oscillator = (() => {
    switch (oscillatorType) {
        case 'RSI':            return rsi(close, oscillatorPeriod);
        case 'Stochastic':     return stochastic(close, high, low, oscillatorPeriod);
        case 'Stochastic RSI': return stochastic_rsi(close, oscillatorPeriod, 3, 3);
        default: throw 'Invalid oscillator type';
    }
})();

const priceChange = for_every(close, (c, _prev, i) =>
    i === 0 ? 0 : (c - close[i - 1]) / close[i - 1] * 100
);

const sentimentScore = for_every(close, oscillator, volume, volumeSMA, priceChange,
    (c, osc, vol, avgVol, pChange, _prev, i) => {
        if (i === 0) return 50;

        let score = 50;

        score += pChange * 2;

        const volumeRatio = vol / avgVol;
        if (pChange > 0 && volumeRatio > 1) {
            score += 15 * (volumeRatio - 1);
        } else if (pChange < 0 && volumeRatio > 1) {
            score -= 15 * (volumeRatio - 1);
        }

        if (osc > 50) {
            score += (osc - 50) * 0.6;
        } else {
            score -= (50 - osc) * 0.6;
        }

        return Math.max(0, Math.min(100, score));
    }
);

// ============================================================
// PAINTING
// ============================================================
const gradColor = for_every(sentimentScore, (s) => (isFinite(s) ? scoreToColor(s) : null));

paint(sentimentScore, { name: 'Market Sentiment', color: gradColor, thickness: 2, style: 'line' });

paint(series_of(70), { name: 'Overbought', color: BULL_HEX, thickness: 1, style: 'dotted' });
paint(series_of(30), { name: 'Oversold', color: BEAR_HEX, thickness: 1, style: 'dotted' });

// ============================================================
// INFO PANEL (display only)
// ============================================================
const BG = 'rgba(13, 17, 26, 0.94)';
const DIVIDER = '1px solid #1c2231';
const idx = close.length - 1;

function safeVal(arr, i) {
    const v = arr && arr[i];
    return isFinite(v) ? v : 0;
}

const nowScore = safeVal(sentimentScore, idx);
const prevScore = safeVal(sentimentScore, idx - 1);
const delta = nowScore - prevScore;

const pNow = safeVal(priceChange, idx);
const vNow = safeVal(volume, idx);
const vAvgNow = safeVal(volumeSMA, idx);
const oNow = safeVal(oscillator, idx);

const pPts = pNow * 2;
const vRatio = vAvgNow > 0 ? vNow / vAvgNow : 1;
let vPts = 0;
if (pNow > 0 && vRatio > 1) { vPts = 15 * (vRatio - 1); }
else if (pNow < 0 && vRatio > 1) { vPts = -15 * (vRatio - 1); }
const oPts = (oNow - 50) * 0.6;

let regime = 'Neutral';
let regimeColor = NEUT_HEX;
if (nowScore > 70)      { regime = 'Overbought'; regimeColor = BULL_HEX; }
else if (nowScore > 55) { regime = 'Bullish';    regimeColor = BULL_HEX; }
else if (nowScore >= 45){ regime = 'Neutral';    regimeColor = NEUT_HEX; }
else if (nowScore >= 30){ regime = 'Bearish';    regimeColor = BEAR_HEX; }
else                    { regime = 'Oversold';   regimeColor = BEAR_HEX; }

function ptsColor(v) {
    if (v > 0.5) return BULL_HEX;
    if (v < -0.5) return BEAR_HEX;
    return NEUT_HEX;
}

function ptsRow(label, v) {
    return { cells: [
        { text: label, background: BG, color: '#6b7488', fontSize: '10px', padding: '2px 8px', borderTop: DIVIDER },
        { text: (v >= 0 ? '+' : '') + v.toFixed(1), background: BG, color: ptsColor(v), fontSize: '10px', fontWeight: '700', textAlign: 'right', padding: '2px 8px', borderTop: DIVIDER }
    ]};
}

const rows = [];

rows.push({ cells: [{
    text: 'MARKET SENTIMENT', colspan: 2, background: BG, color: '#8a93a6',
    fontSize: '9px', fontWeight: '700', letterSpacing: '1px',
    padding: '4px 8px 3px 8px', borderBottom: DIVIDER
}]});

rows.push({ cells: [
    { text: nowScore.toFixed(1), background: BG, color: scoreToColor(nowScore), fontSize: '22px', fontWeight: '700', padding: '4px 8px 0 8px' },
    { text: regime, background: BG, color: regimeColor, fontSize: '11px', fontWeight: '700', textAlign: 'right', padding: '8px 8px 0 8px' }
]});

rows.push({ cells: [{
    text: (delta >= 0 ? 'u25B2 +' : 'u25BC ') + delta.toFixed(1) + ' vs prior bar',
    colspan: 2, background: BG, color: delta >= 0 ? BULL_HEX : BEAR_HEX,
    fontSize: '9px', padding: '0 8px 5px 8px'
}]});

rows.push(ptsRow('Price Action', pPts));
rows.push(ptsRow('Volume', vPts));
rows.push(ptsRow('Oscillator', oPts));

rows.push({ cells: [
    { text: 'Rel Volume', background: BG, color: '#6b7488', fontSize: '10px', padding: '2px 8px 4px 8px', borderTop: DIVIDER },
    { text: vRatio.toFixed(2) + 'x', background: BG, color: '#c8cedb', fontSize: '10px', fontWeight: '700', textAlign: 'right', padding: '2px 8px 4px 8px', borderTop: DIVIDER }
]});

paint_overlay('Sentiment Panel', { position: 'top_right', offset_x: -10, offset_y: 8 }, {
    background_color: BG,
    order: 'above_all',
    width: 190,
    rows: rows
});</code>