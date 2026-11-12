<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('AutoFib Bands');

const fiblength = input.number('Fibonacci Lookback Length', 265, { min: 1 });

// We need to ensure that maxr and minr are series, not single values
const maxr = highest(close, fiblength);
const minr = lowest(close, fiblength);

// Use the 'sub' function to create a series
const ranr = sub(maxr, minr);

// Ensure all levels are created using operations on series
const Level_100 = maxr;
const Level_764 = sub(maxr, mult(series_of(0.236), ranr));
const Level_618 = sub(maxr, mult(series_of(0.382), ranr));
const Level_500 = sub(maxr, mult(series_of(0.50), ranr));
const Level_382 = add(minr, mult(series_of(0.382), ranr));
const Level_236 = add(minr, mult(series_of(0.236), ranr));
const Level_0 = minr;

const Level_100_painted = paint(Level_100, { color: 'black', name: 'Level 100' });
const Level_764_painted = paint(Level_764, { color: '#3399FF', name: 'Level 76.4' });
const Level_618_painted = paint(Level_618, { color: 'blue', name: 'Level 61.8' });
const Level_500_painted = paint(Level_500, { color: 'lime', name: 'Level 50.0' });
const Level_382_painted = paint(Level_382, { color: 'green', name: 'Level 38.2' });
const Level_236_painted = paint(Level_236, { color: 'red', name: 'Level 23.6' });
const Level_0_painted = paint(Level_0, { color: 'black', name: 'Level 0' });

fill(Level_100_painted, Level_764_painted, 'red', 0.1);
fill(Level_764_painted, Level_618_painted, '#3399FF', 0.1);
fill(Level_618_painted, Level_500_painted, 'lime', 0.1);
fill(Level_500_painted, Level_382_painted, 'lime', 0.1);
fill(Level_382_painted, Level_236_painted, '#3399FF', 0.1);
fill(Level_236_painted, Level_0_painted, 'red', 0.1);
</code>