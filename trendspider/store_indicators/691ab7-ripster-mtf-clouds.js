<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Ripster MTF Clouds', 'price', { mainColorInheritFrom: '#000000' });

// Inputs for the lower timeframe EMA Cloud
const lowerTimeFrame = input.select('Lower Timeframe', '60', constants.time_frames);
const lowerShortLength = input.number('Cloud 1 Short', 34, { min: 1, max: 200, hide_in_legend: true });
const lowerLongLength = input.number('Cloud 1 Long', 50, { min: 1, max: 200, hide_in_legend: true });
const showLowerCloud = input.boolean('Show Cloud 1', true);

// Inputs for the higher timeframe EMA Cloud
const higherTimeFrame = input.select('Higher Timeframe', 'D', constants.time_frames);
const higherShortLength = input.number('Cloud 2 Short', 20, { min: 1, max: 200, hide_in_legend: true });
const higherLongLength = input.number('Cloud 2 Long', 21, { min: 1, max: 200, hide_in_legend: true });
const showHigherCloud = input.boolean('Show Cloud 2', true);

// Inputs for the third timeframe EMA Cloud
const thirdTimeFrame = input.select('Third Timeframe', 'D', constants.time_frames);
const thirdShortLength = input.number('Cloud 3 Short', 50, { min: 1, max: 200, hide_in_legend: true });
const thirdLongLength = input.number('Cloud 3 Long', 55, { min: 1, max: 200, hide_in_legend: true });
const showThirdCloud = input.boolean('Show Cloud 3', true);

// Inputs for the fourth timeframe EMA Cloud
const fourthTimeFrame = input.select('Fourth Timeframe', 'W', constants.time_frames);
const fourthShortLength = input.number('Cloud 4 Short', 8, { min: 1, max: 200, hide_in_legend: true });
const fourthLongLength = input.number('Cloud 4 Long', 9, { min: 1, max: 200, hide_in_legend: true });
const showFourthCloud = input.boolean('Show Cloud 4', false);

// Inputs for the fifth timeframe EMA Cloud
const fifthTimeFrame = input.select('Fifth Timeframe', 'W', constants.time_frames);
const fifthShortLength = input.number('Cloud 5 Short', 20, { min: 1, max: 200, hide_in_legend: true });
const fifthLongLength = input.number('Cloud 5 Long', 21, { min: 1, max: 200, hide_in_legend: true });
const showFifthCloud = input.boolean('Show Cloud 5', false);

// Allow user to select the moving average type
const maType = input.select('MA Type', 'ema', ['ema', 'sma', 'wma', 'vwma']);

// Allow user to toggle inclusion of extended hours
const includeExtHours = input.boolean('Include Extended Hours', true);

// Fetch data for all five timeframe clouds with session control
const [lowerTimeFrameData, higherTimeFrameData, thirdTimeFrameData, fourthTimeFrameData, fifthTimeFrameData] = await Promise.all([
	request.history(current.ticker, lowerTimeFrame, { ext_session: includeExtHours }),
	request.history(current.ticker, higherTimeFrame, { ext_session: includeExtHours }),
	request.history(current.ticker, thirdTimeFrame, { ext_session: includeExtHours }),
	request.history(current.ticker, fourthTimeFrame, { ext_session: includeExtHours }),
	request.history(current.ticker, fifthTimeFrame, { ext_session: includeExtHours })
]);

const lowerShortEMA = indicators[maType](lowerTimeFrameData.close, lowerShortLength);
const lowerLongEMA = indicators[maType](lowerTimeFrameData.close, lowerLongLength);
const higherShortEMA = indicators[maType](higherTimeFrameData.close, higherShortLength);
const higherLongEMA = indicators[maType](higherTimeFrameData.close, higherLongLength);
const thirdShortEMA = indicators[maType](thirdTimeFrameData.close, thirdShortLength);
const thirdLongEMA = indicators[maType](thirdTimeFrameData.close, thirdLongLength);
const fourthShortEMA = indicators[maType](fourthTimeFrameData.close, fourthShortLength);
const fourthLongEMA = indicators[maType](fourthTimeFrameData.close, fourthLongLength);
const fifthShortEMA = indicators[maType](fifthTimeFrameData.close, fifthShortLength);
const fifthLongEMA = indicators[maType](fifthTimeFrameData.close, fifthLongLength);

// Land the EMA series onto the current chart timeframe
const landedLowerShortEMA = land_points_onto_series(lowerTimeFrameData.time, lowerShortEMA, time, 'ge');
const landedLowerLongEMA = land_points_onto_series(lowerTimeFrameData.time, lowerLongEMA, time, 'ge');
const landedHigherShortEMA = land_points_onto_series(higherTimeFrameData.time, higherShortEMA, time, 'ge');
const landedHigherLongEMA = land_points_onto_series(higherTimeFrameData.time, higherLongEMA, time, 'ge');
const landedThirdShortEMA = land_points_onto_series(thirdTimeFrameData.time, thirdShortEMA, time, 'ge');
const landedThirdLongEMA = land_points_onto_series(thirdTimeFrameData.time, thirdLongEMA, time, 'ge');
const landedFourthShortEMA = land_points_onto_series(fourthTimeFrameData.time, fourthShortEMA, time, 'ge');
const landedFourthLongEMA = land_points_onto_series(fourthTimeFrameData.time, fourthLongEMA, time, 'ge');
const landedFifthShortEMA = land_points_onto_series(fifthTimeFrameData.time, fifthShortEMA, time, 'ge');
const landedFifthLongEMA = land_points_onto_series(fifthTimeFrameData.time, fifthLongEMA, time, 'ge');

// Interpolate the series to smooth the visual
const interpolatedLowerShortEMA = interpolate_sparse_series(landedLowerShortEMA, 'constant');
const interpolatedLowerLongEMA = interpolate_sparse_series(landedLowerLongEMA, 'constant');
const interpolatedHigherShortEMA = interpolate_sparse_series(landedHigherShortEMA, 'constant');
const interpolatedHigherLongEMA = interpolate_sparse_series(landedHigherLongEMA, 'constant');
const interpolatedThirdShortEMA = interpolate_sparse_series(landedThirdShortEMA, 'constant');
const interpolatedThirdLongEMA = interpolate_sparse_series(landedThirdLongEMA, 'constant');
const interpolatedFourthShortEMA = interpolate_sparse_series(landedFourthShortEMA, 'constant');
const interpolatedFourthLongEMA = interpolate_sparse_series(landedFourthLongEMA, 'constant');
const interpolatedFifthShortEMA = interpolate_sparse_series(landedFifthShortEMA, 'constant');
const interpolatedFifthLongEMA = interpolate_sparse_series(landedFifthLongEMA, 'constant');

// Paint the EMA clouds (always paint, but use null series when toggled off)
color_cloud(
	showLowerCloud ? interpolatedLowerShortEMA : series_of(null),
	showLowerCloud ? interpolatedLowerLongEMA : series_of(null),
	'rgba(0,255,0,0.5)',
	'rgba(255,0,0,0.5)'
);

color_cloud(
	showHigherCloud ? interpolatedHigherShortEMA : series_of(null),
	showHigherCloud ? interpolatedHigherLongEMA : series_of(null),
	'rgba(0,0,255,0.5)',
	'rgba(255,165,0,0.5)'
);

color_cloud(
	showThirdCloud ? interpolatedThirdShortEMA : series_of(null),
	showThirdCloud ? interpolatedThirdLongEMA : series_of(null),
	'rgba(218,165,32,0.5)',
	'rgba(128,0,128,0.5)'
);

color_cloud(
	showFourthCloud ? interpolatedFourthShortEMA : series_of(null),
	showFourthCloud ? interpolatedFourthLongEMA : series_of(null),
	'rgba(0,255,255,0.5)',
	'rgba(255,0,255,0.5)'
);

color_cloud(
	showFifthCloud ? interpolatedFifthShortEMA : series_of(null),
	showFifthCloud ? interpolatedFifthLongEMA : series_of(null),
	'rgba(255,255,0,0.5)',
	'rgba(0,128,128,0.5)'
);

// Paint the lines
const lowerLineColor = for_every(interpolatedLowerShortEMA, interpolatedLowerLongEMA, (s, l) => s > l ? 'rgba(0,255,0,0.5)' : 'rgba(255,0,0,0.5)');
paint(showLowerCloud ? interpolatedLowerShortEMA : series_of(null), { name: 'Cloud 1 Short', color: lowerLineColor });
paint(showLowerCloud ? interpolatedLowerLongEMA : series_of(null), { name: 'Cloud 1 Long', color: lowerLineColor });

const higherLineColor = for_every(interpolatedHigherShortEMA, interpolatedHigherLongEMA, (s, l) => s > l ? 'rgba(0,0,255,0.5)' : 'rgba(255,165,0,0.5)');
paint(showHigherCloud ? interpolatedHigherShortEMA : series_of(null), { name: 'Cloud 2 Short', color: higherLineColor });
paint(showHigherCloud ? interpolatedHigherLongEMA : series_of(null), { name: 'Cloud 2 Long', color: higherLineColor });

const thirdLineColor = for_every(interpolatedThirdShortEMA, interpolatedThirdLongEMA, (s, l) => s > l ? 'rgba(218,165,32,0.5)' : 'rgba(128,0,128,0.5)');
paint(showThirdCloud ? interpolatedThirdShortEMA : series_of(null), { name: 'Cloud 3 Short', color: thirdLineColor });
paint(showThirdCloud ? interpolatedThirdLongEMA : series_of(null), { name: 'Cloud 3 Long', color: thirdLineColor });

const fourthLineColor = for_every(interpolatedFourthShortEMA, interpolatedFourthLongEMA, (s, l) => s > l ? 'rgba(0,255,255,0.5)' : 'rgba(255,0,255,0.5)');
paint(showFourthCloud ? interpolatedFourthShortEMA : series_of(null), { name: 'Cloud 4 Short', color: fourthLineColor });
paint(showFourthCloud ? interpolatedFourthLongEMA : series_of(null), { name: 'Cloud 4 Long', color: fourthLineColor });

const fifthLineColor = for_every(interpolatedFifthShortEMA, interpolatedFifthLongEMA, (s, l) => s > l ? 'rgba(255,255,0,0.5)' : 'rgba(0,128,128,0.5)');
paint(showFifthCloud ? interpolatedFifthShortEMA : series_of(null), { name: 'Cloud 5 Short', color: fifthLineColor });
paint(showFifthCloud ? interpolatedFifthLongEMA : series_of(null), { name: 'Cloud 5 Long', color: fifthLineColor });</code>