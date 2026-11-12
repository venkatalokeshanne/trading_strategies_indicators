<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Multi-Oscillator Average', 'lower');

// Input parameters for each indicator
const rsiLength = input.number('RSI Length', 14, { min: 1 });
const macdFastLength = input.number('MACD Fast Length', 12, { min: 1 });
const macdSlowLength = input.number('MACD Slow Length', 26, { min: 1 });
const macdSignalLength = input.number('MACD Signal Length', 9, { min: 1 });
const ppoFastLength = input.number('PPO Fast Length', 12, { min: 1 });
const ppoSlowLength = input.number('PPO Slow Length', 26, { min: 1 });
const ppoSignalLength = input.number('PPO Signal Length', 9, { min: 1 });
const cciLength = input.number('CCI Length', 20, { min: 1 });
const mfiLength = input.number('MFI Length', 14, { min: 1 });

// DSS Blau oscillator parameters
const dssLength = input.number('DSS Blau Length', 13, { min: 1 });
const dssStochLength = input.number('DSS Blau Stochastic Length', 8, { min: 1 });
const dssMaType = input.select('DSS Blau MA Type', 'ema', constants.ma_types);

// Moving Average parameters for Multi-Oscillator
const multiOscMaLength = input.number('Multi-Oscillator MA Length', 9, { min: 1 });
const multiOscMaType = input.select('Multi-Oscillator MA Type', 'sma', constants.ma_types);

// Standard Deviation Bands parameters
const stdDevMultiplier = input.number('Std Dev Band Multiplier', 2, { min: 0.1, max: 5, step: 0.1 });

// Calculate individual indicators
const myRsi = rsi(close, rsiLength);
const myMacd = sub(
    sub(ema(close, macdFastLength), ema(close, macdSlowLength)),
    ema(sub(ema(close, macdFastLength), ema(close, macdSlowLength)), macdSignalLength)
);
const myPpo = sub(
    div(sub(ema(close, ppoFastLength), ema(close, ppoSlowLength)), ema(close, ppoSlowLength)),
    ema(div(sub(ema(close, ppoFastLength), ema(close, ppoSlowLength)), ema(close, ppoSlowLength)), ppoSignalLength)
);
const myCci = cci(hlc3, cciLength);
const myMfi = mfi(hlc3, volume, mfiLength);

// Calculate DSS Blau oscillator
const computeMA = indicators[dssMaType];
const myStoch = stochastic(close, high, low, dssStochLength);
const myDssBlau = computeMA(myStoch, dssLength);

// Normalize indicators to a 0-100 scale
const normalizeRsi = myRsi; // RSI is already 0-100
const normalizeMacd = for_every(myMacd, m => (m + 2) * 25); // Assuming MACD typically ranges from -2 to 2
const normalizePpo = for_every(myPpo, p => (p + 4) * 12.5); // Assuming PPO typically ranges from -4 to 4
const normalizeCci = for_every(myCci, c => (c + 200) / 4); // Assuming CCI typically ranges from -200 to 200
const normalizeMfi = myMfi; // MFI is already 0-100
const normalizeDssBlau = myDssBlau; // DSS Blau is already 0-100

// Average all normalized indicators
const myMultiOscillator = div(
    add(normalizeRsi, normalizeMacd, normalizePpo, normalizeCci, normalizeMfi, normalizeDssBlau),
    6
);

// Calculate Moving Average of Multi-Oscillator
const computeMultiOscMA = indicators[multiOscMaType];
const myMultiOscillatorMA = computeMultiOscMA(myMultiOscillator, multiOscMaLength);

// Calculate Standard Deviation Bands
const myStdDev = stdev(myMultiOscillator, multiOscMaLength);
const myUpperBand = add(myMultiOscillatorMA, mult(myStdDev, stdDevMultiplier));
const myLowerBand = sub(myMultiOscillatorMA, mult(myStdDev, stdDevMultiplier));

// Add overbought and oversold levels
const overboughtLevel = 70;
const oversoldLevel = 30;

// Paint the multi-oscillator with dynamic color
paint(myMultiOscillator, { name: 'Multi-Oscillator Average', color: '#fff49b', thickness: 2 });

// Paint the moving average of the multi-oscillator
paint(myMultiOscillatorMA, { name: 'Multi-Oscillator MA', color: '#cccccc', style: 'dotted' });

// Paint the Standard Deviation Bands
paint(myUpperBand, { name: 'Upper Std Dev Band', color: '#cccccc', style: 'ladder' });
paint(myLowerBand, { name: 'Lower Std Dev Band', color: '#cccccc', style: 'ladder' });

</code>