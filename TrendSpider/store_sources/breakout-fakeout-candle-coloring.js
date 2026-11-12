<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Breakout & Fakeout Coloring');

// Input for colors
const colorBreakout = input.color('Breakout Color', 'green');
const colorBreakdown = input.color('Breakdown Color', 'red');
const colorFailedBreakout = input.color('Failed Breakout Color', '#ffcccc');
const colorFailedBreakdown = input.color('Failed Breakdown Color', '#ccffcc');
const colorGray = input.color('Inside Day/Fakeout Color', 'gray');

// Function to get the previous candle's high and low
const getPreviousHL = (index) => {
    if (index <= 0) return { high: null, low: null };
    return { high: high[index - 1], low: low[index - 1] };
};

// Compute the conditions
const breakoutCondition = [];
const breakdownCondition = [];
const failedBreakoutCondition = [];
const failedBreakdownCondition = [];
const insideDayCondition = [];
const fakeoutCondition = [];

for (let i = 1; i < close.length; i++) {
    const { high: prevHigh, low: prevLow } = getPreviousHL(i);
    
    breakoutCondition[i] = high[i] > prevHigh && close[i] > prevHigh;
    breakdownCondition[i] = low[i] < prevLow && close[i] < prevLow;
    failedBreakoutCondition[i] = high[i] > prevHigh && close[i] <= prevHigh;
    failedBreakdownCondition[i] = low[i] < prevLow && close[i] >= prevLow;
    insideDayCondition[i] = high[i] < prevHigh && low[i] > prevLow;
    fakeoutCondition[i] = high[i] > prevHigh && low[i] < prevLow && close[i] >= prevLow && close[i] <= prevHigh;
}

// Register signals for scanning and strategy testing
register_signal(breakoutCondition, 'Breakout');
register_signal(breakdownCondition, 'Breakdown');
register_signal(failedBreakoutCondition, 'Failed Breakout');
register_signal(failedBreakdownCondition, 'Failed Breakdown');
register_signal(insideDayCondition, 'Inside Day');
register_signal(fakeoutCondition, 'Fakeout');

// Apply colors to candles
const candleColors = for_every(
    breakoutCondition,
    breakdownCondition,
    failedBreakoutCondition,
    failedBreakdownCondition,
    insideDayCondition,
    fakeoutCondition,
    (bo, bd, fbo, fbd, id, fo) => {
        if (bo) return colorBreakout;
        if (bd) return colorBreakdown;
        if (fbo) return colorFailedBreakout;
        if (fbd) return colorFailedBreakdown;
        if (id || fo) return colorGray;
        return null;
    }
);

color_candles(candleColors);</code>