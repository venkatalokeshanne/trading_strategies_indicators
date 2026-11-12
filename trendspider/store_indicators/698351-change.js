<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Change% label', 'upper');

// Only display this indicator if the asset is stock or etf
if (current.assetType !== 'stock' && current.assetType !== 'etf') {
    throw "This indicator is only applicable to stocks and ETFs";
}

// Check current time to determine session
const lastCandleTime = time_of(time[time.length - 1]);
const currentHour = lastCandleTime.hours + (lastCandleTime.minutes / 60);

// Define session boundaries
const isRTH = currentHour >= 9.5 && currentHour < 16;
const isAfterHours = currentHour >= 16 || currentHour < 4;

// Input for label font size
const fontSize = input.number('Label Font Size', 12, { min: 8, max: 24 });

// Function to get the reference closing price
const getRefClose = async () => {
    try {
        const data = await request.history(current.ticker, 'D', { ext_session: false });
        assert(!data.error, `Error fetching data: ${data.error}`);
        // During RTH: today's daily candle is incomplete, so use length - 2 (yesterday)
        // During extended hours: last daily candle is the correct reference (length - 1)
        const closeIndex = isRTH ? data.close.length - 2 : data.close.length - 1;
        return data.close[closeIndex];
    } catch (error) {
        console.log("Error fetching closing price:", error);
        return null;
    }
};

// Get data
const refClose = await getRefClose();
const currentPrice = close[close.length - 1];

// Calculate percent change
let percentChange = null;
if (refClose !== null && currentPrice !== null) {
    percentChange = ((currentPrice - refClose) / refClose) * 100;
}

// Paint a single label on the last bar only
const labels = for_every(close, (c, _, i) => {
    if (i === close.length - 1 && percentChange !== null) {
        const icon = percentChange >= 0 ? '🟢' : '🔴';
        const val = Math.abs(percentChange).toFixed(2);
        const labelText = isAfterHours ? 'AH Chg' : 'Chg';
        return `${labelText}: ${icon}${val}%`;
    }
    return null;
});

paint(labels, {
    style: 'labels_above',
    font_weight: 'bold',
    font_size: fontSize,
    color: '#444444',
    backgroundColor: 'white',
    backgroundOpacity: 0.9,
    verticalOffset: 40,
    borderColor: 'black',
    borderWidth: 1,
    name: 'Label'
});
</code>