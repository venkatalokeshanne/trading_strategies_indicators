<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('T3', 'price');

// This indicator was inspired by the work of everget based on the work of Tim Tillson

const length = input.number('Length', 8, { min: 1 });
const factor = input.number('Factor', 0.7, { min: 0, max: 1 });
const highlightMovements = input.boolean('Highlight Movements ?', true);
const source = input.select('Source', 'close', constants.price_source_options);
const mySource = prices[source];

// Generalized DEMA (GD) function
const gd = (data, period) => {
    const ema1 = ema(data, period);
    const ema2 = ema(ema1, period);
    return add(mult(ema1, 1 + factor), mult(ema2, -factor));
};

// Calculate T3
const result1 = gd(mySource, length);
const result2 = gd(result1, length);
const t3Value = gd(result2, length);

// Determine color based on movement
const t3Color = for_every(t3Value, (t, prevT, i) => {
    if (!highlightMovements) return '#6d1e7f';
    return i > 0 && t > prevT ? 'green' : 'red';
});

paint(t3Value, { 
    color: t3Color, 
    linewidth: 2,
    name: 'T3'
});
</code>