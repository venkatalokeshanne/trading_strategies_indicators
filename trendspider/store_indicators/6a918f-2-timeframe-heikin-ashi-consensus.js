<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('2-Timeframe Heikin Ashi Consensus', 'price', {
    shortName: '2TF HA Consensus',
    description: 'Colors chart candles based on Heikin Ashi direction across two selectable timeframes. Green = both bullish, Red = both bearish, Gray = mixed/neutral. IMPORTANT: Repainting Mode controls behavior. OFF - Confirmed Candles Only uses only fully completed candles from each selected timeframe and does not repaint. ON - Live (Repaints) uses currently forming candles, so candle colors and signals can change until those timeframe candles close.'
});


// =====================================================
// SETTINGS
// =====================================================

const timeframe1 = input.select(
    'Timeframe 1',
    '15',
    constants.time_frames
);

const timeframe2 = input.select(
    'Timeframe 2',
    '60',
    constants.time_frames
);

const repaintMode = input.select(
    'Repainting Mode',
    'OFF - Confirmed Candles Only',
    [
        'OFF - Confirmed Candles Only',
        'ON - Live (Repaints)'
    ]
);

const allowRepainting =
    repaintMode === 'ON - Live (Repaints)';


// =====================================================
// HEIKIN ASHI CALCULATION
// =====================================================

async function getHeikinAshiState(timeframe) {

    const data = await request.history(
        current.ticker,
        timeframe
    );

    assert(
        !data.error,
        `Error fetching ${timeframe} timeframe data: ${data.error}`
    );

    const haOpen = [];
    const haClose = [];
    const state = [];

    for (let i = 0; i < data.close.length; i++) {

        // Standard Heikin Ashi Close
        const currentHaClose =
            (
                data.open[i] +
                data.high[i] +
                data.low[i] +
                data.close[i]
            ) / 4;

        // Standard Heikin Ashi Open
        const currentHaOpen =
            i === 0
                ? (data.open[i] + data.close[i]) / 2
                : (haOpen[i - 1] + haClose[i - 1]) / 2;

        haOpen[i] = currentHaOpen;
        haClose[i] = currentHaClose;

        // 1  = bullish / green
        // -1 = bearish / red
        // 0  = neutral / doji
        if (currentHaClose > currentHaOpen) {
            state[i] = 1;
        } else if (currentHaClose < currentHaOpen) {
            state[i] = -1;
        } else {
            state[i] = 0;
        }
    }


    // =================================================
    // REPAINTING CONTROL
    // =================================================
    //
    // Live:
    // Uses the currently forming HA candle.
    // Its state can change before the candle closes.
    //
    // Confirmed:
    // Shift by one timeframe candle.
    // This means we only use the last fully closed
    // HA candle from the selected timeframe.
    //
    // TrendSpider specifically recommends shifting
    // higher-timeframe data by one candle to avoid
    // using the developing HTF candle.
    // =================================================

    const stateToUse =
        allowRepainting
            ? state
            : shift(state, 1);


    // Map selected timeframe state onto chart timeframe
    const landedState = land_points_onto_series(
        data.time,
        stateToUse,
        time,
        'le'
    );

    return interpolate_sparse_series(
        landedState,
        'constant'
    );
}


// =====================================================
// CALCULATE BOTH TIMEFRAMES CONCURRENTLY
// =====================================================

const [haState1, haState2] = await Promise.all([
    getHeikinAshiState(timeframe1),
    getHeikinAshiState(timeframe2)
]);


// =====================================================
// CONSENSUS CANDLE COLORS
// =====================================================

const candleColors = for_every(
    haState1,
    haState2,
    (state1, state2) => {

        // Both bullish
        if (state1 === 1 && state2 === 1) {
            return 'green';
        }

        // Both bearish
        if (state1 === -1 && state2 === -1) {
            return 'red';
        }

        // Mixed or neutral
        return 'gray';
    }
);


// =====================================================
// PAINT CANDLES
// =====================================================

color_candles(candleColors);


// =====================================================
// SIGNALS
// =====================================================

const bothGreen = for_every(
    haState1,
    haState2,
    (state1, state2) =>
        state1 === 1 &&
        state2 === 1
);

const bothRed = for_every(
    haState1,
    haState2,
    (state1, state2) =>
        state1 === -1 &&
        state2 === -1
);

const mixed = for_every(
    haState1,
    haState2,
    (state1, state2) =>
        !(
            (state1 === 1 && state2 === 1) ||
            (state1 === -1 && state2 === -1)
        )
);


// =====================================================
// REGISTER SIGNALS
// =====================================================

register_signal(
    bothGreen,
    'Both HA Green'
);

register_signal(
    bothRed,
    'Both HA Red'
);

register_signal(
    mixed,
    'HA Mixed'
);</code>