<code x-ref="code" class="hljs" data-clipboard-text>const countries = {
  "Australia": "AUS",
  "Canada": "CAN",
  "China": "CHN",
  "European Union": "EUU",
  "Japan": "JPN",
  "Mexico": "MEX",
  "United Kingdom": "GBR",
  "United States": "USA",
  "World": "WLD"
};
const validIndicatorIds = ["DC.ODA.COMM.CD","DC.ODA.SOCL.CD","DC.ODA.COMM.SA.CD","DC.ODA.TLDC.CD","DC.ODA.SOCL.ZS","DC.ODA.TOTL.CD","DC.ODA.UNTD.CD","DC.ODA.TLDC.GN.ZS","DC.ODA.TOTL.KD","DC.ODA.TOTL.GN.ZS","DC.ODA.UNTD.ZS","NY.AGR.SUBS.GD.ZS","TM.MRC.NOTX.DV.ZS","TM.MRC.NOTX.LD.ZS","TM.TAX.AGRI.CD.LD","TM.TAX.AGRI.CD.DV","TM.TAX.CLTH.CD.DV","TM.TAX.CLTH.CD.LD","TM.TAX.TXTL.CD.DV","TM.TAX.TXTL.CD.LD"];
const data = await request.http(`https://api.worldbank.org/v2/topic/18/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Millennium development goals`, 'lower', { citation: indicatorNote, shortName: `WBI MDGs` });
const country = input.select('Country', 'United States', Object.keys(countries));
const indicatorData = await request.http(`https://api.worldbank.org/v2/country/${countries[country]}/indicator/${indicatorId}?format=json&per_page=20000`);
assert(indicatorData[1] && indicatorData[1].some(d => d.value !== null && d.value !== ''), `The selected indicator doesn't return any data for "${country}".`);
const indicatorTimestamps = indicatorData[1].map(record => {
  const year = parseInt(record.date);
  const milliseconds = Date.UTC(year, 0, 1);
  return milliseconds / 1000;
}).reverse();
const indicatorValues = indicatorData[1].map(record => +record.value || null).reverse();
const lastIndexWithValue = indicatorValues.reduce((a, v, i) => a = v !== null ? i : a, 0);
const isLastValueOlderThanCandles = indicatorTimestamps[lastIndexWithValue] < time[0];
if (isLastValueOlderThanCandles) {
  indicatorTimestamps.push(time[0]);
  indicatorValues.push(indicatorValues[lastIndexWithValue]);
}
const indicatorLine = interpolate_sparse_series(land_points_onto_series(indicatorTimestamps, interpolate_sparse_series(indicatorValues), time, 'ge'), 'constant');
paint(indicatorLine, 'Line', '#469e48');</code>