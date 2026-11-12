<code x-ref="code" class="hljs" data-clipboard-text>// This indicator was made by AI and has not been QA checked by the TrendSpider development team. The indicator is for entertainment purposes only.

describe_indicator('ATR Support and Resistance Levels', 'overlay', { shortName: 'ATR S/R' });

// Inputs for ATR period and user-defined multipliers with allowance for negative values
const atrPeriod = input.number('ATR Period', 14);  // ATR period default is 14
const multiplierS1 = input.number('S1 Multiplier', -1, { min: -10, max: 0 }); // Allow negative S1 multiplier
const multiplierS2 = input.number('S2 Multiplier', -1.5, { min: -10, max: 0 }); // Allow negative S2 multiplier
const multiplierR1 = input.number('R1 Multiplier', 1, { min: 0, max: 10 });  // R1 multiplier must be positive
const multiplierR2 = input.number('R2 Multiplier', 1.5, { min: 0, max: 10 });  // R2 multiplier must be positive

// Request daily historical data for ATR and close prices
const dailyData = await request.history(current.ticker, 'D', { land_onto_current_candles: false });

// Calculate ATR from daily data
const dailyATR = atr(dailyData.high, dailyData.low, dailyData.close, atrPeriod);

// Initialize arrays for daily ATR support and resistance levels using prior day's ATR and close
const s1_daily = dailyData.close.map((closePrice, index) => index > 0 ? dailyData.close[index - 1] + (multiplierS1 * dailyATR[index - 1]) : null);
const s2_daily = dailyData.close.map((closePrice, index) => index > 0 ? dailyData.close[index - 1] + (multiplierS2 * dailyATR[index - 1]) : null);
const r1_daily = dailyData.close.map((closePrice, index) => index > 0 ? dailyData.close[index - 1] + (multiplierR1 * dailyATR[index - 1]) : null);
const r2_daily = dailyData.close.map((closePrice, index) => index > 0 ? dailyData.close[index - 1] + (multiplierR2 * dailyATR[index - 1]) : null);

// Land the daily ATR levels onto the intraday time series
const s1_intraday = land_points_onto_series(dailyData.time, s1_daily, time);
const s2_intraday = land_points_onto_series(dailyData.time, s2_daily, time);
const r1_intraday = land_points_onto_series(dailyData.time, r1_daily, time);
const r2_intraday = land_points_onto_series(dailyData.time, r2_daily, time);

// Paint the support and resistance levels across the intraday chart
paint(interpolate_sparse_series(s1_intraday, 'constant'), { name: 'S1', color: '#38751d', thickness: 2 });
paint(interpolate_sparse_series(s2_intraday, 'constant'), { name: 'S2', color: '#5d9445', thickness: 2 });
paint(interpolate_sparse_series(r1_intraday, 'constant'), { name: 'R1', color: '#982414', thickness: 2 });
paint(interpolate_sparse_series(r2_intraday, 'constant'), { name: 'R2', color: '#cb5949', thickness: 2 });
</code>