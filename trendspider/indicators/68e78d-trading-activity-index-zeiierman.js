<code x-ref="code" class="hljs" data-clipboard-text>// This work is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International  
// https://creativecommons.org/licenses/by-nc-sa/4.0/
// © Zeiierman
describe_indicator('Trading Activity Index (Zeiierman)', 'lower', {
  decimals: 0,
  shortName: 'Trading Activity Index (Zeiierman)',
  warmup: 1500
});

// Formation window (bars) for averaging dollar volume before taking the log.
const myFormationWindow = input.number('Formation Window (bars)', 20, { min: 2, max: 100 });

// History window (bars) used to compute rolling percentiles and bands.
const myHistoryWindow = input.number('History Window (bars)', 252, { min: 50, max: 1000 });

// Dollar Volume: price * volume
const myDollarVolume = mult(close, volume);
const myDollarVolumeAvg = sma(myDollarVolume, myFormationWindow);

// VOLSCALE proxy = log(average(dollar volume))
const myVScale = myDollarVolumeAvg.map(_avgVol => Math.log(Math.max(_avgVol, 1e-10)));

// Rolling percentiles of VOLSCALE proxy over history window
// We use sliding_window_function to compute percentiles
const myP20 = sliding_window_function(myVScale, myHistoryWindow, _window => {
  const sorted = [..._window].sort((a, b) => a - b);
  const pos = (sorted.length - 1) * 0.20;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
});

const myP40 = sliding_window_function(myVScale, myHistoryWindow, _window => {
  const sorted = [..._window].sort((a, b) => a - b);
  const pos = (sorted.length - 1) * 0.40;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
});

const myP60 = sliding_window_function(myVScale, myHistoryWindow, _window => {
  const sorted = [..._window].sort((a, b) => a - b);
  const pos = (sorted.length - 1) * 0.60;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
});

const myP80 = sliding_window_function(myVScale, myHistoryWindow, _window => {
  const sorted = [..._window].sort((a, b) => a - b);
  const pos = (sorted.length - 1) * 0.80;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
});

// Percentile rank proxy for display (normalize by rolling min/max)
const myVMin = lowest(myVScale, myHistoryWindow);
const myVMax = highest(myVScale, myHistoryWindow);

const myRank01 = for_every(myVScale, myVMin, myVMax, (_vscale, _vmin, _vmax) => {
  if (_vmax === _vmin) {
    return 0.5;
  }
  return Math.max(0.0, Math.min(1.0, (_vscale - _vmin) / (_vmax - _vmin)));
});

// Gradient color function: Light blue to Orange/Red
const myGradientColor = myRank01.map(_val => {
  const r1 = 173.0;
  const g1 = 216.0;
  const b1 = 230.0;
  const r2 = 255.0;
  const g2 = 69.0;
  const b2 = 0.0;
  const r = Math.round(r1 + (r2 - r1) * _val);
  const g = Math.round(g1 + (g2 - g1) * _val);
  const b = Math.round(b1 + (b2 - b1) * _val);
  return `rgb(${r}, ${g}, ${b})`;
});

// Blue gradient function for percentile bands: Light blue to Deep blue
const myBlueGradient = _val => {
  const r1 = 173.0;
  const g1 = 216.0;
  const b1 = 230.0;
  const r2 = 0.0;
  const g2 = 0.0;
  const b2 = 255.0;
  const r = Math.round(r1 + (r2 - r1) * _val);
  const g = Math.round(g1 + (g2 - g1) * _val);
  const b = Math.round(b1 + (b2 - b1) * _val);
  return `rgb(${r}, ${g}, ${b})`;
};

// Plot the main trading activity line with gradient color
paint(myVScale, { name: 'Trading Activity', style: 'line', color: myGradientColor });

// Plot quintile bands with blue gradient
paint(myP20, { name: 'P20', style: 'line', color: myBlueGradient(0.2) });
paint(myP40, { name: 'P40', style: 'line', color: myBlueGradient(0.4) });
paint(myP60, { name: 'P60', style: 'line', color: myBlueGradient(0.6) });
paint(myP80, { name: 'P80', style: 'line', color: myBlueGradient(0.8) });
</code>