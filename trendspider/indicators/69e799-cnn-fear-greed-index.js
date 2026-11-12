<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('CNN Fear & Greed Index', 'lower', { decimals: 0, shortName: 'CNN F&G' });
const ratingColors = {
    'extreme fear': '#cc2222',
    'fear': '#e07020',
    'neutral': '#888888',
    'greed': '#70bb50',
    'extreme greed': '#1a8c3a'
}
// CNN's Fear and Greed API requires specific headers to accept the request.
const myData = await request.http(
    `https://production.dataviz.cnn.io/index/fearandgreed/graphdata`,
    60,
    {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'accept': 'application/json'
    }
);
const fngData = myData.fear_and_greed_historical.data;
const fngTimestamps = fngData.map(d => d.x / 1000);
const fngValues = fngData.map(d => d.y);
const fngRating = fngData.map(d => d.rating);
const landedData = land_points_onto_series(fngTimestamps, fngValues, time, 'ge');
// Assign the latest value to the last candle in order to have values at the end after interpolation
landedData[close.length - 1] = fngValues[fngValues.length - 1];
const mySeriesForPaint = interpolate_sparse_series(landedData);
// Create dynamic color series based on score values
const ratingSeries = interpolate_sparse_series(land_points_onto_series(fngTimestamps, fngRating, time, 'ge'), 'constant');
const myColorSeries = ratingSeries.map(rating => ratingColors[rating]);
// Paint horizontal reference lines at key levels
const bottom = paint(horizontal_line(-50), { hidden: true });
const l25 = paint(horizontal_line(25), { hidden: true });
const l45 = paint(horizontal_line(45), { hidden: true });
const l55 = paint(horizontal_line(55), { hidden: true });
const l75 = paint(horizontal_line(75), { hidden: true });
const top = paint(horizontal_line(150), { hidden: true });
fill(bottom, l25, ratingColors['extreme fear'], 0.2, 'Extreme fear');
fill(l25, l45, ratingColors['fear'], 0.2, 'Fear');
fill(l45, l55, ratingColors['neutral'], 0.2, 'Neutral');
fill(l55, l75, ratingColors['greed'], 0.2, 'Greed');
fill(l75, top, ratingColors['extreme greed'], 0.2, 'Extreme greed');
// Paint the main Fear & Greed line with dynamic colors
const myMainLine = paint(mySeriesForPaint, {
    name: 'Fear & Greed',
    color: myColorSeries,
    thickness: 2,
    style: 'line'
});
const myCurrentScore = myData.fear_and_greed.score;
const myCurrentRating = myData.fear_and_greed.rating;
// Determine background color based on current score
let myLabelBgColor = ratingColors[myCurrentRating];
paint_label_at_line(
    myMainLine,
    close.length - 1,
    `F&G: ${myCurrentScore.toFixed(0)} (${myCurrentRating})`,
    {
        color: 'white',
        background_color: myLabelBgColor,
        border_radius: 3,
        border_width: 1,
        border_color: 'black',
        vertical_align: 'middle'
    }
);</code>