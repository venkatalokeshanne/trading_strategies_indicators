<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('MavilimW MTF', 'price');

// This indicator is based on the work of mavilim0732 on Twitter and KivancOzbilgic

const timeFrame = input.select('Time Frame', '1 Day', ['1 minute', '5 minute', '15 minute', '1 hour', '4 hour', '1 Day', '1 Week', '1 Month']);
const showPreviousVersion = input.boolean('Show Previous Version?', false);
const firstMALength = input.number('First Moving Average length', 3);
const secondMALength = input.number('Second Moving Average length', 5);

// Calculate lengths for the main version
const length3 = firstMALength + secondMALength;
const length4 = secondMALength + length3;
const length5 = length3 + length4;
const length6 = length4 + length5;

// Function to calculate nested WMAs
const nestedWMA = (source, lengths) => {
    let result = source;
    for (const length of lengths) {
        result = wma(result, length);
    }
    return result;
};

// Calculate main version
const m6 = nestedWMA(close, [firstMALength, secondMALength, length3, length4, length5, length6]);

// Calculate previous version if enabled
let m6Old = null;
if (showPreviousVersion) {
    m6Old = nestedWMA(close, [3, 5, 8, 13, 21, 34]);
}

// Convert timeFrame to a valid resolution string for request.history
const timeFrameToResolution = {
    '1 minute': '1',
    '5 minute': '5',
    '15 minute': '15',
    '1 hour': '60',
    '4 hour': '240',
    '1 Day': 'D',
    '1 Week': 'W',
    '1 Month': 'M'
};
const resolution = timeFrameToResolution[timeFrame];
assert(resolution, `Invalid time frame: ${timeFrame}`);

// Fetch data from higher time frame
const higherTimeFrameData = await request.history(current.ticker, resolution);
assert(!higherTimeFrameData.error, `Error fetching data: ${higherTimeFrameData.error}`);

// Land higher time frame data onto current time frame
const mavw = land_points_onto_series(higherTimeFrameData.time, m6, time, 'ge');
const mavwInterpolated = interpolate_sparse_series(mavw, 'constant');

// Paint main version
paint(mavwInterpolated, { color: 'blue', linewidth: 2, name: 'MAVW' });

// Paint previous version if enabled
if (showPreviousVersion) {
    const mavwOld = land_points_onto_series(higherTimeFrameData.time, m6Old, time, 'ge');
    const mavwOldInterpolated = interpolate_sparse_series(mavwOld, 'constant');
    paint(mavwOldInterpolated, { color: 'blue', linewidth: 2, name: 'MAVW Old' });
}
</code>