<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('KRI', 'lower');

// User Inputs
const fastKairiLength = input.number('Length of Kairi Index 0', 7, { min: 1 });
const slowKairiLength = input.number('Length of Kairi Index 1', 24, { min: 1 });
const smaLength = input.number('Length of SMA', 24, { min: 1 });
const plotSlowKairi = input.boolean('Plot Slow Kairi Relative Index?', true);

// Kairi Relative Index formula
const kairiRelativeIndex = (source, length) => {
    const sourceSMA = sma(source, length);
    return mult(div(sub(source, sourceSMA), sourceSMA), 100);
};

// Calculate Fast Kairi line (kri0)
const kri0 = kairiRelativeIndex(close, fastKairiLength);

// Calculate Slow Kairi line (kri1)
const kri1 = kairiRelativeIndex(close, slowKairiLength);

// Calculate Signal Line (_SMA)
const _SMA = sma(kri1, smaLength);

// Plotting
paint(kri0, { color: 'blue', name: 'Fast Kairi' });

paint(plotSlowKairi ? kri1 : series_of(null), { color: 'red', name: 'Slow Kairi' });

paint(_SMA, { color: 'green', name: 'Signal Line' });
</code>