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
const validIndicatorIds = ["AG.LND.EL5M.RU.K2","AG.LND.ARBL.HA.PC","AG.LND.EL5M.RU.ZS","AG.CON.FERT.PT.ZS","AG.LND.AGRI.ZS","AG.CON.FERT.ZS","AG.LND.ARBL.ZS","AG.LND.AGRI.K2","AG.LND.CREL.HA","AG.LND.ARBL.HA","AG.LND.CROP.ZS","AG.LND.FRST.K2","AG.LND.FRST.ZS","AG.LND.PRCP.MM","AG.LND.IRIG.AG.ZS","AG.LND.TOTL.RU.K2","AG.PRD.CREL.MT","AG.LND.TOTL.K2","AG.PRD.CROP.XD","AG.PRD.FOOD.XD","AG.SRF.TOTL.K2","AG.PRD.LVSK.XD","EG.ELC.ACCS.RU.ZS","AG.YLD.CREL.KG","EN.POP.EL5M.RU.ZS","ER.H2O.FWAG.ZS","NV.AGR.TOTL.CD","NV.AGR.TOTL.ZS","SL.AGR.EMPL.MA.ZS","SL.AGR.EMPL.FE.ZS","SP.RUR.TOTL","SL.AGR.EMPL.ZS","SP.RUR.TOTL.ZG","TM.VAL.AGRI.ZS.UN","SP.RUR.TOTL.ZS","TX.VAL.AGRI.ZS.UN"];
const data = await request.http(`https://api.worldbank.org/v2/topic/1/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Agriculture & Rural Development`, 'lower', { citation: indicatorNote, shortName: `WBI Agriculture` });
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