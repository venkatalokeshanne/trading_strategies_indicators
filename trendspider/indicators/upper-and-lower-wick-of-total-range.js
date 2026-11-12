<code x-ref="code" class="hljs" data-clipboard-text>// This indicator was made by AI and has not been QA checked by the TrendSpider development team. The indicator is for entertainment purposes only.

describe_indicator('Upper and Lower Wick % of Total Range', 'lower', { shortName: 'CRangeWLLine', decimals: 'by_symbol_2x' });

// ==============================
//        INPUT PARAMETERS
// ==============================

// Input for line thickness
const lineThickness = input.number('Line Thickness', 2, { min: 1, max: 10 });

// ==============================
//          CALCULATIONS
// ==============================

// Calculate the total range (High - Low)
const totalRange = sub(prices.high, prices.low);

// Calculate the upper wick range
const upperWickRange = for_every(prices.high, prices.close, prices.open, (high, close, open) => close > open ? high - close : high - open);

// Calculate the lower wick range
const lowerWickRange = for_every(prices.low, prices.close, prices.open, (low, close, open) => close > open ? open - low : close - low);

// Calculate the upper wick percentage of the total range
const upperWickPercentage = for_every(upperWickRange, totalRange, (upperWick, range) => range > 0 ? (upperWick / range) * 100 : 0);

// Calculate the lower wick percentage of the total range
const lowerWickPercentage = for_every(lowerWickRange, totalRange, (lowerWick, range) => range > 0 ? (lowerWick / range) * 100 : 0);

// ==============================
//           PLOTTING
// ==============================

// Paint the total range as a line
paint(totalRange, {
    name: 'Total Range',
    color: 'yellow', // Black color for total range
    thickness: lineThickness,
    style: 'line'
});

// Paint the upper wick percentage as a histogram
paint(upperWickPercentage, {
    name: 'Upper Wick %',
    color: '#f44336', // Red color for upper wick
    thickness: lineThickness,
    style: 'histogram'
});

// Paint the lower wick percentage as a histogram
paint(lowerWickPercentage, {
    name: 'Lower Wick %',
    color: '#2196f3', // Blue color for lower wick
    thickness: lineThickness,
    style: 'histogram'
});

</code>