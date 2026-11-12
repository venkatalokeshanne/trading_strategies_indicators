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
const validIndicatorIds = ["EG.ELC.HYRO.ZS","EG.ELC.COAL.ZS","EG.ELC.LOSS.ZS","EG.ELC.NGAS.ZS","BX.GSR.CCIS.CD","EG.USE.ELEC.KH.PC","BX.GSR.CCIS.ZS","EG.ELC.NUCL.ZS","ER.H2O.FWAG.ZS","EG.ELC.PETR.ZS","ER.H2O.FWDM.ZS","ER.H2O.FWIN.ZS","ER.H2O.FWTL.K3","ER.H2O.FWTL.ZS","ER.H2O.INTR.PC","ER.H2O.INTR.K3","IP.IDS.RSCT","IP.TMK.RSCT","IP.TMK.NRCT","IS.AIR.DPRT","IS.AIR.GOOD.MT.K1","IS.AIR.PSGR","IS.RRS.GOOD.MT.K6","IP.IDS.NRCT","IS.RRS.PASG.KM","IS.SHP.GOOD.TU","IS.SHP.GCNW.XQ","IT.CMP.PCMP.P2","IT.MLT.MAIN","IT.MLT.MAIN.P2","IT.NET.BBND","IT.NET.BBND.P2","IT.NET.SECR.P6","IT.NET.SECR","IT.NET.USER.MA.ZS","IT.NET.USER.FE.ZS","IT.NET.USER.ZS","IS.RRS.TOTL.KM","TX.VAL.ICTG.ZS.UN","TM.VAL.ICTG.ZS.UN","IT.CEL.SETS","IT.CEL.SETS.P2"];
const data = await request.http(`https://api.worldbank.org/v2/topic/9/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Infrastructure`, 'lower', { citation: indicatorNote, shortName: `WBI Infrastructure` });
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