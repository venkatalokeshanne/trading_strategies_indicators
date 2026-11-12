<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Breadth Snapshot with 5-Day Comparison (Indexes)', 'price');

// ============================================================================
// BREADTH SNAPSHOT WITH 5-DAY COMPARISON
// Shows current breadth reading for major indexes alongside the reading
// from 5 days ago for comparison.
//
// PERFORMANCE: All history requests are dispatched in parallel and resolved
// together via Promise.all (per "Best Practices of Requesting Data" #3 in
// the TrendSpider scripting docs). The 5-day-ago value is read from the
// same close[] array as the current value -- no second request per ticker.
// ============================================================================

// Breadth metric options available for selection
const metricOptions = [
    '% Above 20-SMA',
    '% Above 50-SMA',
    '% Above 200-SMA',
    '% 21-Day Highs',
    '% 63-Day Highs'
];

const prefixMap = {
    '% Above 20-SMA':  '$MA20',
    '% Above 50-SMA':  '$MA50',
    '% Above 200-SMA': '$MA200',
    '% 21-Day Highs':  '$H21',
    '% 63-Day Highs':  '$H63'
};

const selectedMetric = input.select('Breadth Metric', '% Above 50-SMA', metricOptions);
const prefix = prefixMap[selectedMetric];

// ----------------------------------------------------------------------------
// Indexes universe
// ----------------------------------------------------------------------------
const indexes = [
    { key: 'SP500',  label: 'S&P 500'      },
    { key: 'N100',   label: 'Nasdaq 100'   },
    { key: 'R2000',  label: 'Russell 2000' },
    { key: 'DJ30',   label: 'Dow 30'       },
    { key: 'SPM400', label: 'S&P MidCap'   }
];

// ----------------------------------------------------------------------------
// PARALLEL FETCH (canonical pattern)
// Build an array of unawaited request.history() promises, then resolve them
// together with Promise.all. No await inside the loop.
// ----------------------------------------------------------------------------
const historyPromises = [];
for (let i = 0; i < indexes.length; i++) {
    historyPromises.push(request.history(prefix + indexes[i].key, 'D'));
}
const histories = await Promise.all(historyPromises);

// ----------------------------------------------------------------------------
// Extract current and 5-day-ago values from each resolved history
// ----------------------------------------------------------------------------
function extractValues(h) {
    if (!h || h.error) return { current: null, previous: null };
    if (!h.close || h.close.length === 0) return { current: null, previous: null };

    const lastIdx = h.close.length - 1;
    const prevIdx = h.close.length - 6;

    const lastVal = h.close[lastIdx];
    const currentPct = (typeof lastVal === 'number') ? lastVal * 100 : null;

    let previousPct = null;
    if (prevIdx >= 0) {
        const prevVal = h.close[prevIdx];
        previousPct = (typeof prevVal === 'number') ? prevVal * 100 : null;
    }

    return { current: currentPct, previous: previousPct };
}

const indexValues = [];
for (let i = 0; i < indexes.length; i++) {
    const vals = extractValues(histories[i]);
    indexValues.push({
        label: indexes[i].label,
        current: vals.current,
        previous: vals.previous
    });
}

// ----------------------------------------------------------------------------
// Colors & thresholds
// ----------------------------------------------------------------------------
const GREEN = '#22c55e';
const LIGHT_GREEN = '#86efac';
const YELLOW = '#eab308';
const RED = '#ef4444';
const GRAY = '#9ca3af';
const MUTED = '#6b7280';
const BG_TRACK = 'rgba(255,255,255,0.08)';
const DIVIDER = '1px solid rgba(255,255,255,0.06)';

function colorForPct(v) {
    if (v === null) return GRAY;
    if (v >= 70) return GREEN;
    if (v >= 50) return LIGHT_GREEN;
    if (v >= 30) return YELLOW;
    return RED;
}

function fmtPct(v) {
    if (v === null) return '—';
    return v.toFixed(0) + '%';
}

// ----------------------------------------------------------------------------
// Row builder — label + progress bar + current value + 5-day-ago value
// ----------------------------------------------------------------------------
const BAR_WIDTH = 110;
const LABEL_W   = '100px';
const VAL_W     = '45px';

function dataRow(item) {
    const currentPct = item.current;
    const previousPct = item.previous;

    const currentCol = colorForPct(currentPct);
    const previousCol = colorForPct(previousPct);

    const clamped = currentPct === null ? 0 : Math.max(0, Math.min(100, currentPct));
    const fillWidth = (clamped / 100) * BAR_WIDTH;

    const barHtml = `<div style="width:${BAR_WIDTH}px;height:8px;background:${BG_TRACK};border-radius:4px;overflow:hidden;"><div style="width:${fillWidth}px;height:8px;background:${currentCol};border-radius:4px;"></div></div>`;

    return {
        cells: [
            {
                text: item.label,
                color: '#d1d5db',
                fontSize: '11px',
                width: LABEL_W,
                textAlign: 'left',
                padding: '4px 8px',
                borderTop: DIVIDER
            },
            {
                text: barHtml,
                width: BAR_WIDTH + 'px',
                textAlign: 'left',
                padding: '4px 8px',
                borderTop: DIVIDER
            },
            {
                text: fmtPct(currentPct),
                color: currentCol,
                fontSize: '12px',
                fontWeight: 'bold',
                width: VAL_W,
                textAlign: 'right',
                padding: '4px 8px',
                borderTop: DIVIDER
            },
            {
                text: fmtPct(previousPct),
                color: previousCol,
                fontSize: '11px',
                width: VAL_W,
                textAlign: 'right',
                padding: '4px 8px',
                borderTop: DIVIDER
            }
        ]
    };
}

function sectionHeader(text) {
    return {
        cells: [
            {
                text: text,
                color: MUTED,
                fontSize: '10px',
                fontWeight: 'bold',
                letterSpacing: '1px',
                colspan: 4,
                textAlign: 'left',
                padding: '10px 8px 4px 8px'
            }
        ]
    };
}

// ----------------------------------------------------------------------------
// Build rows
// ----------------------------------------------------------------------------
const rows = [];

rows.push({
    cells: [
        {
            text: 'BREADTH SNAPSHOT — ' + selectedMetric.toUpperCase(),
            color: '#f9fafb',
            fontSize: '12px',
            fontWeight: 'bold',
            letterSpacing: '1px',
            colspan: 4,
            textAlign: 'left',
            padding: '4px 8px 8px 8px'
        }
    ]
});

rows.push({
    cells: [
        { text: '', width: LABEL_W, padding: '2px 8px', fontSize: '9px' },
        { text: '', width: BAR_WIDTH + 'px', padding: '2px 8px', fontSize: '9px' },
        {
            text: 'LAST CLS',
            color: MUTED,
            fontSize: '9px',
            fontWeight: 'bold',
            width: VAL_W,
            textAlign: 'right',
            padding: '2px 8px'
        },
        {
            text: '5D AGO',
            color: MUTED,
            fontSize: '9px',
            fontWeight: 'bold',
            width: VAL_W,
            textAlign: 'right',
            padding: '2px 8px'
        }
    ]
});

rows.push(sectionHeader('INDEXES'));

for (let i = 0; i < indexValues.length; i++) {
    rows.push(dataRow(indexValues[i]));
}

// ----------------------------------------------------------------------------
// Render overlay
// ----------------------------------------------------------------------------
paint_overlay('BreadthSnapshot', {
    position: 'top_right',
    offset_x: -40,
    offset_y: 40,
    order: 'above_all'
}, {
    background: 'rgba(13, 13, 13, 0.94)',
    padding: '12px',
    borderRadius: '8px',
    rows: rows
});
</code>