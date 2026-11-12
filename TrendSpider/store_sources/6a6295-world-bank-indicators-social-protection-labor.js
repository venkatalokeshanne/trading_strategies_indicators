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
const validIndicatorIds = ["SL.AGR.EMPL.MA.ZS","SL.EMP.1524.SP.FE.NE.ZS","SL.AGR.EMPL.ZS","SL.AGR.EMPL.FE.ZS","SL.EMP.1524.SP.MA.NE.ZS","SL.EMP.1524.SP.MA.ZS","SL.EMP.1524.SP.FE.ZS","SL.EMP.1524.SP.ZS","SL.EMP.MPYR.FE.ZS","SL.EMP.MPYR.MA.ZS","SL.EMP.MPYR.ZS","SL.EMP.SELF.MA.ZS","SL.EMP.SELF.ZS","SL.EMP.SELF.FE.ZS","SL.EMP.TOTL.SP.FE.NE.ZS","SL.EMP.TOTL.SP.MA.NE.ZS","SL.EMP.SMGT.FE.ZS","SL.EMP.1524.SP.NE.ZS","SL.EMP.TOTL.SP.MA.ZS","SL.EMP.TOTL.SP.ZS","SL.EMP.TOTL.SP.FE.ZS","SL.EMP.TOTL.SP.NE.ZS","SL.EMP.VULN.FE.ZS","SL.EMP.VULN.ZS","SL.EMP.WORK.FE.ZS","SL.EMP.VULN.MA.ZS","SL.EMP.WORK.ZS","SL.EMP.WORK.MA.ZS","SL.FAM.WORK.FE.ZS","SL.FAM.WORK.MA.ZS","SL.FAM.WORK.ZS","SL.GDP.PCAP.EM.KD","SL.IND.EMPL.MA.ZS","SL.IND.EMPL.ZS","SL.IND.EMPL.FE.ZS","SL.SRV.EMPL.FE.ZS","SL.SRV.EMPL.ZS","SL.SRV.EMPL.MA.ZS","SL.TLF.ACTI.1524.FE.ZS","SL.TLF.ACTI.1524.MA.NE.ZS","SL.TLF.ACTI.1524.FE.NE.ZS","SL.TLF.ACTI.1524.MA.ZS","SL.TLF.ACTI.1524.NE.ZS","SL.TLF.ACTI.1524.ZS","SL.TLF.ACTI.FE.ZS","SL.TLF.ACTI.ZS","SL.TLF.ACTI.MA.ZS","SL.TLF.ADVN.FE.ZS","SL.TLF.ADVN.MA.ZS","SL.TLF.BASC.FE.ZS","SL.TLF.BASC.MA.ZS","SL.TLF.ADVN.ZS","SL.TLF.BASC.ZS","SL.TLF.CACT.FE.NE.ZS","SL.TLF.CACT.FE.ZS","SL.TLF.CACT.MA.NE.ZS","SL.TLF.CACT.FM.ZS","SL.TLF.CACT.MA.ZS","SL.TLF.CACT.NE.ZS","SL.TLF.INTM.FE.ZS","SL.TLF.CACT.ZS","SL.TLF.INTM.MA.ZS","SL.TLF.INTM.ZS","SL.TLF.PART.MA.ZS","SL.TLF.PART.FE.ZS","SL.TLF.CACT.FM.NE.ZS","SL.TLF.PART.ZS","SL.UEM.1524.FE.NE.ZS","SL.TLF.TOTL.FE.ZS","SL.TLF.TOTL.IN","SL.UEM.1524.FE.ZS","SL.UEM.1524.MA.ZS","SL.UEM.1524.MA.NE.ZS","SL.UEM.1524.ZS","SL.UEM.ADVN.MA.ZS","SL.UEM.ADVN.FE.ZS","SL.UEM.ADVN.ZS","SL.UEM.1524.NE.ZS","SL.UEM.INTM.FE.ZS","SL.UEM.BASC.FE.ZS","SL.UEM.BASC.ZS","SL.UEM.BASC.MA.ZS","SL.UEM.INTM.ZS","SL.UEM.INTM.MA.ZS","SL.UEM.NEET.FE.ME.ZS","SL.UEM.NEET.FE.ZS","SL.UEM.NEET.ZS","SL.UEM.NEET.ME.ZS","SL.UEM.NEET.MA.ZS","SL.UEM.NEET.MA.ME.ZS","SL.UEM.TOTL.FE.ZS","SL.UEM.TOTL.MA.NE.ZS","SL.UEM.TOTL.ZS","SL.UEM.TOTL.MA.ZS","SL.UEM.TOTL.NE.ZS","SL.UEM.TOTL.FE.NE.ZS"];
const data = await request.http(`https://api.worldbank.org/v2/topic/10/indicator?per_page=3000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Social Protection & Labor`, 'lower', { citation: indicatorNote, shortName: `WBI Labor` });
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