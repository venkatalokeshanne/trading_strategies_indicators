<code x-ref="code" class="hljs" data-clipboard-text>// This indicator code was generated using AI. It was not checked by Quality Assurance
// and did not pass any quality assurance processes that we normally would use at TrendSpider
// As a result, we can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only.
describe_indicator('Midpoint of Prior Candle', 'price');

// Input for customization
const myPeriodOffset = input.number('Period Offset', 1, { min: 1 });

// Calculate midpoint of prior candle
const myMidpoint = for_every(open, close, (o, c, prev, i) => {
    if (i < myPeriodOffset) return null;
    const priorOpen = open[i - myPeriodOffset];
    const priorClose = close[i - myPeriodOffset];
    return (priorOpen + priorClose) / 2;
});

// Paint the midpoint as a lower indicator
paint(myMidpoint, { 
    name: 'Prior Midpoint', 
    color: 'white', 
    style: 'line' 
});

// Register a signal for use in other TrendSpider features
register_signal(myMidpoint, 'Prior Candle Midpoint');
</code>