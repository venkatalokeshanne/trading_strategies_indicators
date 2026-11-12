<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Earnings Bubbles');

// Input toggle for surprise type
const surpriseType = input.select('Surprise Type', 'earnings', ['earnings', 'revenue']);

// Input toggle for showing labels
const showLabels = input.boolean('Show Labels', true);

// Input colors for each category (tied for bubbles and labels)
const beatColor = input.color('Beat Color', '#8ac14b');
const missColor = input.color('Miss Color', '#ff0000');
const inlineColor = input.color('Inline Color', 'grey');

const earnings = await request.earnings(constants.ticker);

const nmdTime = earnings.map(record => record.timestamp);

// Select surprise based on toggle
const surpriseValues = surpriseType === 'earnings' ? earnings.map(record => record.eps_surprise_percent) : earnings.map(record => record.revenue_surprise_percent);

const surpriseLanded = land_points_onto_series(nmdTime, surpriseValues, time, 'ge');

// Use a logarithmic scale to amplify bubble sizes, especially for small values.
const bubbles = for_every(surpriseLanded, close, (surprise, c) => {
    if (surprise == null) {
        return null;
    }
    const size = 10 + Math.log10(Math.abs(surprise) + 1) * 20; 
    return { y: c, z: size };
});

// Tie bubble colors to input colors
const bubblesColors = for_every(surpriseLanded, surprise => {
    if (surprise > 0) return beatColor;
    if (surprise < 0) return missColor;
    return inlineColor; // Inline for surprise = 0
});

paint(bubbles, { style: 'bubble', color: bubblesColors });

// Create labels for surprise % beat to 2 decimal places
const labels = for_every(surpriseLanded, surprise => {
    if (surprise == null) {
        return null;
    }
    return `${surprise > 0 ? '+' : ''}${surprise.toFixed(2)}%`;
});

// Split labels for positive, negative, and zero
const positiveLabels = for_every(surpriseLanded, labels, (surprise, label) => {
    return surprise > 0 ? label : null;
});

const negativeLabels = for_every(surpriseLanded, labels, (surprise, label) => {
    return surprise < 0 ? label : null;
});

const zeroLabels = for_every(surpriseLanded, labels, (surprise, label) => {
    return surprise === 0 ? label : null;
});

// Conditionally paint labels based on toggle, using tied input colors
if (showLabels) {
    // Paint positive labels with beat color
    paint(positiveLabels, { style: 'labels_above', color: beatColor, name: 'Surprise Label' });

    // Paint negative labels with miss color
    paint(negativeLabels, { style: 'labels_below', color: missColor, name: 'Miss Label' });

    // Paint zero labels inline (using labels_above as default, inline color)
    paint(zeroLabels, { style: 'labels_above', color: inlineColor, name: 'Inline Label' });
}</code>