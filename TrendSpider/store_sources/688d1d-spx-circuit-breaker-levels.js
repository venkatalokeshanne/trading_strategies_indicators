<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('SPX Circuit Breaker Levels');

// --- Inputs ---
const lvl1Pct = input.number('Level 1 CB %', 7,  { min: 1, max: 20 });
const lvl2Pct = input.number('Level 2 CB %', 13, { min: 1, max: 20 });
const lvl3Pct = input.number('Level 3 CB %', 20, { min: 1, max: 20 });

// --- Colors (adjust as you like) ---
const L1_COLOR = '#32cd32';   // lime green instead of yellow
const L2_COLOR = 'orange';
const L3_COLOR = 'red';

// --- Previous day close series ---
function getPreviousDayClose() {
    const out = series_of(null);
    let lastSession = null;

    for (let i = 0; i < close.length; i++) {
        const sess = bar_at(time[i]).session;
        if (sess !== lastSession) {
            // new session -> yesterday's close is the previous bar's close (if it exists)
            out[i] = i > 0 ? close[i - 1] : null;
            lastSession = sess;
        } else {
            out[i] = out[i - 1];
        }
    }
    return out;
}

const prevClose = getPreviousDayClose();

// --- Level calculations ---
const level1 = for_every(prevClose, pc => pc ? pc * (1 - lvl1Pct / 100) : null);
const level2 = for_every(prevClose, pc => pc ? pc * (1 - lvl2Pct / 100) : null);
const level3 = for_every(prevClose, pc => pc ? pc * (1 - lvl3Pct / 100) : null);

// --- Paint lines (STATIC names) ---
const l1Line = paint(level1, {
    color: L1_COLOR,
    thickness: 2,
    style: 'line',
    name: 'CB Level 1'
});

const l2Line = paint(level2, {
    color: L2_COLOR,
    thickness: 2,
    style: 'line',
    name: 'CB Level 2'
});

const l3Line = paint(level3, {
    color: L3_COLOR,
    thickness: 2,
    style: 'line',
    name: 'CB Level 3'
});

// --- Labels at the most recent bar ---
const lastIdx = close.length - 1;

paint_label_at_line(l1Line, lastIdx, `Level 1 (${lvl1Pct}%)`, {
    color: L1_COLOR,
    background_color: 'black',
    vertical_align: 'bottom'
});

paint_label_at_line(l2Line, lastIdx, `Level 2 (${lvl2Pct}%)`, {
    color: L2_COLOR,
    background_color: 'black',
    vertical_align: 'bottom'
});

paint_label_at_line(l3Line, lastIdx, `Level 3 (${lvl3Pct}%)`, {
    color: L3_COLOR,
    background_color: 'black',
    vertical_align: 'bottom'
});
</code>