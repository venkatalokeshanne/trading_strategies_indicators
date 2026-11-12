<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Darvas Box Indicator');

// ===== Inputs =====
const confirmBars        = input.number('Confirmation Bars', 3, { min: 1 });
const showLabels         = input.select('Show Labels', 'Yes', ['Yes', 'No']) === 'Yes';
const breakoutUsesClose  = input.select('Breakout Uses Close', 'Yes', ['Yes', 'No']) === 'Yes';
const useRVOLForBreakout = input.select('Use RVOL for Breakout', 'No', ['Yes', 'No']) === 'Yes';
const rvolLookback       = input.number('RVOL Lookback', 20, { min: 1 });
const rvolThreshold      = input.number('RVOL Threshold', 1.0, { min: 0.1 });

// ===== Validate Inputs =====
assert(confirmBars >= 1, 'Confirmation bars must be at least 1');
assert(close.length >= 52, 'Need at least 52 bars of data for this indicator');

// ===== Core Data Series =====
const rollingHigh52 = highest(high, 52);

// Compute RVOL if needed
const rvol = useRVOLForBreakout
    ? div(volume, sma(volume, rvolLookback))
    : series_of(1);

// ===== State Variables =====
// Candidate box state
let candidateActive    = false;
let candidateTop       = null;
let candidateBottom    = null;
let candidateHighIndex = null;
let confirmCount       = 0;

// Active box state
let boxActive  = false;
let boxTop     = null;
let boxBottom  = null;

// Box bottom persists until broken or new box forms
let boxBottomActive      = false;
let persistentBoxBottom  = null;

// Previous bar's rolling high to detect new highs
let prevRollingHigh = null;

// ===== Output Series =====
const rollingHighSeries   = series_of(null);
const boxTopSeries        = series_of(null);
const boxBottomSeries     = series_of(null);
const boxFormedSignal     = series_of(0);
const boxBreakoutSignal   = series_of(0);
const boxBreakdownSignal  = series_of(0);
const boxFormedLabels     = series_of(null);
const boxBreakoutLabels   = series_of(null);
const boxBreakdownLabels  = series_of(null);

// ===== Main Loop =====
for (let i = 0; i < close.length; i++) {

    // Always populate rolling high
    rollingHighSeries[i] = rollingHigh52[i];

    // Check if price breaks below the persistent box bottom (deactivates box)
    if (boxBottomActive && close[i] < persistentBoxBottom) {
        boxBreakdownSignal[i] = 1;
        if (showLabels) {
            boxBreakdownLabels[i] = 'BD';
        }

        boxBottomActive        = false;
        persistentBoxBottom    = null;

        if (boxActive) {
            boxActive  = false;
            boxTop     = null;
            boxBottom  = null;
        }
    }

    // Check for new 52-bar high event (only when no active box and not in candidate)
    const isNew52High = high[i] === rollingHigh52[i] &&
                        (prevRollingHigh === null || high[i] > prevRollingHigh);

    if (isNew52High && !boxActive && !candidateActive) {
        candidateActive    = true;
        candidateTop       = high[i];
        candidateBottom    = low[i];
        candidateHighIndex = i;
        confirmCount       = 0;

        // Clear previous box bottom when new candidate starts
        boxBottomActive      = false;
        persistentBoxBottom  = null;
    }

    // Process candidate confirmation
    if (candidateActive && i > candidateHighIndex) {

        if (high[i] > candidateTop) {
            // New higher high — reset candidate
            candidateTop       = high[i];
            candidateBottom    = low[i];
            candidateHighIndex = i;
            confirmCount       = 0;
        } else {
            confirmCount++;
            candidateBottom = Math.min(candidateBottom, low[i]);

            if (confirmCount >= confirmBars) {
                // Lock the box
                boxTop    = candidateTop;
                boxBottom = candidateBottom;
                boxActive = true;

                candidateActive     = false;
                boxBottomActive     = true;
                persistentBoxBottom = boxBottom;

                // Retroactively paint the box from its first candle up to now.
                // This is the key fix: the box visually "covers" the candles it
                // was built from, not just the candles after confirmation.
                for (let j = candidateHighIndex; j <= i; j++) {
                    boxTopSeries[j]    = boxTop;
                    boxBottomSeries[j] = boxBottom;
                }

                boxFormedSignal[i] = 1;
                if (showLabels) {
                    boxFormedLabels[i] = 'Box';
                }
            }
        }
    }

    // Populate box top going forward when active
    if (boxActive) {
        boxTopSeries[i] = boxTop;

        const priceBreakout = breakoutUsesClose
            ? close[i] > boxTop
            : high[i] > boxTop;

        const rvolCondition = useRVOLForBreakout
            ? (rvol[i] !== null && rvol[i] >= rvolThreshold)
            : true;

        if (priceBreakout && rvolCondition) {
            boxBreakoutSignal[i] = 1;
            if (showLabels) {
                boxBreakoutLabels[i] = 'BO';
            }

            // Deactivate box top after breakout, keep bottom active
            boxActive = false;
            boxTop    = null;
            boxBottom = null;
        }
    }

    // Populate box bottom whenever active (persists after breakout)
    if (boxBottomActive) {
        boxBottomSeries[i] = persistentBoxBottom;
    }

    prevRollingHigh = rollingHigh52[i];
}

// ===== Paint Outputs =====
paint(rollingHighSeries, {
    name:      'Rolling High 52',
    color:     '#888888',
    thickness: 1,
    style:     'line'
});

paint(boxTopSeries, {
    name:      'Box Top',
    color:     '#0066ff',
    thickness: 2,
    style:     'ladder'
});

paint(boxBottomSeries, {
    name:      'Box Bottom',
    color:     '#0066ff',
    thickness: 2,
    style:     'ladder'
});

paint(showLabels ? boxFormedLabels : series_of(null), {
    name:            'Box labels',
    style:           'labels_above',
    color:           '#0066ff',
    backgroundColor: '#0066ff',
    fontSize:        10,
    verticalOffset:  5
});

paint(showLabels ? boxBreakoutLabels : series_of(null), {
    name:            'BO labels',
    style:           'labels_above',
    color:           '#00ff00',
    backgroundColor: '#00ff00',
    fontSize:        10,
    verticalOffset:  10
});

paint(showLabels ? boxBreakdownLabels : series_of(null), {
    name:            'BD labels',
    style:           'labels_below',
    color:           '#ff0000',
    backgroundColor: '#ff0000',
    fontSize:        10,
    verticalOffset:  5
});

// ===== Register Signals =====
register_signal(boxFormedSignal,    'Box Formed');
register_signal(boxBreakoutSignal,  'Box Breakout');
register_signal(boxBreakdownSignal, 'Box Breakdown');</code>