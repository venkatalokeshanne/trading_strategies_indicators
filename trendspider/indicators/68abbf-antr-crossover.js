<code x-ref="code" class="hljs" data-clipboard-text>// This script had been cloned from "ANTR" at 08 Aug 2025, 15:22
describe_indicator('ANTR Crossover', 'lower');

const smaLengthLong = input.number('MA Length Long', 20, { min: 1 });
const smaLengthShort = input.number('MA Length Short', 5, { min: 1 });

// Calculate the Normalized ATR
const normalizedATR = mult(div(sub(high, low), close), 100);

// Apply SMA to the Normalized ATR using the user-defined length
const smantrLong = sma(normalizedATR, smaLengthLong);
const smantrShort = sma(normalizedATR, smaLengthShort);

paint(smantrLong, { name: 'ANTR Long %', color: 'cyan' });
paint(smantrShort, { name: 'ANTR Short %', color: 'white' });
</code>