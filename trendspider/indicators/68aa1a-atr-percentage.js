<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('ATR/Price%')
// Define input parameters
var atrPeriod = input("ATR Period", 7);

// Calculate True Range
var trueRange = [];
for (var i = 0; i < close.length; i++) {
    if (i === 0) {
        trueRange[i] = high[i] - low[i];
    } else {
        var highLowRange = high[i] - low[i];
        var highCloseRange = Math.abs(high[i] - close[i-1]);
        var lowCloseRange = Math.abs(low[i] - close[i-1]);
        trueRange[i] = Math.max(highLowRange, highCloseRange, lowCloseRange);
    }
}

// Calculate ATR
var averageTrueRange = sma(trueRange, atrPeriod);

// Calculate ATR as percentage of price
var atrPercentage = [];
for (var i = 0; i < close.length; i++) {
    atrPercentage[i] = (averageTrueRange[i] / close[i]) * 100;
}

// Paint ATR Percentage
paint(atrPercentage, "ATR %", "blue");

// Calculate and paint a 20-period average of ATR Percentage
var avgAtrPercentage = sma(atrPercentage, 20);
paint(avgAtrPercentage, "20-period Avg ATR %", "red");

// Paint a reference line at 0 to force a separate panel
paint(Array(close.length).fill(0), "Reference", "#00000001");

describe_indicator('ATR Percentage', 'lower');</code>