describe_indicator('Anchored VWAP Sessions', 'price');

// ── General ───────────────────────────────────────────────────────────
const myGeneralTab = input.tab('General');
const myTimezone = myGeneralTab.text('Timezone', 'Etc/GMT-8', { hide_in_legend: true });
const myPriceSource = myGeneralTab.select('Source', 'hlc3', constants.price_source_options);
const myHideOnDWM = myGeneralTab.boolean('Hide on 1D and above', true);

// ── Band ──────────────────────────────────────────────────────────────
const myBandGroup = myGeneralTab.group('Band (Standard Deviation)');
const myShowBand = myBandGroup.boolean('Show band', true);
const myBandMultiplier = myBandGroup.number('Std Dev Multiplier', 1, { min: 0, max: 10, step: 0.5 });

// ── Globex anchor ─────────────────────────────────────────────────────
const myGlobexTab = input.tab('Globex anchor');
const myShowGlobex = myGlobexTab.boolean('Show Globex VWAP', true);
const myGlobexRow = myGlobexTab.row();
const myGlobexHour = myGlobexRow.number('Hour', 6, { min: 0, max: 23 });
const myGlobexMinute = myGlobexRow.number('Minute', 0, { min: 0, max: 59 });

// ── EU Open anchor ───────────────────────────────────────────────────
const myEuTab = input.tab('EU Open anchor');
const myShowEu = myEuTab.boolean('Show EU Open VWAP', true);
const myEuRow = myEuTab.row();
const myEuHour = myEuRow.number('Hour', 14, { min: 0, max: 23 });
const myEuMinute = myEuRow.number('Minute', 0, { min: 0, max: 59 });

// ── US Open anchor ───────────────────────────────────────────────────
const myUsTab = input.tab('US Open anchor');
const myShowUs = myUsTab.boolean('Show US Open VWAP', true);
const myUsRow = myUsTab.row();
const myUsHour = myUsRow.number('Hour', 21, { min: 0, max: 23 });
const myUsMinute = myUsRow.number('Minute', 30, { min: 0, max: 59 });

// moment-timezone is used to resolve the anchor clock time (h:m) in the
// user-specified timezone string into a Unix timestamp, per calendar day.
// Note: "GMT+8" style strings from the Pine script are NOT valid IANA/Etc
// timezone names; the Etc/GMT zones use the REVERSED sign convention
// (Etc/GMT-8 == UTC+8). We default to "Etc/GMT-8" to approximate "GMT+8".
const myMoment = library('moment-timezone');

const myResolutionIsDWM = isNaN(parseInt(current.resolution, 10));
const myHideAll = myHideOnDWM && myResolutionIsDWM;

// Resolves the price source array based on the selected option.
const myPrice = market[myPriceSource];

// Builds the "is this candle the first candle at/after h:m (tz) today" flag.
function myBuildAnchorFlags(_hour, _minute) {
	const myFlags = series_of(false);
	for (let myIndex = 1; myIndex < time.length; myIndex += 1) {
		const myCurrentMoment = myMoment.tz(time[myIndex] * 1000, myTimezone);
		const myAnchorMoment = myCurrentMoment.clone().set({ hour: _hour, minute: _minute, second: 0, millisecond: 0 });
		const myAnchorTimestamp = myAnchorMoment.unix();
		myFlags[myIndex] = (time[myIndex] >= myAnchorTimestamp) && (time[myIndex - 1] < myAnchorTimestamp);
	}
	return myFlags;
}

// Computes the anchored VWAP (and std-dev bands) which resets its
// cumulative sums every time an anchor flag is true.
function myComputeAnchoredVwap(_anchorFlags) {
	const myVwap = series_of(null);
	const myUpper = series_of(null);
	const myLower = series_of(null);

	let myCumPV = 0;
	let myCumV = 0;
	let myCumPV2 = 0;
	let myStarted = false;

	for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
		if (_anchorFlags[myIndex]) {
			myCumPV = 0;
			myCumV = 0;
			myCumPV2 = 0;
			myStarted = true;
		}

		if (!myStarted) {
			continue;
		}

		const myVolumeAtIndex = volume[myIndex] || 0;
		const myPriceAtIndex = myPrice[myIndex];

		myCumPV += myPriceAtIndex * myVolumeAtIndex;
		myCumV += myVolumeAtIndex;
		myCumPV2 += myPriceAtIndex * myPriceAtIndex * myVolumeAtIndex;

		if (myCumV > 0) {
			const myVwapValue = myCumPV / myCumV;
			const myVariance = Math.max(0, (myCumPV2 / myCumV) - (myVwapValue * myVwapValue));
			const myStdev = Math.sqrt(myVariance);

			myVwap[myIndex] = myVwapValue;
			myUpper[myIndex] = myVwapValue + (myBandMultiplier * myStdev);
			myLower[myIndex] = myVwapValue - (myBandMultiplier * myStdev);
		}
	}

	return { vwap: myVwap, upper: myUpper, lower: myLower };
}

const myGlobexAnchors = myBuildAnchorFlags(myGlobexHour, myGlobexMinute);
const myEuAnchors = myBuildAnchorFlags(myEuHour, myEuMinute);
const myUsAnchors = myBuildAnchorFlags(myUsHour, myUsMinute);

const myGlobexVwap = myComputeAnchoredVwap(myGlobexAnchors);
const myEuVwap = myComputeAnchoredVwap(myEuAnchors);
const myUsVwap = myComputeAnchoredVwap(myUsAnchors);

const myShowGlobexFinal = myShowGlobex && !myHideAll;
const myShowEuFinal = myShowEu && !myHideAll;
const myShowUsFinal = myShowUs && !myHideAll;

const myMaskSeries = (_series, _show) => _show ? _series : constants.empty_series;

// ── Globex plots ──────────────────────────────────────────────────────
paint(myMaskSeries(myGlobexVwap.vwap, myShowGlobexFinal), { name: 'Globex VWAP', color: '#F2C40F', thickness: 2 });
const myGlobexUpperPainted = paint(myMaskSeries(myGlobexVwap.upper, myShowGlobexFinal && myShowBand), { name: 'Globex Upper', color: 'rgba(242,196,15,0.4)' });
const myGlobexLowerPainted = paint(myMaskSeries(myGlobexVwap.lower, myShowGlobexFinal && myShowBand), { name: 'Globex Lower', color: 'rgba(242,196,15,0.4)' });
fill(myGlobexUpperPainted, myGlobexLowerPainted, '#F2C40F', 0.08);

// ── EU Open plots ─────────────────────────────────────────────────────
paint(myMaskSeries(myEuVwap.vwap, myShowEuFinal), { name: 'EU VWAP', color: '#D0D0D0', thickness: 2 });
const myEuUpperPainted = paint(myMaskSeries(myEuVwap.upper, myShowEuFinal && myShowBand), { name: 'EU Upper', color: 'rgba(208,208,208,0.4)' });
const myEuLowerPainted = paint(myMaskSeries(myEuVwap.lower, myShowEuFinal && myShowBand), { name: 'EU Lower', color: 'rgba(208,208,208,0.4)' });
fill(myEuUpperPainted, myEuLowerPainted, '#D0D0D0', 0.08);

// ── US Open plots ─────────────────────────────────────────────────────
paint(myMaskSeries(myUsVwap.vwap, myShowUsFinal), { name: 'US VWAP', color: '#E91E63', thickness: 2 });
const myUsUpperPainted = paint(myMaskSeries(myUsVwap.upper, myShowUsFinal && myShowBand), { name: 'US Upper', color: 'rgba(233,30,99,0.4)' });
const myUsLowerPainted = paint(myMaskSeries(myUsVwap.lower, myShowUsFinal && myShowBand), { name: 'US Lower', color: 'rgba(233,30,99,0.4)' });
fill(myUsUpperPainted, myUsLowerPainted, '#E91E63', 0.08);

// ── Signals for scanners/alerts/strategies ───────────────────────────
register_signal(myGlobexAnchors, 'Globex Anchor Fired');
register_signal(myEuAnchors, 'EU Open Anchor Fired');
register_signal(myUsAnchors, 'US Open Anchor Fired');
register_signal(for_every(close, myGlobexVwap.vwap, (_c, _v) => _v !== null && _c > _v), 'Close Above Globex VWAP');
register_signal(for_every(close, myEuVwap.vwap, (_c, _v) => _v !== null && _c > _v), 'Close Above EU VWAP');
register_signal(for_every(close, myUsVwap.vwap, (_c, _v) => _v !== null && _c > _v), 'Close Above US VWAP');