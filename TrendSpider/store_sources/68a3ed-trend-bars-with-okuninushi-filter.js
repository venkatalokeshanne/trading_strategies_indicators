<code x-ref="code" class="hljs" data-clipboard-text>//#TSBuild25
// TrendSpider Indicator: Trend Bars with Okuninushi Line Filter
// Colors candles based on trend bar conditions AND position relative to Okuninushi Line

describe_indicator('Trend Bars with Okuninushi Filter');

// Define adjustable parameters
const trendThreshold = input("trendThreshold", 0.75, {
    title: "Trend Bar Threshold (%)",
    min: 0.1,
    max: 1.0,
    step: 0.05
});

const length = input.number('Length', 52, { min: 1 });

// Calculate Okuninushi Line (without offset)
const highN = highest(high, length);
const lowN  = lowest(low, length);
const okuninushiLine = for_every(highN, lowN, (h, l) => (h + l) / 2);

// Define trend bar conditions with Okuninushi Line filter
const bullTrendBar = for_every(close, open, high, low, okuninushiLine, (c, o, h, l, okuLine) => 
    (c > o) && 
    (Math.abs(c - o) >= trendThreshold * (h - l)) && 
    (c > okuLine) &&  // Close price must be above Okuninushi Line
    !isNaN(okuLine)   // Ensure Okuninushi Line value exists
);

const bearTrendBar = for_every(close, open, high, low, okuninushiLine, (c, o, h, l, okuLine) => 
    (c < o) && 
    (Math.abs(c - o) >= trendThreshold * (h - l)) && 
    (c < okuLine) &&  // Close price must be below Okuninushi Line
    !isNaN(okuLine)   // Ensure Okuninushi Line value exists
);

// Create colors array based on trend bar conditions
const colors = for_every(bullTrendBar, bearTrendBar, (bull, bear) => {
    if (bull) return 'green';
    if (bear) return 'red';
    return 'gray';
});

// Apply colors to candles
color_candles(colors);

// Paint the Okuninushi Line for reference
paint(okuninushiLine, { name: 'Okuninushi Line', color: 'orange', style: 'line' });

//Trend Bars with Okuninushi Line Filter: A Powerful Trading Indicator

//The **Trend Bars with Okuninushi Line Filter** is an innovative technical indicator 
//that combines two powerful concepts: trend bar analysis and the Okuninushi Line filter. 
//This indicator helps traders identify high-quality trending moves by analyzing candle body strength 
//relative to the overall price range while ensuring the price action aligns with the dominant market structure.

//## What Are Trend Bars?

//Trend bars are candles where the body (distance between open and close) 
//represents a significant portion of the total price range (high to low). 
//These bars indicate strong directional momentum with minimal indecision, 
//making them valuable signals for trend continuation.

// Key Characteristics:
//- **Strong directional movement**: Large body relative to total range
//- **Minimal upper/lower shadows**: Shows sustained pressure in one direction
//- **High conviction**: Represents decisive market action

// The Okuninushi Line Filter

//The Okuninushi Line represents the **AB Structure** concept - 
//a 50% equilibrium level of the market's recent range. 
//It's calculated as the midpoint of the highest high and lowest low over the past 52 periods (default setting).

//**Formula**: `(Highest High + Lowest Low) / 2`

//Understanding the AB Structure:
//- **A to B Movement**: Represents the complete range of market movement over the lookback period
//- **50% Equilibrium**: The midpoint represents the balance point between buyers and sellers
//- **Market Dynamics**:
// - **Uptrend scenario**: After a rally, a 50% retracement often finds support at this level
// - **Downtrend scenario**: After a decline, a 50% bounce often faces resistance at this level

// Signal Context and Market Behavior:
//- **Bull Trend Bars above the line**: These typically occur after an upward move, 
//		followed by a retracement that finds acceptance at or above the 50% level, 
//		then continues higher. This represents **retracement acceptance** and **trend continuation**.

//- **Bear Trend Bars below the line**: These typically occur after a downward move, 
//		followed by a bounce that gets rejected at or below the 50% level, then continues lower. 
//		This represents **bounce rejection** and **downtrend continuation**.

//This dynamic makes the indicator particularly valuable for identifying high-probability 
//continuation patterns rather than just random strong candles.

//This line acts as a dynamic support/resistance level and trend filter, helping to:
//- Identify the overall market bias relative to the recent range
//- Filter out counter-trend signals that go against the AB structure
//- Provide confluence for trade entries based on 50% equilibrium concepts

// How the Indicator Works

//The indicator combines these two concepts with the following logic:

// Bull Trend Bars (Green)
//A candle is colored **green** when ALL conditions are met:
//1. **Bullish candle**: Close > Open
//2. **Strong body**: |Close - Open| ≥ Threshold × (High - Low)
//3. **Above trend filter**: Close > Okuninushi Line

// Bear Trend Bars (Red)
//A candle is colored **red** when ALL conditions are met:
//1. **Bearish candle**: Close < Open
//2. **Strong body**: |Close - Open| ≥ Threshold × (High - Low)
//3. **Below trend filter**: Close < Okuninushi Line

// Neutral Bars (Gray)
//All other candles that don't meet the complete criteria are colored **gray**.

// Customizable Parameters

// Trend Bar Threshold
//- **Range**: 10% to 100%
//- **Default**: 75%
//- **Purpose**: Controls how "strong" a candle must be to qualify as a trend bar

//**Threshold Effects:**
//- **Low (10-30%)**: More sensitive, catches smaller trending moves
//- **Medium (50-75%)**: Balanced approach, filters out most noise
//- **High (80-100%)**: Very selective, only captures the strongest moves

// Okuninushi Line Length
//- **Default**: 52 periods
//- **Purpose**: Determines the lookback period for calculating the midpoint
//- **Common Settings**:
//  - 26 periods: More responsive to recent price action
//  - 52 periods: Standard setting, good balance
//  - 104 periods: Longer-term trend perspective

// Trading Applications

// 1. Trend Continuation Signals
//- **Green bars above Okuninushi Line**: High-probability bullish continuation signals, 
//		often appearing after retracements that find acceptance above the 50% level
//- **Red bars below Okuninushi Line**: High-probability bearish continuation signals, 
//		often appearing after bounces that get rejected below the 50% level
//- **Key insight**: These signals represent the market's decision to continue 
//the prevailing trend after testing the equilibrium level

// 2. AB Structure Analysis
//- **Above the line**: Price is in the upper half of the recent range, suggesting bullish bias
//- **Below the line**: Price is in the lower half of the recent range, suggesting bearish bias
//- **Price interaction**: Watch for bounces and rejections at this 50% equilibrium level
//- **Continuation context**: Bull trend bars above the line suggest uptrend continuation after successful retracement acceptance; bear trend bars below the line suggest downtrend continuation after failed bounce attempts

// 3. Market Structure Analysis
//- Clusters of same-colored bars indicate strong trends
//- Alternating colors suggest choppy, indecisive markets
//- Transition from red to green (or vice versa) may signal trend changes

// 4. AB Structure Analysis
//- **Above the line**: Price is in the upper half of the recent range, suggesting bullish bias
//- **Below the line**: Price is in the lower half of the recent range, suggesting bearish bias
//- **Price interaction**: Watch for bounces and rejections at this 50% equilibrium level

// 5. Entry Timing
//- Use colored bars as confirmation for existing trade setups
//- Wait for color alignment with your market bias
//- Avoid trading during predominantly gray periods

// 6. Risk Management
//- Gray bars can serve as early warning signs of weakening trends
//- Color changes might indicate appropriate exit points
//- Use in conjunction with other risk management tools

// Advantages

//1. **Dual Filtering**: Combines momentum (trend bars) with trend direction (Okuninushi Line)
//2. **Visual Clarity**: Immediate visual feedback through candle coloring
//3. **Customizable**: Adjustable parameters for different trading styles
//4. **Versatile**: Works across multiple timeframes and instruments
//5. **Objective**: Rule-based system reduces subjective interpretation

// Best Practices

// Optimization Tips:
//- **Volatile Markets**: Use higher thresholds (80-90%)
//- **Steady Trends**: Use moderate thresholds (60-75%)
//- **Short-term Trading**: Shorter Okuninushi Line periods (26)
//- **Long-term Analysis**: Longer Okuninushi Line periods (104+)

// Combination Strategies:
//- Pair with volume indicators for confirmation
//- Use alongside support/resistance levels
//- Combine with other trend-following indicators
//- Consider market context and overall trend direction
</code>