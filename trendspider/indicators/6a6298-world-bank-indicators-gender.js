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
const validIndicatorIds = ["IC.FRM.FEMM.ZS","IC.FRM.FEMO.ZS","SE.ENR.PRIM.FM.ZS","SE.ENR.PRSC.FM.ZS","SE.ENR.SECO.FM.ZS","SE.PRE.ENRR.FE","SE.PRE.ENRR.MA","SE.PRM.CMPT.FE.ZS","SE.ENR.TERT.FM.ZS","SE.PRM.CMPT.MA.ZS","SE.PRM.CUAT.FE.ZS","SE.PRM.CUAT.ZS","SE.PRM.CUAT.MA.ZS","SE.PRM.ENRR.FE","SE.PRM.ENRL.FE.ZS","SE.PRM.ENRR.MA","SE.PRM.GINT.FE.ZS","SE.PRM.GINT.MA.ZS","SE.PRM.NENR.FE","SE.PRM.NINT.MA.ZS","SE.PRM.NINT.FE.ZS","SE.PRM.NENR.MA","SE.PRM.PRS5.MA.ZS","SE.PRM.PRS5.FE.ZS","SE.PRM.REPT.FE.ZS","SE.PRM.REPT.MA.ZS","SE.PRM.TCAQ.MA.ZS","SE.PRM.TENR.FE","SE.PRM.TCAQ.FE.ZS","SE.PRM.TCHR.FE.ZS","SE.PRM.TENR.MA","SE.PRM.UNER.FE","SE.SCH.LIFE.MA","SE.PRM.UNER.MA","SE.SEC.CUAT.LO.FE.ZS","SE.SCH.LIFE.FE","SE.SEC.CUAT.LO.MA.ZS","SE.SEC.CUAT.PO.ZS","SE.SEC.CUAT.PO.FE.ZS","SE.SEC.CUAT.PO.MA.ZS","SE.SEC.CUAT.LO.ZS","SE.SEC.CUAT.UP.MA.ZS","SE.SEC.CUAT.UP.FE.ZS","SE.SEC.ENRL.FE.ZS","SE.SEC.ENRL.GC.FE.ZS","SE.SEC.CUAT.UP.ZS","SE.SEC.ENRR.FE","SE.SEC.ENRR.MA","SE.SEC.NENR.FE","SE.SEC.NENR.MA","SE.SEC.PROG.FE.ZS","SE.SEC.TCHR.FE.ZS","SE.SEC.PROG.MA.ZS","SE.TER.CUAT.BA.FE.ZS","SE.TER.CUAT.BA.ZS","SE.TER.CUAT.DO.FE.ZS","SE.TER.CUAT.BA.MA.ZS","SE.TER.CUAT.DO.ZS","SE.TER.CUAT.DO.MA.ZS","SE.TER.CUAT.MS.FE.ZS","SE.TER.CUAT.MS.MA.ZS","SE.TER.CUAT.MS.ZS","SE.TER.ENRR.FE","SE.TER.CUAT.ST.ZS","SE.TER.CUAT.ST.MA.ZS","SE.TER.CUAT.ST.FE.ZS","SE.TER.ENRR.MA","SG.GEN.MNST.ZS","SG.GEN.PARL.ZS","SG.GEN.TECH.ZS","SG.POP.MIGR.FE.ZS","SG.TIM.UWRK.FE","SG.TIM.UWRK.MA","SH.DYN.AIDS.FE.ZS","SH.MMR.RISK.ZS","SH.MMR.RISK","SH.PRV.SMOK.MA","SH.STA.BRTC.ZS","SH.STA.MALN.FE.ZS","SH.PRV.SMOK.FE","SH.STA.MALN.MA.ZS","SH.STA.MMRT","SH.STA.MMRT.NE","SH.STA.OB18.MA.ZS","SH.STA.OB18.FE.ZS","SL.AGR.EMPL.FE.ZS","SL.EMP.1524.SP.MA.ZS","SL.AGR.EMPL.MA.ZS","SL.EMP.MPYR.FE.ZS","SL.EMP.1524.SP.FE.ZS","SL.EMP.MPYR.MA.ZS","SL.EMP.OWAC.FE.ZS","SL.EMP.OWAC.MA.ZS","SL.EMP.SELF.FE.ZS","SL.EMP.SELF.MA.ZS","SL.EMP.TOTL.SP.FE.ZS","SL.EMP.UNDR.FE.ZS","SL.EMP.UNDR.MA.ZS","SL.EMP.TOTL.SP.MA.ZS","SL.EMP.VULN.MA.ZS","SL.EMP.WORK.FE.ZS","SL.EMP.VULN.FE.ZS","SL.EMP.WORK.MA.ZS","SL.FAM.WORK.FE.ZS","SL.FAM.WORK.MA.ZS","SL.IND.EMPL.FE.ZS","SL.IND.EMPL.MA.ZS","SL.SRV.EMPL.FE.ZS","SL.SRV.EMPL.MA.ZS","SL.TLF.CACT.FE.ZS","SL.TLF.PART.FE.ZS","SL.TLF.CACT.MA.ZS","SL.TLF.PART.MA.ZS","SL.UEM.1524.FE.ZS","SL.TLF.TOTL.FE.IN","SL.UEM.1524.FM.NE.ZS","SL.TLF.TOTL.FE.ZS","SL.UEM.1524.FM.ZS","SL.UEM.1524.MA.ZS","SL.UEM.TOTL.FE.ZS","SP.ADO.TFRT","SL.UEM.TOTL.MA.ZS","SP.DYN.AMRT.FE","SP.DYN.CONU.ZS","SP.DYN.LE00.FE.IN","SP.DYN.AMRT.MA","SP.DYN.LE00.MA.IN","SP.DYN.LE60.FE.IN","SP.DYN.SMAM.MA","SP.DYN.SMAM.FE","SP.DYN.LE60.MA.IN","SP.DYN.TO65.FE.ZS","SP.DYN.TFRT.IN","SP.DYN.TO65.MA.ZS","SP.POP.AG00.FE.IN","SP.POP.AG01.FE.IN","SP.POP.AG00.MA.IN","SP.POP.AG01.MA.IN","SP.POP.AG02.FE.IN","SP.POP.AG02.MA.IN","SP.POP.AG03.FE.IN","SP.POP.AG03.MA.IN","SP.POP.AG04.MA.IN","SP.POP.AG04.FE.IN","SP.POP.AG05.MA.IN","SP.POP.AG05.FE.IN","SP.RUR.TOTL.FE.ZS","SP.URB.TOTL.FE.ZS","SP.RUR.TOTL.MA.ZS","SP.URB.TOTL.MA.ZS"];
const data = await request.http(`https://api.worldbank.org/v2/topic/17/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Gender`, 'lower', { citation: indicatorNote, shortName: `WBI Gender` });
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