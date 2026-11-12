<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('True Daily SMA Pack');

const show10  = input.boolean('Show 10 DMA', true);
const show20  = input.boolean('Show 20 DMA', true);
const show50  = input.boolean('Show 50 DMA', true);
const show100 = input.boolean('Show 100 DMA', true);
const show200 = input.boolean('Show 200 DMA', true);

const opacity = input.number('Opacity %', 70, { min: 0, max: 100 });

const color10 = input.color('10 DMA Color', '#00bcd4');
const color20 = input.color('20 DMA Color', '#4caf50');
const color50 = input.color('50 DMA Color', '#2196f3');
const color100 = input.color('100 DMA Color', '#9c27b0');
const color200 = input.color('200 DMA Color', '#e53935');

const dailyData = await request.history(current.ticker, 'D');
assert(!dailyData.error, `Error fetching daily data: ${dailyData.error}`);

function makeDailySma(length) {
  const dailySma = sma(dailyData.close, length);
  const landed = land_points_onto_series(dailyData.time, dailySma, time, 'le');
  return interpolate_sparse_series(landed, 'constant');
}

function rgba(hex, alphaPct) {
  const alpha = alphaPct / 100;
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

const ma10 = show10 ? makeDailySma(10) : series_of(null);
paint(ma10, { name: '10 DMA', color: series_of(rgba(color10, opacity)) });

const ma20 = show20 ? makeDailySma(20) : series_of(null);
paint(ma20, { name: '20 DMA', color: series_of(rgba(color20, opacity)) });

const ma50 = show50 ? makeDailySma(50) : series_of(null);
paint(ma50, { name: '50 DMA', color: series_of(rgba(color50, opacity)) });

const ma100 = show100 ? makeDailySma(100) : series_of(null);
paint(ma100, { name: '100 DMA', color: series_of(rgba(color100, opacity)) });

const ma200 = show200 ? makeDailySma(200) : series_of(null);
paint(ma200, { name: '200 DMA', color: series_of(rgba(color200, opacity)) });
</code>