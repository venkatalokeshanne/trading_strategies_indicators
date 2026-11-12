<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('After Hours Chng %', { shortName: '🌙 AH/PM Chg' });

// ─── Asset check ─────────────────────────────────────────────────────────────
if (current.assetType !== 'stock' && current.assetType !== 'etf') {
    throw "This indicator is only applicable to stocks and ETFs";
}

// ─── Inputs ──────────────────────────────────────────────────────────────────
const themeName = input.select('Theme', 'Turquoise Classic', [
    'Midnight Neon',
    'Steel + Cyan',
    'Monochrome + Accent',
    'Turquoise Classic',
    'Carbon Pro',
    'Forest Tape',
    'Ocean Abyss',
    'Void Purple',
    'Amber Terminal',
    'Matrix Rain',
    'Platinum Ice'
]);

const scaleChoice = input('UI Scale', '100%', ['70%', '80%', '100%', '110%', '120%', '150%']);
const signalThreshold = input.number('Signal Threshold %', 5, { min: 0.5, max: 25 });

// ─── UI scale helpers ────────────────────────────────────────────────────────
const uiScale = parseInt(scaleChoice, 10);
function scaleVal(n) { return Math.max(1, Math.round(n * uiScale / 100)); }
function px(n) { return scaleVal(n) + 'px'; }

// Base font sizes
const FS = {
    header: px(15),
    body: px(14),
    small: px(12)
};

// Scaled paddings
const PAD = {
    header: px(8) + ' ' + px(10),
    cell: px(5) + ' ' + px(10),
    big: px(8) + ' ' + px(15)
};

// ─── Theme selector ──────────────────────────────────────────────────────────
function pickTheme(_name) {
    if (_name === 'Steel + Cyan') {
        return {
            panelBg: 'rgba(29, 41, 61, 0.90)',
            border: '#22D3EE',
            headerBg: '#1E2A44',
            headerText: '#F1F5F9',
            rowBg: 'rgba(29, 41, 61, 0.88)',
            labelText: '#67E8F9',
            valueText: '#E2E8F0',
            timeText: '#FFCC33',
            posBg: 'rgba(34, 197, 94, 0.88)',
            negBg: 'rgba(239, 68, 68, 0.88)',
            neutralBg: 'rgba(148, 163, 184, 0.75)',
            rthDimText: '#94A3B8',
            rthDimBg: 'rgba(15, 23, 42, 0.90)'
        };
    }
    if (_name === 'Monochrome + Accent') {
        return {
            panelBg: 'rgba(0, 0, 0, 0.92)',
            border: 'rgba(255, 176, 0, 0.85)',
            headerBg: '#0A0A0A',
            headerText: '#FFB000',
            rowBg: 'rgba(10, 10, 10, 0.92)',
            labelText: '#FFB000',
            valueText: '#E5E5E5',
            timeText: '#FFB000',
            posBg: 'rgba(80, 80, 80, 0.9)',
            negBg: 'rgba(40, 40, 40, 0.95)',
            neutralBg: 'rgba(60, 60, 60, 0.85)',
            rthDimText: '#737373',
            rthDimBg: 'rgba(0, 0, 0, 0.9)'
        };
    }
    if (_name === 'Turquoise Classic') {
        return {
            panelBg: 'rgba(61,61,61,0.85)',
            border: 'MediumTurquoise',
            headerBg: 'MediumTurquoise',
            headerText: '#6200ff',
            rowBg: 'rgba(61,61,61,0.85)',
            labelText: 'MediumTurquoise',
            valueText: 'white',
            timeText: '#FFBA03',
            posBg: 'rgba(0, 128, 0, 0.85)',
            negBg: 'rgba(255, 0, 0, 0.85)',
            neutralBg: 'rgba(128, 128, 128, 0.75)',
            rthDimText: 'gray',
            rthDimBg: 'rgba(61,61,61,0.85)'
        };
    }
    if (_name === 'Carbon Pro') {
        return {
            panelBg: 'rgba(18, 22, 28, 0.95)',
            border: '#9CA3AF',
            headerBg: '#1F2A37',
            headerText: '#E4E7EB',
            rowBg: 'rgba(36, 45, 54, 0.92)',
            labelText: '#9CA3AF',
            valueText: '#E6EAEF',
            timeText: '#D4A017',
            posBg: 'rgba(45, 157, 98, 0.88)',
            negBg: 'rgba(185, 55, 55, 0.88)',
            neutralBg: 'rgba(75, 85, 99, 0.80)',
            rthDimText: '#6B7280',
            rthDimBg: 'rgba(18, 22, 28, 0.95)'
        };
    }
    if (_name === 'Forest Tape') {
        return {
            panelBg: 'rgba(10, 25, 18, 0.9)',
            border: '#34D399',
            headerBg: '#064E3B',
            headerText: '#A7F3D0',
            rowBg: 'rgba(10, 25, 18, 0.9)',
            labelText: '#34D399',
            valueText: '#D1FAE5',
            timeText: '#FBBF24',
            posBg: 'rgba(16, 185, 129, 0.85)',
            negBg: 'rgba(220, 38, 38, 0.85)',
            neutralBg: 'rgba(75, 85, 99, 0.8)',
            rthDimText: '#6B7280',
            rthDimBg: 'rgba(10, 25, 18, 0.9)'
        };
    }
    if (_name === 'Ocean Abyss') {
        return {
            panelBg: 'rgba(8, 19, 35, 0.92)',
            border: '#06B6D4',
            headerBg: '#0C2A4A',
            headerText: '#BAE6FD',
            rowBg: 'rgba(8, 19, 35, 0.90)',
            labelText: '#67E8F9',
            valueText: '#E0F2FE',
            timeText: '#FACC15',
            posBg: 'rgba(34, 211, 151, 0.88)',
            negBg: 'rgba(248, 113, 113, 0.88)',
            neutralBg: 'rgba(103, 114, 142, 0.75)',
            rthDimText: '#64748B',
            rthDimBg: 'rgba(8, 19, 35, 0.92)'
        };
    }
    if (_name === 'Void Purple') {
        return {
            panelBg: 'rgba(13, 9, 26, 0.93)',
            border: '#C026D3',
            headerBg: '#2E1065',
            headerText: '#F3E8FF',
            rowBg: 'rgba(13, 9, 26, 0.90)',
            labelText: '#D946EF',
            valueText: '#F5E8FF',
            timeText: '#FACC15',
            posBg: 'rgba(74, 222, 128, 0.78)',
            negBg: 'rgba(251, 113, 133, 0.78)',
            neutralBg: 'rgba(126, 105, 163, 0.75)',
            rthDimText: '#7C6D9C',
            rthDimBg: 'rgba(13, 9, 26, 0.93)'
        };
    }
    if (_name === 'Amber Terminal') {
        return {
            panelBg: 'rgba(28, 18, 8, 0.94)',
            border: '#F59E0B',
            headerBg: '#451A03',
            headerText: '#FEF3C7',
            rowBg: 'rgba(28, 18, 8, 0.92)',
            labelText: '#FBBF24',
            valueText: '#FEF9C3',
            timeText: '#67E8F9',
            posBg: 'rgba(163, 230, 77, 0.88)',
            negBg: 'rgba(248, 113, 113, 0.88)',
            neutralBg: 'rgba(161, 98, 7, 0.75)',
            rthDimText: '#B45309',
            rthDimBg: 'rgba(28, 18, 8, 0.94)'
        };
    }
    if (_name === 'Matrix Rain') {
        return {
            panelBg: 'rgba(2, 12, 8, 0.93)',
            border: '#22C55E',
            headerBg: '#052E16',
            headerText: '#86EFAC',
            rowBg: 'rgba(2, 12, 8, 0.90)',
            labelText: '#4ADE80',
            valueText: '#D1FAE5',
            timeText: '#E0F2FE',
            posBg: 'rgba(74, 222, 128, 0.90)',
            negBg: 'rgba(185, 28, 28, 0.88)',
            neutralBg: 'rgba(52, 211, 153, 0.65)',
            rthDimText: '#4F7A5F',
            rthDimBg: 'rgba(2, 12, 8, 0.93)'
        };
    }
    if (_name === 'Platinum Ice') {
        return {
            panelBg: 'rgba(15, 23, 42, 0.92)',
            border: '#E0F2FE',
            headerBg: '#1E2937',
            headerText: '#F0F9FF',
            rowBg: 'rgba(15, 23, 42, 0.90)',
            labelText: '#BAE6FD',
            valueText: '#F1F5F9',
            timeText: '#FDE047',
            posBg: 'rgba(52, 211, 153, 0.88)',
            negBg: 'rgba(248, 113, 113, 0.88)',
            neutralBg: 'rgba(148, 163, 184, 0.80)',
            rthDimText: '#94A3B8',
            rthDimBg: 'rgba(15, 23, 42, 0.92)'
        };
    }
    return {
        panelBg: 'rgba(10, 12, 18, 0.90)',
        border: '#6200ff',
        headerBg: '#100099',
        headerText: '#FFFFFF',
        rowBg: 'rgba(10, 12, 18, 0.90)',
        labelText: '#A78BFA',
        valueText: '#E5E7EB',
        timeText: '#FBBF24',
        posBg: 'rgba(34, 197, 94, 0.88)',
        negBg: 'rgba(239, 68, 68, 0.88)',
        neutralBg: 'rgba(148, 163, 184, 0.75)',
        rthDimText: '#64748B',
        rthDimBg: 'rgba(10, 12, 18, 0.90)'
    };
}

const TH = pickTheme(themeName);

// ─── Session detection ───────────────────────────────────────────────────────
const lastCandleTime = time_of(time[time.length - 1]);
const currentHour = lastCandleTime.hours + (lastCandleTime.minutes / 60);
const isRTH = currentHour >= 9.5 && currentHour < 16;
const isAfterHours = currentHour >= 16 || currentHour < 4;
const isPremarket = currentHour >= 4 && currentHour < 9.5;

// ─── Daily close fetch ───────────────────────────────────────────────────────
const getDailyClosingPrices = async () => {
    try {
        const data = await request.history(current.ticker, 'D', { ext_session: false });
        assert(!data.error, `Error fetching data: ${data.error}`);
        return interpolate_sparse_series(land_points_onto_series(data.time, data.close, time, 'ge'), 'constant');
    } catch (error) {
        console.log("Error fetching closing price:", error);
        return null;
    }
};

const closingPrices = await getDailyClosingPrices();
const closingPrice = closingPrices ? closingPrices[close.length - 1] : null;
const currentPrice = close[close.length - 1];

// ─── Percent change ──────────────────────────────────────────────────────────
let percentChange = null;
if (closingPrice !== null && currentPrice !== null) {
    percentChange = ((currentPrice - closingPrice) / closingPrice) * 100;
}

// ─── Signal series ───────────────────────────────────────────────────────────
const signalArray = time.map((t, index) => {
    const barTime = time_of(t);
    const barHour = barTime.hours + (barTime.minutes / 60);
    const barIsRTH = barHour >= 9.5 && barHour < 16;
    if (barIsRTH || !closingPrices || closingPrices[index] === null) return false;
    const barPercentChange = ((close[index] - closingPrices[index]) / closingPrices[index]) * 100;
    return Math.abs(barPercentChange) >= signalThreshold;
});

register_signal(signalArray, 'AH Change > Threshold');

// ─── Overlay placement ───────────────────────────────────────────────────────
const overlayOpts = {
    position: 'center_right',
    offset_x: -50,
    offset_y: 0,
    order: 'above_all'
};

// ─── RTH: minimal placeholder ────────────────────────────────────────────────
if (isRTH) {
    paint_overlay('AH Change Table', overlayOpts, {
        border: `${scaleVal(2)}px solid ${TH.rthDimText}`,
        background: TH.rthDimBg,
        rows: [
            {
                cells: [{
                    text: 'AH/PM Change',
                    fontWeight: 'bold',
                    color: TH.rthDimText,
                    background: TH.rthDimBg,
                    padding: PAD.header,
                    fontSize: FS.header,
                    textAlign: 'center'
                }]
            },
            {
                cells: [{
                    text: 'Off During RTH',
                    color: TH.rthDimText,
                    background: TH.rthDimBg,
                    padding: PAD.big,
                    fontStyle: 'italic',
                    fontSize: FS.body,
                    textAlign: 'center'
                }]
            }
        ]
    });
    return;
}

// ─── Active session label ────────────────────────────────────────────────────
const sessionLabel = isPremarket ? 'PM Change' : 'AH Change';

// ─── Pct background picker ───────────────────────────────────────────────────
const pctBg = percentChange === null
    ? TH.neutralBg
    : percentChange > 0 ? TH.posBg
    : percentChange < 0 ? TH.negBg
    : TH.neutralBg;

// ─── Build rows ──────────────────────────────────────────────────────────────
const rows = [
    {
        cells: [{
            text: sessionLabel,
            fontWeight: 'bold',
            color: TH.headerText,
            background: TH.headerBg,
            padding: PAD.header,
            fontSize: FS.header,
            textAlign: 'center',
            colspan: 2
        }]
    },
    {
        cells: [
            {
                text: 'Session Close',
                fontWeight: 'bold',
                color: TH.labelText,
                background: TH.rowBg,
                padding: PAD.cell,
                fontSize: FS.body
            },
            {
                text: closingPrice ? closingPrice.toFixed(2) : 'N/A',
                color: TH.labelText,
                background: TH.rowBg,
                padding: PAD.cell,
                fontSize: FS.body
            }
        ]
    },
    {
        cells: [
            {
                text: 'Current Candle',
                color: TH.valueText,
                background: TH.rowBg,
                padding: PAD.cell,
                fontSize: FS.body
            },
            {
                text: currentPrice ? currentPrice.toFixed(2) : 'N/A',
                color: TH.valueText,
                background: TH.rowBg,
                padding: PAD.cell,
                fontSize: FS.body
            }
        ]
    },
    {
        cells: [
            {
                text: 'Last Candle Time',
                color: TH.valueText,
                background: TH.rowBg,
                padding: PAD.cell,
                fontSize: FS.small
            },
            {
                text: `${lastCandleTime.hours}:${lastCandleTime.minutes.toString().padStart(2, '0')}`,
                color: TH.timeText,
                background: TH.rowBg,
                padding: PAD.cell,
                fontSize: FS.small
            }
        ]
    },
    {
        cells: [
            {
                text: sessionLabel,
                fontWeight: 'bold',
                color: TH.valueText,
                background: TH.rowBg,
                padding: PAD.cell,
                fontSize: FS.body
            },
            {
                text: percentChange !== null ? percentChange.toFixed(2) + '%' : 'N/A',
                color: 'white',
                background: pctBg,
                padding: PAD.cell,
                fontWeight: 'bold',
                fontSize: FS.body
            }
        ]
    }
];

// ─── Paint overlay ───────────────────────────────────────────────────────────
paint_overlay('AH Change Table', overlayOpts, {
    border: `${scaleVal(2)}px solid ${TH.border}`,
    background: TH.panelBg,
    rows
});
</code>