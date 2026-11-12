<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('ALMA');

// User Inputs
const source = input.select('Source', 'close', constants.price_source_options);
const myAlmaLength = input.number('Arnaud Legoux MA Length', 48, { min: 1 });
const myAlmaOffset = input.number('ALMA Offset', 0.15, { min: 0.0001 });
const myAlmaSigma = input.number('ALMA Sigma Value', 6, { min: 1 });

// Constants for ALMA calculation
const myM = myAlmaOffset * (myAlmaLength - 1);
const myS = myAlmaLength / myAlmaSigma;

// ALMA calculation function
const computeALMA = (price, length, m, s) => {
    const myWeightedSum = series_of(0);
    const myWeightSum = series_of(0);
    const myTrendALMA = series_of(null);
    for (let i = length - 1; i < price.length; i++) {
        let weightedSum = 0;
        let weightSum = 0;
        for (let j = 0; j < length; j++) {
            const w = Math.exp(-((j - m) * (j - m)) / (2 * s * s));
            weightedSum += price[i - j] * w;
            weightSum += w;
        }
        myWeightedSum[i] = weightedSum;
        myWeightSum[i] = weightSum;
        myTrendALMA[i] = weightedSum / weightSum;
    }
    return myTrendALMA;
};

const myTrendALMA = computeALMA(market[source], myAlmaLength, myM, myS);

// Color calculations
const myAlmaColor = 'aqua'



// Plotting
paint(myTrendALMA);
// Plotting
paint(myTrendALMA, { color: myAlmaColor, linewidth: 3, name: 'ALMA Line' });
//color_candles(myBarColor);
//color_candles(myBarColor);

// Fixed the fill function to use a single color string

</code>