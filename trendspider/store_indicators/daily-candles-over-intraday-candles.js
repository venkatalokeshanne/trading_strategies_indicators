<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Daily candles');

let topGreenLines = series_of(null);
let bottomGreenLines = series_of(null);
let topRedLines = series_of(null);
let bottomRedLines = series_of(null);

function paintCandle(dailyCandle, firstIndex, lastIndex, topLinesStorage, bottomLinesStorage) {
    const bodyTop = Math.max(dailyCandle.open, dailyCandle.close);
    const bodyBottom = Math.min(dailyCandle.open, dailyCandle.close);
    const middleIndex = Math.floor((lastIndex + firstIndex) / 2);

    const bigTopLine = line(firstIndex, bodyTop, lastIndex, bodyTop, false);
    bigTopLine[middleIndex] = dailyCandle.high;
    bigTopLine[middleIndex + 1] = dailyCandle.high;

    const bigBottomLine = line(firstIndex, bodyBottom, lastIndex, bodyBottom, false);
    bigBottomLine[middleIndex] = dailyCandle.low;
    bigBottomLine[middleIndex + 1] = dailyCandle.low;

    for (let candleIndex = firstIndex; candleIndex <= lastIndex; candleIndex += 1) {    
        topLinesStorage[candleIndex] = bigTopLine[candleIndex];
        bottomLinesStorage[candleIndex] = bigBottomLine[candleIndex];
    }
}

let firstIndex = 0;

for (let candleIndex = 1; candleIndex  < close.length; candleIndex++) {
    const sessionChanged = session_of(time[candleIndex]).session !== session_of(time[candleIndex - 1]).session;

    if (!sessionChanged && candleIndex != close.length - 1) {
        continue;
    }

    const lastIndex = candleIndex - 1;

    const dailyCandle = {
        open: open[firstIndex],
        high: Math.max(...high.slice(firstIndex, lastIndex + 1)),
        low: Math.min(...low.slice(firstIndex, lastIndex + 1)),
        close: close[lastIndex]
    };

    if (dailyCandle.close > dailyCandle.open) {
        paintCandle(dailyCandle, firstIndex, lastIndex, topGreenLines, bottomGreenLines);
    } else {
        paintCandle(dailyCandle, firstIndex, lastIndex, topRedLines, bottomRedLines);
    }

    firstIndex = candleIndex;
}

fill(
    paint(topGreenLines, 'Green top', 'green', 'ladder'),
    paint(bottomGreenLines, 'Green bottom', 'green', 'ladder'),
    'green'
);
fill(
    paint(topRedLines, 'Red top', 'red', 'ladder'),
    paint(bottomRedLines, 'Red bottom', 'red', 'ladder'),
    'red'
);</code>