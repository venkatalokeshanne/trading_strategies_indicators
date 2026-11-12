<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator("Volume & Trend Confluence");

// Input parameters
const obvTrendPeriod = input.number("OBV Trend Period", 14, { min: 1 });
const smaPeriod = input.number("Price MA Period", 50, { min: 1 });
const maType = input.select("MA Type", "sma", constants.ma_types);
const bullishColor = input.color("Bullish Color", "green");
const bearishColor = input.color("Bearish Color", "red");
const neutralColor = input.color("Neutral Color", "gray");

// Calculate On-Balance Volume (OBV)
const myObv = for_every(close, volume, (c, v, prevObv, i) => {
    if (i === 0) return v;
    return c > close[i - 1] ? prevObv + v : (c < close[i - 1] ? prevObv - v : prevObv);
});

// Calculate OBV trend using selected MA type
const myObvTrend = indicators[maType](myObv, obvTrendPeriod);

// Calculate price MA using selected MA type
const myPriceMa = indicators[maType](close, smaPeriod);

// Determine signals
const mySignal = for_every(close, myObv, myObvTrend, myPriceMa, (c, obv, obvTrend, priceMa, prevSignal, i) => {
    if (i === 0) return 0; // Neutral for the first candle
    const obvTrendUp = obv > obvTrend;
    const priceAboveMa = c > priceMa;
    if (obvTrendUp && priceAboveMa) {
        return 1; // Bullish
    } else if (!obvTrendUp && !priceAboveMa) {
        return -1; // Bearish
    } else {
        return 0; // Neutral
    }
});

// Paint candles
const myCandleColors = for_every(mySignal, s => {
    if (s === 1) return bullishColor;
    if (s === -1) return bearishColor;
    return neutralColor;
});

color_candles(myCandleColors);

// Display price MA
paint(myPriceMa, { color: "blue", name: `${smaPeriod} ${maType.toUpperCase()}` });

// Register signals for alerts and strategies
register_signal(for_every(mySignal, s => s === 1), "Bullish Signal");
register_signal(for_every(mySignal, s => s === -1), "Bearish Signal");</code>