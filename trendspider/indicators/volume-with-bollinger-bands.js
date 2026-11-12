<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Volume Bollinger Bands', 'lower', { decimals: 0, shortName: 'Vol BB' });

// Input parameters for the Bollinger Bands calculation
const length = input.number('Length', 20, { min: 1, max: 100 });
const multiplier = input.number('Multiplier', 2, { min: 0.1, max: 5 });

// Calculate the moving average of volume
const maVolume = sma(volume, length);

// Calculate the standard deviation of volume
const stdevVolume = stdev(volume, length);

// Calculate the upper and lower Bollinger Bands
const upperBand = add(maVolume, mult(stdevVolume, multiplier));
const lowerBand = sub(maVolume, mult(stdevVolume, multiplier));

// Paint the moving average of volume
paint(maVolume, { name: 'MA Volume', color: 'blue', thickness: 2 });

// Paint the upper Bollinger Band
paint(upperBand, { name: 'Upper Band', color: 'red', thickness: 2 });

// Paint the lower Bollinger Band
paint(lowerBand, { name: 'Lower Band', color: 'green', thickness: 2 });

// Paint the actual volume
paint(volume, { name: 'Volume', style: 'histogram', color: volume.map(v => v > maVolume[volume.indexOf(v)] ? 'grey' : '#999') });

fill(
    paint(upperBand, { hidden: true }),
    paint(lowerBand, { hidden: true }),
    '#cccccc',
    0.1
);
</code>