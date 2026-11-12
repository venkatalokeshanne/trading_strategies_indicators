<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Multi-Timeframe High/Low Levels');

// Input toggles for each timeframe
const showDaily = input.boolean('Show Daily Levels', true);
const showWeekly = input.boolean('Show Weekly Levels', true);
const showMonthly = input.boolean('Show Monthly Levels', true);
const showYearly = input.boolean('Show Yearly Levels', true);
const show52Week = input.boolean('Show 52 Week Levels', true);

// Function to calculate high and low for a given timeframe
const calculateHighLow = (timeframe) => {
    const myHigh = series_of(null);
    const myLow = series_of(null);
    let lastPeriod = null;
    for (let i = 0; i < time.length; i++) {
        let currentPeriod;
        
        if (timeframe === 'day') {
            currentPeriod = bar_at(time[i]).session;
        } else if (timeframe === 'week') {
            currentPeriod = bar_at(time[i], 'W').session;
        } else if (timeframe === 'month') {
            currentPeriod = bar_at(time[i], 'M').session;
        } else if (timeframe === 'year') {
            currentPeriod = bar_at(time[i], 'Y').session;
        }
        
        if (currentPeriod !== lastPeriod) {
            myHigh[i] = high[i];
            myLow[i] = low[i];
        } else {
            myHigh[i] = Math.max(myHigh[i - 1], high[i]);
            myLow[i] = Math.min(myLow[i - 1], low[i]);
        }
        lastPeriod = currentPeriod;
    }
    return { high: myHigh, low: myLow };
};

// Calculate levels for each timeframe
const dailyLevels = calculateHighLow('day');
const weeklyLevels = calculateHighLow('week');
const monthlyLevels = calculateHighLow('month');
const yearlyLevels = calculateHighLow('year');

// Calculate 52-week high and low
const calculate52WeekLevels = () => {
    const myHigh = series_of(null);
    const myLow = series_of(null);
    const period = 52 * 7 * 24 * 60 * 60; // 52 weeks in seconds
    for (let i = 0; i < time.length; i++) {
        const startTime = time[i] - period;
        let periodHigh = -Infinity;
        let periodLow = Infinity;
        for (let j = Math.max(0, i - 365); j <= i; j++) {
            if (time[j] >= startTime) {
                periodHigh = Math.max(periodHigh, high[j]);
                periodLow = Math.min(periodLow, low[j]);
            }
        }
        myHigh[i] = periodHigh;
        myLow[i] = periodLow;
    }
    return { high: myHigh, low: myLow };
};
const week52Levels = calculate52WeekLevels();

// Paint levels based on user toggles and add labels
if (showDaily) {
    const dailyHighLine = paint(dailyLevels.high, { name: 'Daily High', color: 'lightblue', style: 'ladder' });
    const dailyLowLine = paint(dailyLevels.low, { name: 'Daily Low', color: 'lightblue', style: 'ladder' });
    paint_label_at_line(dailyHighLine, close.length - 1, 'Daily High', { color: 'lightblue' });
    paint_label_at_line(dailyLowLine, close.length - 1, 'Daily Low', { color: 'lightblue' });
}
if (showWeekly) {
    const weeklyHighLine = paint(weeklyLevels.high, { name: 'Weekly High', color: 'blue', style: 'ladder' });
    const weeklyLowLine = paint(weeklyLevels.low, { name: 'Weekly Low', color: 'blue', style: 'ladder' });
    paint_label_at_line(weeklyHighLine, close.length - 1, 'Weekly High', { color: 'blue' });
    paint_label_at_line(weeklyLowLine, close.length - 1, 'Weekly Low', { color: 'blue' });
}
if (showMonthly) {
    const monthlyHighLine = paint(monthlyLevels.high, { name: 'Monthly High', color: 'green', style: 'ladder' });
    const monthlyLowLine = paint(monthlyLevels.low, { name: 'Monthly Low', color: 'green', style: 'ladder' });
    paint_label_at_line(monthlyHighLine, close.length - 1, 'Monthly High', { color: 'green' });
    paint_label_at_line(monthlyLowLine, close.length - 1, 'Monthly Low', { color: 'green' });
}
if (showYearly) {
    const yearlyHighLine = paint(yearlyLevels.high, { name: 'Yearly High', color: 'red', style: 'ladder' });
    const yearlyLowLine = paint(yearlyLevels.low, { name: 'Yearly Low', color: 'red', style: 'ladder' });
    paint_label_at_line(yearlyHighLine, close.length - 1, 'Yearly High', { color: 'red' });
    paint_label_at_line(yearlyLowLine, close.length - 1, 'Yearly Low', { color: 'red' });
}
if (show52Week) {
    const week52HighLine = paint(week52Levels.high, { name: '52 Week High', color: 'purple', style: 'ladder' });
    const week52LowLine = paint(week52Levels.low, { name: '52 Week Low', color: 'purple', style: 'ladder' });
    paint_label_at_line(week52HighLine, close.length - 1, '52 Week High', { color: 'purple' });
    paint_label_at_line(week52LowLine, close.length - 1, '52 Week Low', { color: 'purple' });
}</code>