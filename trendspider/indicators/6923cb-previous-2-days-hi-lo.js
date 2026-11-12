<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Previous 2 Days Hi Lo');

// Request daily data to get high and low from previous days
const dailyData = await request.history(current.ticker, 'D');
assert(!dailyData.error, `Error fetching daily data: ${dailyData.error}`);

// Request weekly data to get high and low from previous week
const weeklyData = await request.history(current.ticker, 'W');
assert(!weeklyData.error, `Error fetching weekly data: ${weeklyData.error}`);

// Get values from 2 days ago (index length-3)
const altaAnteontem = dailyData.high.length >= 3 ? dailyData.high[dailyData.high.length - 3] : null;
const baixaAnteontem = dailyData.low.length >= 3 ? dailyData.low[dailyData.low.length - 3] : null;

// Get values from yesterday (index length-2)
const altaOntem = dailyData.high.length >= 2 ? dailyData.high[dailyData.high.length - 2] : null;
const baixaOntem = dailyData.low.length >= 2 ? dailyData.low[dailyData.low.length - 2] : null;

// Get values from previous week (index length-2)
const baixaSemanaAnterior = weeklyData.low.length >= 2 ? weeklyData.low[weeklyData.low.length - 2] : null;
const altaSemanaAnterior = weeklyData.high.length >= 2 ? weeklyData.high[weeklyData.high.length - 2] : null;

// Paint horizontal lines for each level
paint(horizontal_line(altaAnteontem), { name: 'High 2 Days Ago', color: 'red', style: 'dotted' });
paint(horizontal_line(baixaAnteontem), { name: 'Low 2 Days Ago', color: 'red', style: 'dotted' });
paint(horizontal_line(altaOntem), { name: 'High Yesterday', color: 'yellow', style: 'dotted' });
paint(horizontal_line(baixaOntem), { name: 'Low Yesterday', color: 'yellow', style: 'dotted' });
paint(horizontal_line(baixaSemanaAnterior), { name: 'Low Previous Week', color: 'purple', style: 'line' });
paint(horizontal_line(altaSemanaAnterior), { name: 'High Previous Week', color: 'purple', style: 'line' });</code>