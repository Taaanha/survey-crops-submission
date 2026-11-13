/* Sowing-date risk calendar (a card on the Issues page). Draws what /api/v1/risk-calendar returns:
   problem-year counts per hazard and sowing date over past seasons, the cited sowing window, water need.
   Nothing is worked out here. Past seasons, not a forecast. A grey cell = not assessed, never 0.
   Uses globals from modes.html: st, lang, s, esc, T, N, bi, MON, spinner, showSources, CS_API; adapter CS_RK. */
var RK={crop:null,key:null,res:null,ad:null,wait:false,ads:{}};
var RK_CROPS=['wheat','mustard','potato','lentil','boro_rice'];
var RK_WATER={irrigation_mm_mean:['Irrigation needed, average (mm)','সেচ লাগে, গড় (মিমি)'],irrigation_mm_worst20:['Irrigation needed, worst 20% of years (mm)','সেচ লাগে, সবচেয়ে খারাপ ২০% বছর (মিমি)'],stress_days_mean:['Dry-soil days, average','শুকনো মাটির দিন, গড়'],stress_days_worst20:['Dry-soil days, worst 20% of years','শুকনো মাটির দিন, সবচেয়ে খারাপ ২০%']};
(function(){var c=document.createElement('style');c.textContent=
 '.rkbox{overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:12px}.rktab{border-collapse:separate;border-spacing:2px;font-size:.8rem;min-width:100%}'+
 '.rktab th{font-weight:600;color:var(--mute);padding:2px 4px;white-space:nowrap;text-align:center}.rktab th.rkh{text-align:left;position:sticky;left:0;background:#0d2330;z-index:1;min-width:92px;white-space:normal}'+
 '.rktab td{min-width:34px;height:30px;text-align:center;border-radius:6px;font-weight:700;color:#06101B}.rktab td.na{background:repeating-linear-gradient(45deg,#3a4651,#3a4651 4px,#2c363f 4px,#2c363f 8px);color:var(--mute);font-weight:500}'+
 '.rktab th.inwin{color:var(--gold);box-shadow:inset 0 -3px 0 var(--gold)}.rktab td.num{background:transparent;color:var(--ink);font-weight:500;border:1px solid var(--line)}';
 document.head.appendChild(c)})();
function rkSrc(ids){var ad=RK.srcAd||RK.ad;if(!ad||!ids||!ids.length)return '';var k='k'+Object.keys(RK.ads).length;RK.ads[k]=ad;return '<button class="src" data-act="rksrc" data-v="'+k+'|'+esc(ids.join(','))+'">'+bi('Source','উৎস')+' ›</button>'}
function rkDate(md){var p=md.split('-');return N(+p[1])+' '+MON[lang][+p[0]-1]}
function rkIn(md,w){if(!w)return false;return w.start<=w.end?(md>=w.start&&md<=w.end):(md>=w.start||md<=w.end)}
function rkHue(v,n){var t=n?Math.min(1,v/n):0;return 'hsl('+Math.round(125-125*t)+',65%,'+(t>0?58:62)+'%)'}
function rkKey(){return JSON.stringify([st.district,RK.crop])}
function rkDefaultCrop(){if(RK.crop)return;var c=st.chosen?liveId(st.chosen):null;RK.crop=RK_CROPS.indexOf(c)>=0?c:'mustard'}
function rkLoad(){
 rkDefaultCrop();rkDisLoad();var k=rkKey();if(RK.key===k&&(RK.wait||RK.ad))return;RK.key=k;RK.wait=true;RK.ad=null;RK.res=null;rkPaint();
 CS_API.get('/api/v1/risk-calendar?district='+st.district+'&crop='+RK.crop).then(function(r){if(RK.key!==k)return;RK.wait=false;RK.res=r;RK.ad=r.data?CS_RK.adapt(r.data):null;rkPaint()})}
function rkPaint(){var e=document.getElementById('rkinner');if(e)e.innerHTML=rkInner();var p=document.getElementById('pestdis');if(p)p.innerHTML=rkPestHtml()}
/* Disease weather risk shown on the Issues page pest card. Potato is the crop with a sourced rule, so its answer is used
   whichever crop chip is selected; when Potato is selected the same answer is reused. Other crops: no sourced rule yet. */
function rkPestHtml(){var a=RK.crop==='potato'?RK.ad:(RK.dis&&RK.dis.key===st.district?RK.dis.ad:null);
 if(!a||!a.ok||!a.disease||!a.disease.length)return RK.disWait?'<p>'+spinner()+esc(s('planWait'))+'</p>':'';
 RK.srcAd=a;var h=rkDiseaseHtml(a,true);RK.srcAd=null;
 return h+'<p class="only-officer" style="color:var(--mute);font-size:.85em;margin:4px 0 0">'+esc(bi('Wheat, lentil, mustard and boro rice: no sourced disease rule yet.','গম, মসুর, সরিষা ও বোরো ধান: এখনও সূত্রসহ রোগের নিয়ম নেই।'))+'</p>'}
function rkDisLoad(){if(RK.crop==='potato'||(RK.dis&&RK.dis.key===st.district)||RK.disWait)return;RK.disWait=true;var d=st.district;
 CS_API.get('/api/v1/risk-calendar?district='+d+'&crop=potato').then(function(r){RK.disWait=false;RK.dis={key:d,ad:r.data?CS_RK.adapt(r.data):null};rkPaint()})}
/* Disease-favourable weather, as counted by the server over past seasons (not a claim that disease occurred). Not assessed = no sourced rule, never 0. */
function rkDiseaseHtml(a,compact){
 if(!a||!a.disease||!a.disease.length)return '';
 var h='<div style="margin-top:10px"><h4 style="margin:8px 0 4px">'+esc(bi('Disease weather risk','রোগের আবহাওয়া-ঝুঁকি'))+'</h4>';
 a.disease.forEach(function(x){
  if(x.status!=='assessed'){h+='<p style="color:var(--mute);margin:4px 0">'+esc(bi('Not assessed for this crop.','এই ফসলের জন্য মূল্যায়ন হয়নি।'))+'<span class="only-officer"> '+esc(x.reason)+'</span></p>';return}
  h+='<p style="margin:4px 0"><b>'+esc(x.label?T(x.label):'')+':</b> '+esc(bi('conditions favourable in','অনুকূল আবহাওয়া ছিল'))+' <b>'+N(x.fav.value)+'</b> '+esc(bi('of','/'))+' '+N(x.n.value)+' '+esc(bi('past seasons','অতীত মৌসুমে'))+' '+rkSrc(x.fav.src)+'</p>';
  if(x.windowText)h+='<p style="color:var(--mute);font-size:.85em;margin:2px 0">'+esc(bi('Counted from','গণনার সময়'))+' '+esc(T(x.windowText))+'. '+esc(x.meaning?T(x.meaning):'')+'</p>';
  if(!compact){h+='<div class="only-officer" style="font-size:.85em;color:var(--mute)">'+x.rule.map(function(r){return esc(r.label)+': '+N(r.value)+' '+esc(r.unit)}).join('<br>')+(x.run?'<br>'+esc(bi('Counted as a favourable season when it lasts','অনুকূল মৌসুম ধরা হয় যখন টানা'))+' '+N(x.run.value)+' '+esc(bi('days in a row','দিন থাকে'))+'':'')+(x.windowNote?'<br>'+esc(T(x.windowNote)):'')+'</div>'}
 });
 return h+'</div>'}
function rkInner(){
 var chips='<div class="chips" style="margin:6px 0">'+RK_CROPS.map(function(c){var k=c==='boro_rice'?'boro':c;return '<button class="chip'+(RK.crop===c?' on':'')+'" data-act="rkcrop" data-v="'+c+'">'+esc(T((CROPS[k]||{n:{en:c,bn:c}}).n))+'</button>'}).join('')+'</div>';
 if(RK.wait)return chips+'<p>'+spinner()+esc(s('planWait'))+'</p>';
 var a=RK.ad;
 if(!a)return chips+'<div class="note warn"><span>'+esc(s('offline'))+'</span></div>';
 if(!a.ok)return chips+'<div class="note warn"><span>'+esc(a.errors.length?T(a.errors[0]):s('planNone'))+'</span></div>';
 if(RK.res&&RK.res.source==='sample'&&a.crop&&a.crop!==RK.crop)return chips+'<div class="note warn"><span>'+esc(bi('Cannot reach the server right now, and there is no saved example for this crop.','এখন সার্ভারের সঙ্গে যোগ হচ্ছে না, আর এই ফসলের কোনো সংরক্ষিত উদাহরণ নেই।'))+'</span></div>';   // the saved example is for another crop
 var live=CS_API.isLive(RK.res),n=a.years?a.years.value:24,h=chips+(live?'':'<div class="note warn"><span class="badge">'+esc(s('planDemo'))+'</span></div>');
 if(a.narration&&a.narration[lang])h+='<p>'+esc(a.narration[lang])+'</p>'+(a.narration.check&&a.narration.check!=='passed'?'<p style="color:var(--amber);font-size:.85em">'+esc(bi('The text above is the plain template sentence (the wording check did not pass).','উপরের লেখাটি সাধারণ ছক-বাক্য (ভাষা যাচাই পাস করেনি)।'))+'</p>':'')+'<span class="only-officer" style="font-size:.8em;color:var(--mute)">'+esc(a.narration.narrator||'')+' · '+esc(a.narration.check||'')+'</span>';
 if(a.window)h+='<p>'+esc(bi('Recommended sowing window','সুপারিশকৃত বপনের সময়'))+': <b>'+rkDate(a.window.start)+' – '+rkDate(a.window.end)+'</b> '+(a.window.method==='cited'?'<span style="color:var(--mute)">('+esc(bi('from a cited source','উৎস থেকে'))+')</span> ':'')+rkSrc(a.window.src)+'</p>';
 /* heat grid: rows = hazards, columns = sowing dates; each number = past seasons with the problem */
 h+='<p style="color:var(--mute);font-size:.85em;margin:8px 0 4px">'+esc(bi('Number of past seasons (of '+n+') with the problem, by sowing date. Grey = not assessed.','অতীতের কতটি মৌসুমে (মোট '+n+') সমস্যা হয়েছে, বপনের তারিখ অনুযায়ী। ধূসর = মূল্যায়ন হয়নি।'))+' '+rkSrc(a.gridSrc)+'</p>';
 h+='<div class="rkbox"><table class="rktab"><thead><tr><th class="rkh"></th>'+a.dates.map(function(d){return '<th class="'+(rkIn(d,a.window)?'inwin':'')+'">'+rkDate(d)+'</th>'}).join('')+'</tr></thead><tbody>';
 a.grid.forEach(function(r){var hz=a.hazards[r.id]||{};h+='<tr><th class="rkh">'+esc(hz.label?T(hz.label):r.id)+(hz.threshold?'<br><small style="font-weight:400">'+esc(bi('limit','সীমা'))+' '+N(hz.threshold.value)+'</small>':'')+'</th>'+r.hit.map(function(v){return v==null?'<td class="na" title="'+esc(bi('not assessed','মূল্যায়ন হয়নি'))+'">–</td>':'<td style="background:'+rkHue(v,n)+'">'+N(v)+'</td>'}).join('')+'</tr>'});
 h+='</tbody></table></div>';
 if(a.checkedText)h+='<p style="margin:8px 0 0">'+esc(T(a.checkedText))+'</p>';
 if(a.missing.length||a.coverageNotice)h+='<div class="note warn"><span>'+esc(a.coverageNotice?T(a.coverageNotice):bi('Not all risks for this crop are checked.','এই ফসলের সব ঝুঁকি যাচাই করা হয়নি।'))+'</span></div>';
 h+=rkDiseaseHtml(a,false);
 /* water */
 if(a.water)h+='<h4 style="margin:12px 0 4px">'+esc(bi('Water, by sowing date','পানি, বপনের তারিখ অনুযায়ী'))+' '+rkSrc(a.water.src)+'</h4><div class="rkbox"><table class="rktab"><thead><tr><th class="rkh"></th>'+a.dates.map(function(d){return '<th>'+rkDate(d)+'</th>'}).join('')+'</tr></thead><tbody>'+a.water.rows.filter(function(r){return r.values.length}).map(function(r){var lb=RK_WATER[r.key]||[r.key,r.key];return '<tr class="'+(r.key.indexOf('stress')>=0?'only-officer':'')+'"><th class="rkh">'+esc(bi(lb[0],lb[1]))+'</th>'+r.values.map(function(v){return '<td class="num">'+N(v)+'</td>'}).join('')+'</tr>'}).join('')+'</tbody></table></div>';
 /* how much the answer depends on our choices (officer) */
 if(a.sens&&a.sens.rows.length)h+='<div class="only-officer"><h4 style="margin:12px 0 4px">'+esc(bi('How sure is this? Other ways of counting','কতটা নিশ্চিত? গণনার অন্য উপায়'))+' '+rkSrc(a.sens.src)+'</h4><div class="rkbox"><table class="rktab"><thead><tr><th class="rkh"></th>'+a.dates.map(function(d){return '<th>'+rkDate(d)+'</th>'}).join('')+'</tr></thead><tbody>'+a.sens.rows.map(function(r){return '<tr><th class="rkh">'+esc(T(r.label)||r.id)+'</th>'+r.values.map(function(v){return v==null?'<td class="na">–</td>':'<td style="background:'+rkHue(v,n)+'">'+N(v)+'</td>'}).join('')+'</tr>'}).join('')+'</tbody></table></div></div>';
 a.notices.forEach(function(x){h+='<div class="note'+(x.level==='caution'?' warn':'')+'"><span>'+esc(T(x))+'</span></div>'});
 return h}
function riskCard(){RK.ads={};return '<div class="card"><h3>'+esc(bi('When is sowing risky?','কখন বুনলে ঝুঁকি বেশি?'))+(window.voiceBtn?voiceBtn('page-risk'):'')+'</h3><p style="color:var(--mute);margin:0">'+esc(bi('Sowing dates checked against every past season (2001–2024). Not a forecast.','প্রতিটি অতীত মৌসুম (২০০১–২০২৪) দিয়ে বপনের তারিখ যাচাই। পূর্বাভাস নয়।'))+'</p><div id="rkinner">'+rkInner()+'</div></div>'}
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-act^="rk"]');if(!b)return;var a=b.dataset.act,v=b.dataset.v;
 if(a==='rkcrop'){RK.crop=v;rkLoad()}else if(a==='rksrc'){var p=v.split('|');showSources(p[1],RK.ads[p[0]])}});
