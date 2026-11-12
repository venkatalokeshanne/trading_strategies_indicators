<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Sector Rotation Chart v6', 'price');

const VERBOSE_INPUT_OPTIONS = { hide_in_legend: true };

const tinycolor = library('tinycolor2');

//	applies an alpha to any user-picked color (hex or named)
const withAlpha = (color, alpha) => tinycolor(color).setAlpha(alpha).toRgbString();

const enableSector1 = input.boolean('Show 1', true, VERBOSE_INPUT_OPTIONS);
const mySector1 = input.symbol('Symbol 1', 'XLE', VERBOSE_INPUT_OPTIONS);
const myColor1 = input.color('Color 1', '#FF5722', VERBOSE_INPUT_OPTIONS);
const enableSector2 = input.boolean('Show 2', true, VERBOSE_INPUT_OPTIONS);
const mySector2 = input.symbol('Symbol 2', 'XLB', VERBOSE_INPUT_OPTIONS);
const myColor2 = input.color('Color 2', '#795548', VERBOSE_INPUT_OPTIONS);
const enableSector3 = input.boolean('Show 3', true, VERBOSE_INPUT_OPTIONS);
const mySector3 = input.symbol('Symbol 3', 'XLI', VERBOSE_INPUT_OPTIONS);
const myColor3 = input.color('Color 3', '#607D8B', VERBOSE_INPUT_OPTIONS);
const enableSector4 = input.boolean('Show 4', true, VERBOSE_INPUT_OPTIONS);
const mySector4 = input.symbol('Symbol 4', 'XLY', VERBOSE_INPUT_OPTIONS);
const myColor4 = input.color('Color 4', '#FFA500', VERBOSE_INPUT_OPTIONS);
const enableSector5 = input.boolean('Show 5', false, VERBOSE_INPUT_OPTIONS);
const mySector5 = input.symbol('Symbol 5', 'XLP', VERBOSE_INPUT_OPTIONS);
const myColor5 = input.color('Color 5', '#28A745', VERBOSE_INPUT_OPTIONS);
const enableSector6 = input.boolean('Show 6', true, VERBOSE_INPUT_OPTIONS);
const mySector6 = input.symbol('Symbol 6', 'XLV', VERBOSE_INPUT_OPTIONS);
const myColor6 = input.color('Color 6', '#DC3545', VERBOSE_INPUT_OPTIONS);
const enableSector7 = input.boolean('Show 7', true, VERBOSE_INPUT_OPTIONS);
const mySector7 = input.symbol('Symbol 7', 'XLF', VERBOSE_INPUT_OPTIONS);
const myColor7 = input.color('Color 7', '#1E90FF', VERBOSE_INPUT_OPTIONS);
const enableSector8 = input.boolean('Show 8', true, VERBOSE_INPUT_OPTIONS);
const mySector8 = input.symbol('Symbol 8', 'XLK', VERBOSE_INPUT_OPTIONS);
const myColor8 = input.color('Color 8', '#00BCD4', VERBOSE_INPUT_OPTIONS);
const enableSector9 = input.boolean('Show 9', false, VERBOSE_INPUT_OPTIONS);
const mySector9 = input.symbol('Symbol 9', 'XLC', VERBOSE_INPUT_OPTIONS);
const myColor9 = input.color('Color 9', '#9C27B0', VERBOSE_INPUT_OPTIONS);
const enableSector10 = input.boolean('Show 10', false, VERBOSE_INPUT_OPTIONS);
const mySector10 = input.symbol('Symbol 10', 'XLU', VERBOSE_INPUT_OPTIONS);
const myColor10 = input.color('Color 10', '#6366F1', VERBOSE_INPUT_OPTIONS);
const enableSector11 = input.boolean('Show 11', false, VERBOSE_INPUT_OPTIONS);
const mySector11 = input.symbol('Symbol 11', 'XLRE', VERBOSE_INPUT_OPTIONS);
const myColor11 = input.color('Color 11', '#009688', VERBOSE_INPUT_OPTIONS);
const myBenchmark = input.symbol('Benchmark', 'VTI');

const myCalcTimeframe = input.select('Timeframe', 'Weekly', ['Weekly', 'Monthly']);
const myHistoryLength = input.number('Tail length', 5, { min: 2, max: 100 });
const mySolidBackground = input.boolean('Solid background', true);

//	octant slice colors: one picker per slice. The picked color drives both
//	the slice's background fill (alpha applied programmatically) and its
//	edge label. Defaults match the original palette.
const myOctantColor1 = input.color('Slice: Strong leader', '#32CD32', VERBOSE_INPUT_OPTIONS);
const myOctantColor2 = input.color('Slice: Accelerating', '#9ACD32', VERBOSE_INPUT_OPTIONS);
const myOctantColor3 = input.color('Slice: Turning up', '#4DD0E1', VERBOSE_INPUT_OPTIONS);
const myOctantColor4 = input.color('Slice: Bottoming', '#AAAAAA', VERBOSE_INPUT_OPTIONS);
const myOctantColor5 = input.color('Slice: Deep laggard', '#DC3545', VERBOSE_INPUT_OPTIONS);
const myOctantColor6 = input.color('Slice: Falling', '#E57373', VERBOSE_INPUT_OPTIONS);
const myOctantColor7 = input.color('Slice: Rolling over', '#FFA726', VERBOSE_INPUT_OPTIONS);
const myOctantColor8 = input.color('Slice: Losing steam', '#AAAAAA', VERBOSE_INPUT_OPTIONS);

const CHART_SIZE_MAP = {
	small: { w: 450, h: 300 },
	medium: { w: 600, h: 400 },
	large: { w: 900, h: 600 },
	xlarge: { w: 1200, h: 800 }
};

const tableDimensions = CHART_SIZE_MAP[input.select('Chart size', 'medium', Object.keys(CHART_SIZE_MAP))];

const SECTORS = [{
	ticker: mySector1,
	color: myColor1,
	enabled: enableSector1
}, {
	ticker: mySector2,
	color: myColor2,
	enabled: enableSector2
}, {
	ticker: mySector3,
	color: myColor3,
	enabled: enableSector3
}, {
	ticker: mySector4,
	color: myColor4,
	enabled: enableSector4
}, {
	ticker: mySector5,
	color: myColor5,
	enabled: enableSector5
}, {
	ticker: mySector6,
	color: myColor6,
	enabled: enableSector6
}, {
	ticker: mySector7,
	color: myColor7,
	enabled: enableSector7
}, {
	ticker: mySector8,
	color: myColor8,
	enabled: enableSector8
}, {
	ticker: mySector9,
	color: myColor9,
	enabled: enableSector9
}, {
	ticker: mySector10,
	color: myColor10,
	enabled: enableSector10
}, {
	ticker: mySector11,
	color: myColor11,
	enabled: enableSector11
}].filter(sector => sector.enabled);

const myDataResolution = myCalcTimeframe === 'Weekly' ? 'W' : 'M';
const allSymbolsToFetch = [myBenchmark, ...SECTORS.map(sector => sector.ticker)];
const allDataPromises = allSymbolsToFetch.map(ticker => request.history(ticker, myDataResolution));

let allDataResults;

try {
	allDataResults = await Promise.all(allDataPromises);
}
catch (exception) {
	throw "Failed to fetch historical data. This may be due to an invalid ticker symbol or network issue.";
}

const benchmarkData = allDataResults[0];
assert(!benchmarkData.error, `Error fetching ${myBenchmark} data: ${benchmarkData.error}`);

const computeChangePercentValue = (dataSeries, value, dummy, index) => index < myHistoryLength
	? null
	: (value - dataSeries[index - myHistoryLength]) / dataSeries[index - myHistoryLength];

const benchmarkChange = for_every(benchmarkData.close, computeChangePercentValue.bind(null, benchmarkData.close));

const sectorRSData = [];
const sectorRSMomentumData = [];
const sectorVolumeData = [];

for (let i = 0; i < SECTORS.length; i++) {
	const sector = SECTORS[i];
	const thisDataSeries = allDataResults[i + 1];

	const sectorPrice = land_points_onto_series(thisDataSeries.time, thisDataSeries.close, benchmarkData.time);

	const volumeTail = thisDataSeries.volume.slice(-(myHistoryLength + 1));

	const maxSectorVolume = Math.max(...volumeTail);
	const minSectorVolume = Math.min(...volumeTail);
	const sectorVolumeRange = Math.max(1, maxSectorVolume - minSectorVolume);

	const sectorVolume = volumeTail.map(value => (value - minSectorVolume) / sectorVolumeRange);
	const sectorPriceChange = for_every(sectorPrice, computeChangePercentValue.bind(null, sectorPrice));

	const EPSILON = 1;

	const myRelativeStrength = for_every(sectorPriceChange, benchmarkChange, (_sectorChange, _benchmarkChange) => {
		if (_sectorChange === null || _benchmarkChange === null) {
			return null;
		}

		return (_sectorChange + EPSILON) / (_benchmarkChange + EPSILON);
	});

	const myRSMomentum = for_every(myRelativeStrength, (_currentRS, _prevOutput, _index) => {
		if (_index < 1 || _currentRS === null) {
			return null;
		}

		const previousRS = myRelativeStrength[_index - 1];

		if (previousRS === null || previousRS === 0) {
			return null;
		}

		return (_currentRS / previousRS) * 100;
	});

	sectorRSData.push(myRelativeStrength.slice(-myHistoryLength));
	sectorRSMomentumData.push(myRSMomentum.slice(-myHistoryLength));
	sectorVolumeData.push(sectorVolume);
}

//	========================================================================
//	SPIRAL TRANSFORM
//	Each (RS, momentum) observation collapses to a phase angle around the
//	(100, 100) center: theta = atan2(momentum - 100, RS - 100).
//	Angles are UNWRAPPED across time (each step adjusted by +/-360 to take
//	the smallest move) so direction and turn count survive the 0/360 seam.
//	Radius encodes TIME: oldest observation near the center, newest at the
//	rim. A path can never overlap itself. Clockwise winding = forward
//	rotation (Outperforming -> Degrading -> ...), a switchback = reversal.
//	========================================================================

const CX = 100;
const CY = 100;
const HALF_RANGE = 10;		// data-units from center to rim, both axes
const AXIS_PAD = 1.05;		// extra room outside the rim for labels
const INNER_RADIUS_FRAC = 0.18;	// radius fraction of the oldest point

//	the canvas is wider than tall; widening ONLY the x-axis range by the
//	aspect ratio makes pixels-per-unit equal on both axes, so rings render
//	as true circles and angles are undistorted
const ASPECT = tableDimensions.w / tableDimensions.h;

const minX = CX - HALF_RANGE * AXIS_PAD * ASPECT;
const maxX = CX + HALF_RANGE * AXIS_PAD * ASPECT;
const minY = CY - HALF_RANGE * AXIS_PAD;
const maxY = CY + HALF_RANGE * AXIS_PAD;

const DEG = Math.PI / 180;

//	polar (degrees, radius fraction 0..1) -> chart data-space, OCTAGON
//	geometry. The rim is a regular octagon with vertices at the slice
//	boundaries (0/45/90/...), so each octant's rim is one flat edge.
//	Distance to the rim along a ray = apothem / cos(offset from the edge
//	center); frac = 1 lands exactly on the octagon in every direction.
const OCT_APOTHEM = Math.cos(22.5 * DEG);

const polarToXY = (angleDeg, radiusFrac) => {
	const norm = ((angleDeg % 360) + 360) % 360;
	const offsetFromEdgeCenter = norm - (Math.floor(norm / 45) * 45 + 22.5);
	const t = radiusFrac * HALF_RANGE * OCT_APOTHEM / Math.cos(offsetFromEdgeCenter * DEG);

	return {
		x: CX + t * Math.cos(angleDeg * DEG),
		y: CY + t * Math.sin(angleDeg * DEG)
	};
};

//	smallest signed angular difference, result in (-180, 180]
const wrapDelta = (delta) => ((delta % 360) + 540) % 360 - 180;

const radiusAt = (stepIndex, totalSteps) => totalSteps <= 1
	? 1
	: INNER_RADIUS_FRAC + (1 - INNER_RADIUS_FRAC) * (stepIndex / (totalSteps - 1));

//	screen-space rotation (degrees, clockwise, 0 = pointing up) for a
//	Chart.js triangle pointStyle so it points along the path tangent.
//	Accounts for unequal axis ranges, unequal pixel dimensions, and the
//	flipped screen y axis.
const screenRotation = (fromPt, toPt) => {
	const dxScreen = (toPt.x - fromPt.x) / (maxX - minX) * tableDimensions.w;
	const dyScreen = -(toPt.y - fromPt.y) / (maxY - minY) * tableDimensions.h;

	return Math.atan2(dyScreen, dxScreen) / DEG + 90;
};

const MIN_DOT_SIZE = 0.5;
const MAX_DOT_SIZE = 6;
const INTERP_DEGREES_PER_DOT = 2;	// path dot density along the angular sweep
const MIN_DOTS_PER_SEGMENT = 10;

const chartDatasets = [];
const labelAnnotations = {};
const placedLabels = [];

for (let i = 0; i < SECTORS.length; i++) {
	const sectorTicker = SECTORS[i].ticker;
	const sectorColor = SECTORS[i].color;

	//	pair up RS and momentum, dropping leading nulls but preserving
	//	the volume index alignment via the original step index
	const observations = [];

	for (let candleIdx = 0; candleIdx < sectorRSData[i].length; candleIdx++) {
		const rsValue = sectorRSData[i][candleIdx];
		const momentumValue = sectorRSMomentumData[i][candleIdx];

		if (rsValue === null || momentumValue === null || !isFinite(rsValue) || !isFinite(momentumValue)) {
			continue;
		}

		observations.push({
			rawAngle: Math.atan2(momentumValue - 100, rsValue * 100 - 100) / DEG,
			volume: sectorVolumeData[i][candleIdx] ?? 0
		});
	}

	if (observations.length < 2) {
		continue;
	}

	//	unwrap
	const angles = [observations[0].rawAngle];

	for (let k = 1; k < observations.length; k++) {
		angles.push(angles[k - 1] + wrapDelta(observations[k].rawAngle - angles[k - 1]));
	}

	const totalSteps = angles.length;

	//	interpolated spiral path: dots only, volume-sized, linear in
	//	unwrapped angle and in radius within each segment
	const interpData = [];
	const interpRadii = [];
	const arrowData = [];
	const arrowRotations = [];

	for (let k = 0; k < totalSteps - 1; k++) {
		const angleSpan = Math.abs(angles[k + 1] - angles[k]);
		const steps = Math.max(MIN_DOTS_PER_SEGMENT, Math.round(angleSpan / INTERP_DEGREES_PER_DOT));

		const vol1 = observations[k].volume;
		const vol2 = observations[k + 1].volume;

		for (let s = 0; s < steps; s++) {
			const t = s / steps;
			const angle = angles[k] + (angles[k + 1] - angles[k]) * t;
			const radius = radiusAt(k + t, totalSteps);

			interpData.push(polarToXY(angle, radius));

			const vol = vol1 + (vol2 - vol1) * t;
			interpRadii.push(MIN_DOT_SIZE + vol * (MAX_DOT_SIZE - MIN_DOT_SIZE));
		}

		//	one direction arrow per segment, at the segment midpoint,
		//	rotated to the local tangent of the interpolated path
		const midAngle = angles[k] + (angles[k + 1] - angles[k]) * 0.5;
		const midRadius = radiusAt(k + 0.5, totalSteps);
		const tangentStep = 0.02;
		const tangentAngle = angles[k] + (angles[k + 1] - angles[k]) * (0.5 + tangentStep);
		const tangentRadius = radiusAt(k + 0.5 + tangentStep, totalSteps);

		const midPoint = polarToXY(midAngle, midRadius);
		const aheadPoint = polarToXY(tangentAngle, tangentRadius);

		arrowData.push(midPoint);
		arrowRotations.push(screenRotation(midPoint, aheadPoint));
	}

	chartDatasets.push({
		label: `${sectorTicker}_interp`,
		data: interpData,
		showLine: false,
		borderWidth: 0,
		backgroundColor: withAlpha(sectorColor, 0.7),
		borderColor: withAlpha(sectorColor, 0.7),
		pointRadius: interpRadii,
		pointStyle: 'circle'
	});

	chartDatasets.push({
		label: `${sectorTicker}_arrows`,
		data: arrowData,
		showLine: false,
		borderWidth: 0,
		backgroundColor: sectorColor,
		borderColor: sectorColor,
		pointRadius: 5,
		pointStyle: 'triangle',
		rotation: arrowRotations
	});

	//	observation markers: small dots, larger dot at "now" (the rim)
	const markerData = angles.map((angle, k) => polarToXY(angle, radiusAt(k, totalSteps)));

	chartDatasets.push({
		label: sectorTicker,
		data: markerData,
		showLine: false,
		borderWidth: 0,
		backgroundColor: sectorColor,
		borderColor: sectorColor,
		pointRadius: markerData.map((_, pointIndex) => pointIndex === totalSteps - 1 ? 5 : 2),
		pointStyle: 'circle'
	});

	const lastPoint = markerData[totalSteps - 1];
	const netRotation = Math.round(angles[totalSteps - 1] - angles[0]);

	//	collision avoidance: stack clustered labels away from the point in
	//	14px steps; labels flip BELOW the point when the endpoint is near
	//	the top edge so they don't clip the tighter frame
	const LABEL_X_CLEARANCE = 2.4;	// data units
	const LABEL_Y_CLEARANCE = 0.9;	// data units
	const LABEL_STACK_PX = 14;

	const nearTop = lastPoint.y > CY + 0.8 * HALF_RANGE;
	const stackDir = nearTop ? 1 : -1;

	let yAdjust = 10 * stackDir;
	let collided = true;
	let guard = 0;

	while (collided && guard < 12) {
		collided = placedLabels.some(placed =>
			Math.abs(lastPoint.x - placed.x) < LABEL_X_CLEARANCE &&
			Math.abs(lastPoint.y - placed.y) < LABEL_Y_CLEARANCE &&
			Math.abs(yAdjust - placed.yAdjust) < LABEL_STACK_PX
		);

		if (collided) {
			yAdjust += LABEL_STACK_PX * stackDir;
		}

		guard++;
	}

	placedLabels.push({ x: lastPoint.x, y: lastPoint.y, yAdjust });

	labelAnnotations[`label_${i}`] = {
		type: 'label',
		xValue: lastPoint.x,
		yValue: lastPoint.y,
		content: [`${sectorTicker} ${netRotation > 0 ? '+' : ''}${netRotation}u00B0`],
		color: sectorColor,
		font: { size: 11, weight: 'bold' },
		position: { x: 'center', y: nearTop ? 'bottom' : 'top' },
		textStrokeColor: mySolidBackground ? 'black' : 'var(--background-color)',
		textStrokeWidth: 2,
		xAdjust: 0,
		yAdjust
	};
}

//	time rings: drawn at the SAME radii the data points use (radiusAt), so
//	rings are evenly spaced and labels land exactly on observation circles.
//	For long tails, periods are subsampled evenly to at most MAX_RINGS.
const ringAnnotations = {};
const MAX_RINGS = 8;
const totalPeriods = myHistoryLength;
const ringCount = Math.min(totalPeriods - 1, MAX_RINGS);

for (let ringIdx = 1; ringIdx <= ringCount; ringIdx++) {
	//	fractional period position -> perfectly uniform ring gaps at any
	//	tail length; exact data radii whenever (tail - 1) <= MAX_RINGS
	const periodPos = ringIdx * (totalPeriods - 1) / ringCount;
	const frac = radiusAt(periodPos, totalPeriods);
	const rx = frac * HALF_RANGE;
	const ry = frac * HALF_RANGE;

	const periodsBack = Math.round((totalPeriods - 1) - periodPos);
	const isNowRing = periodsBack === 0;

	//	recency ramp: oldest rings dim, newest bright, "now" highlighted
	const recency = ringIdx / ringCount;
	const ringColor = isNowRing
		? 'rgba(255, 255, 255, 0.7)'
		: `rgba(160, 160, 160, ${(0.15 + 0.35 * recency).toFixed(2)})`;

	//	octagon ring outline as a line dataset: 9 points through the
	//	vertices (slice boundaries), exact in data space. order 98 puts
	//	rings above the wedge fills (99) and below all sector data (0).
	const ringPts = [];

	for (let v = 0; v <= 8; v++) {
		ringPts.push(polarToXY(v * 45, frac));
	}

	chartDatasets.push({
		label: `_ring_${ringIdx}`,
		data: ringPts,
		showLine: true,
		fill: false,
		borderColor: ringColor,
		borderWidth: isNowRing ? 1.5 : 1,
		pointRadius: 0,
		pointHitRadius: 0,
		tension: 0,
		order: 98
	});

	ringAnnotations[`ring_${ringIdx}_label`] = {
		type: 'label',
		xValue: CX,
		yValue: CY + frac * HALF_RANGE,
		content: [isNowRing ? 'now' : `-${periodsBack}`],
		color: isNowRing ? 'rgba(255, 255, 255, 0.8)' : `rgba(170, 170, 170, ${(0.3 + 0.4 * recency).toFixed(2)})`,
		font: { size: 9 },
		position: { x: 'center', y: 'start' },
		drawTime: 'beforeDatasetsDraw'
	};
}

//	========================================================================
//	OCTANT SLICES
//	The chart is cut into 8 pizza slices. The main crosshair (RS and
//	momentum axes) stays prominent; the 45-degree diagonals are fainter.
//	Each slice is labeled just outside the midpoint of its octagon edge.
//	Slice colors are user inputs: the picked color drives the label at
//	full opacity and the background fill at the slice's fixed alpha.
//	========================================================================

const OCTANTS = [
	{ centerAngle: 22.5,  label: 'Strong leader', color: myOctantColor1, fillAlpha: 0.10 },
	{ centerAngle: 67.5,  label: 'Accelerating',  color: myOctantColor2, fillAlpha: 0.07 },
	{ centerAngle: 112.5, label: 'Turning up',    color: myOctantColor3, fillAlpha: 0.07 },
	{ centerAngle: 157.5, label: 'Bottoming',     color: myOctantColor4, fillAlpha: 0.05 },
	{ centerAngle: 202.5, label: 'Deep laggard',  color: myOctantColor5, fillAlpha: 0.10 },
	{ centerAngle: 247.5, label: 'Falling',       color: myOctantColor6, fillAlpha: 0.07 },
	{ centerAngle: 292.5, label: 'Rolling over',  color: myOctantColor7, fillAlpha: 0.07 },
	{ centerAngle: 337.5, label: 'Losing steam',  color: myOctantColor8, fillAlpha: 0.05 }
];

const octantAnnotations = {};

//	diagonal slice boundaries (the 0/90/180/270 boundaries are the
//	existing crosshair lines)
[45, 135, 225, 315].forEach((boundaryAngle, idx) => {
	const edge = polarToXY(boundaryAngle, 1);

	octantAnnotations[`octantBoundary_${idx}`] = {
		type: 'line',
		xMin: CX,
		xMax: edge.x,
		yMin: CY,
		yMax: edge.y,
		borderColor: 'rgba(128, 128, 128, 0.25)',
		borderWidth: 1,
		borderDash: [4, 4],
		drawTime: 'beforeDatasetsDraw'
	};
});

OCTANTS.forEach((octant, idx) => {
	//	label just outside the midpoint of this slice's octagon edge
	const labelPoint = polarToXY(octant.centerAngle, 1.1);

	octantAnnotations[`octantLabel_${idx}`] = {
		type: 'label',
		xValue: labelPoint.x,
		yValue: labelPoint.y,
		position: { x: 'center', y: 'center' },
		content: [octant.label],
		color: octant.color,
		font: { size: 12, weight: 'bold' },
		padding: 5
	};

	//	pizza-slice background fill: a closed line dataset tracing
	//	center -> rim arc -> center, filled by the Filler plugin.
	//	order: 99 + appended last = drawn behind all sector datasets.
	const wedgeData = [{ x: CX, y: CY }];
	const startAngle = octant.centerAngle - 22.5;
	const ARC_STEP_DEG = 3;

	for (let a = 0; a <= 45; a += ARC_STEP_DEG) {
		wedgeData.push(polarToXY(startAngle + a, 1));
	}

	wedgeData.push({ x: CX, y: CY });

	chartDatasets.push({
		label: `_octant_fill_${idx}`,
		data: wedgeData,
		showLine: true,
		fill: 'shape',
		backgroundColor: withAlpha(octant.color, octant.fillAlpha),
		borderWidth: 0,
		borderColor: 'transparent',
		pointRadius: 0,
		pointHitRadius: 0,
		tension: 0,
		order: 99
	});
});

paint_overlay('Chart', {
	position: 'bottom_left',
	offset_x: 0,
	offset_y: 0,
	order: 'above_all'
}, {
	rows: [{
		cells: [{
			chart: {
				width: `${tableDimensions.w}px`,
				height: `${tableDimensions.h}px`,
				type: 'scatter',
				options: {
					showLine: false,
					scales: {
						x: {
							type: 'linear',
							min: minX,
							max: maxX,
							ticks: { display: false },
							title: { display: false },
							border: { display: false },
							grid: { display: false }
						},
						y: {
							type: 'linear',
							min: minY,
							max: maxY,
							ticks: { display: false },
							title: { display: false },
							border: { display: false },
							grid: { display: false }
						}
					},
					plugins: {
						legend: { display: false },
						annotation: {
							annotations: {
								...(mySolidBackground ? {
									chartBackground: {
										type: 'box',
										xMin: minX,
										xMax: maxX,
										yMin: minY,
										yMax: maxY,
										backgroundColor: 'rgba(0, 0, 0, 0.92)',
										borderWidth: 0,
										drawTime: 'beforeDraw'
									}
								} : {}),
								...ringAnnotations,
								verticalLine: {
									type: 'line',
									xMin: CX,
									xMax: CX,
									yMin: CY - HALF_RANGE,
									yMax: CY + HALF_RANGE,
									borderColor: 'rgba(128, 128, 128, 0.5)',
									borderWidth: 2,
									borderDash: [5, 5],
									drawTime: 'beforeDatasetsDraw'
								},
								horizontalLine: {
									type: 'line',
									yMin: CY,
									yMax: CY,
									xMin: CX - HALF_RANGE,
									xMax: CX + HALF_RANGE,
									borderColor: 'rgba(128, 128, 128, 0.5)',
									borderWidth: 2,
									borderDash: [5, 5],
									drawTime: 'beforeDatasetsDraw'
								},
								...octantAnnotations,
								...labelAnnotations
							}
						}
					}
				},
				data: {
					datasets: chartDatasets
				}
			}
		}]
	}]
});</code>