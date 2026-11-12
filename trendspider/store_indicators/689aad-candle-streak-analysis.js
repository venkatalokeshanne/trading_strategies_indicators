<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Candle Streak Analysis');

const computeStats = () => {
    let totalCandles = close.length;
    let redCandles = 0;
    let greenCandles = 0;
    let currentRedStreak = 0;
    let currentGreenStreak = 0;
    let maxRedStreak = 0;
    let maxGreenStreak = 0;
    let redStreaks = [];
    let greenStreaks = [];
    let redStreakCount = 0;
    let greenStreakCount = 0;

    for (let i = 0; i < totalCandles; i++) {
        if (close[i] < open[i]) {
            redCandles++;
            currentRedStreak++;
            if (currentRedStreak === 2) {
                redStreakCount++;
            }
            if (currentGreenStreak > 1) {
                greenStreaks.push(currentGreenStreak);
            }
            currentGreenStreak = 0;
            maxRedStreak = Math.max(maxRedStreak, currentRedStreak);
        } else if (close[i] > open[i]) {
            greenCandles++;
            currentGreenStreak++;
            if (currentGreenStreak === 2) {
                greenStreakCount++;
            }
            if (currentRedStreak > 1) {
                redStreaks.push(currentRedStreak);
            }
            currentRedStreak = 0;
            maxGreenStreak = Math.max(maxGreenStreak, currentGreenStreak);
        } else {
            if (currentRedStreak > 1) {
                redStreaks.push(currentRedStreak);
            }
            if (currentGreenStreak > 1) {
                greenStreaks.push(currentGreenStreak);
            }
            currentRedStreak = 0;
            currentGreenStreak = 0;
        }
    }

    // Add the last streak if it's more than 1
    if (currentRedStreak > 1) {
        redStreaks.push(currentRedStreak);
    }
    if (currentGreenStreak > 1) {
        greenStreaks.push(currentGreenStreak);
    }

    const redPercent = (redCandles / totalCandles * 100).toFixed(2);
    const greenPercent = (greenCandles / totalCandles * 100).toFixed(2);
    const avgRedStreak = redStreaks.length > 0 ? (redStreaks.reduce((a, b) => a + b, 0) / redStreaks.length).toFixed(2) : '0.00';
    const avgGreenStreak = greenStreaks.length > 0 ? (greenStreaks.reduce((a, b) => a + b, 0) / greenStreaks.length).toFixed(2) : '0.00';

    return {
        totalCandles,
        redPercent,
        greenPercent,
        maxRedStreak,
        maxGreenStreak,
        avgRedStreak,
        avgGreenStreak,
        redStreakCount,
        greenStreakCount
    };
};

const stats = computeStats();

paint_overlay('CandleAnalysis', { position: 'bottom_left', offset_x: 20, offset_y: -50 }, {
    rows: [
        { cells: [{ text: 'Candle Streak Analysis', color: 'var(--text-color)' }] },
        { cells: [{ text: `Total Candles: ${stats.totalCandles}`, color: 'var(--text-color)' }] },
        { cells: [{ text: `Red Candles: ${stats.redPercent}%`, color: 'red' }] },
        { cells: [{ text: `Green Candles: ${stats.greenPercent}%`, color: 'green' }] },
        { cells: [{ text: `Max Red Streak: ${stats.maxRedStreak}`, color: 'red' }] },
        { cells: [{ text: `Max Green Streak: ${stats.maxGreenStreak}`, color: 'green' }] },
        { cells: [{ text: `Red Streaks (>1): ${stats.redStreakCount}`, color: 'red' }] },
        { cells: [{ text: `Green Streaks (>1): ${stats.greenStreakCount}`, color: 'green' }] },
        { cells: [{ text: `Avg Red Streak: ${stats.avgRedStreak}`, color: 'red' }] },
        { cells: [{ text: `Avg Green Streak: ${stats.avgGreenStreak}`, color: 'green' }] }
    ]
});
</code>