<code x-ref="code" class="hljs" data-clipboard-text>// This work is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International  
// https://creativecommons.org/licenses/by-nc-sa/4.0/
// © Zeiierman
describe_indicator('Relative Trend Index [RTI] (Zeiierman)', 'lower', { 
  decimals: 0, 
  shortName: 'RTI (Zeiierman)',
  mainColorInheritFrom: 'text'
});

// Inputs
const trend_data_count = input('Trend Length', 100, { min: 1, max: 500 });
const signal_length    = input('Signal Length', 20, { min: 1, max: 500 });
const ob = input('OB', 80, { min: 1, max: 500 });
const os = input('OS', 20, { min: 1, max: 500 });

// Initialize arrays for upper and lower trend, Relative Trend Index, overbought and oversold
let upper_trend = Array(close.length).fill(0);
let lower_trend = Array(close.length).fill(0);
let RelativeTrendIndex = Array(close.length).fill(0);
let overboughtLine = Array(close.length).fill(ob);
let oversoldLine = Array(close.length).fill(os);
let midLine = Array(close.length).fill(50);

// Calculate upper and lower trend and Relative Trend Index
for (let i = trend_data_count; i < close.length; i++) {
  upper_trend[i] = Math.max(...close.slice(i - trend_data_count, i));
  lower_trend[i] = Math.min(...close.slice(i - trend_data_count, i));
  RelativeTrendIndex[i] = ((close[i] - lower_trend[i]) / (upper_trend[i] - lower_trend[i])) * 100;
}

// Calculate the moving average of RTI using the sma function
const ma_RTI = sma(RelativeTrendIndex, signal_length);

// Paint
const RTI = paint(RelativeTrendIndex, 'Relative Trend Index (RTI)', '#00897B');
paint(ma_RTI, 'RTI Signal Line', '#00bcd4');
paint(overboughtLine, 'Overbought', '#606060');
paint(oversoldLine, 'Oversold', '#606060');
paint(midLine, 'Mid', '#606060', 'dotted');

//Fill
// Create arrays to represent the boundaries of the fill areas
for (let i = 0; i < RelativeTrendIndex.length; i++) {
  overboughtLine[i] = RelativeTrendIndex[i] > ob ? ob:null;
  oversoldLine[i]   = RelativeTrendIndex[i] < os ? os:null;
}

// Paint the boundary series
const aboveOBLinePainted = paint(overboughtLine, 'Above OB','#606060');
const belowOSLinePainted = paint(oversoldLine, 'Below OS','#606060');

// Fill between the RTI line and the boundary lines
fill(RTI, aboveOBLinePainted, 'lime', 0.2);
fill(RTI, belowOSLinePainted, 'red', 0.2);
</code>