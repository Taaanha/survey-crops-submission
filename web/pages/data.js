/* Data, Model, Evidence, Strategies and Server-status pages (#/data #/model #/evidence #/strategies #/server).
   They draw what /data/sources, /districts, /models, /rotation/rank, /rotation/strategies return. Nothing is worked out here:
   every number, interval and sentence is the server's. A gap stays a gap ("not assessed"), never 0.
   Uses globals from modes.html: st, lang, s, esc, T, N, bi, spinner, showSources, go, CS_API, API_BASE, harvestISO; adapters CS_DS, CS_MD, CS_ST. */
var DP={ads:{}};
var DT={src:null,dis:null,srcRes:null,disRes:null,wait:false,key:0};
var MD={ad:null,res:null,wait:false};
var SG={ids:[],cur:null,res:null,ad:null,wait:false,key:null,labels:{},detail:null};
var SV={rows:{},run:false,open:null};
(function(){var c=document.createElement('style');c.textContent=
 '.dpst{display:inline-block;padding:1px 9px;border-radius:99px;font-size:.78rem;font-weight:700;color:#06101B}.dpst.ok{background:#7BD389}.dpst.part{background:#FFB547}.dpst.na{background:#8794a0}.dpst.bad{background:#FF7A6B}'+
 '.dpgrid{display:grid;gap:12px}@media(min-width:760px){.dpgrid.two{grid-template-columns:1fr 1fr}}.dpcard h3{margin:0 0 4px}.dpcard p{margin:4px 0}'+
 '.dpnum{white-space:nowrap}.rktab .src{white-space:nowrap;display:inline-block}';document.head.appendChild(c)})();
function dpHead(eb,t,sub,vid){return '<div class="eyebrow">'+esc(eb)+'</div><h1 style="font-size:clamp(1.5rem,5.5vw,2.1rem);margin-top:6px">'+esc(t)+(window.voiceBtn&&vid?voiceBtn(vid):'')+'</h1>'+(sub?'<p class="lead">'+esc(sub)+'</p>':'')}
function dpBadge(res,mock){var live=CS_API.isLive(res);return '<div class="note'+(live?'':' warn')+'" style="margin:6px 0"><span class="badge">'+esc(live?s('planLive'):s('planDemo'))+'</span><span>'+esc(res&&res.source==='live'&&res.data&&res.data.source_mode||'')+'</span></div>'}
function dpWait(){return '<p>'+spinner()+esc(s('planWait'))+'</p>'}
function dpOff(){return '<div class="note warn"><span>'+esc(s('offline'))+'</span></div>'}
function dpErr(a){return '<div class="note warn"><span>'+esc(a&&a.errors&&a.errors.length?T(a.errors[0]):s('planNone'))+'</span></div>'}
function dpNum(v){if(v==null)return '<span style="color:var(--mute)">'+esc(bi('not assessed','মূল্যায়ন হয়নি'))+'</span>';var r=Math.round(v*1000)/1000;return '<span class="dpnum" title="'+esc(String(v))+'">'+N(r)+'</span>'}
function dpMeas(m){return m?N(m.value)+' '+esc(lang==='bn'&&m.unit==='mm'?'মিমি':m.unit):'<span style="color:var(--mute)">'+esc(bi('not assessed','মূল্যায়ন হয়নি'))+'</span>'}
/* a Source button for a provenance object that sits right next to the number (the strategies answer carries it inline) */
function dpSrc(p){if(!p)return '';var k='p'+Object.keys(DP.ads).length;var u=String(p.source_url||p.url||'').split(';')[0].trim();DP.ads[k]={provenance:{x:{id:'x',dataset:p.dataset,url:u,period:p.retrieved?bi('retrieved ','ডেটা নেওয়া ')+p.retrieved:'',resolution:p.granule_or_file||'',note:p.note||''}}};
 return '<button class="src" data-act="dpsrc" data-v="'+k+'">'+bi('Source','উৎস')+' ›</button>'}
function dpStatus(x){var t=String(x||'').toLowerCase();var c=t==='assessed'||t==='ok'||t==='full'?'ok':(t==='partial'?'part':(t.indexOf('not')>=0||t==='gap'?'na':'bad'));return '<span class="dpst '+c+'">'+esc(x||'?')+'</span>'}
function dpLink(u){return u?'<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(u)+' ↗</a>':'<span style="color:var(--mute)">'+esc(bi('Link pending','লিংক পরে যোগ হবে'))+'</span>'}

/* ---------- #/data ---------- */
function dtLoad(){if(DT.wait||(DT.src&&DT.dis))return;DT.wait=true;var k=++DT.key;
 Promise.all([CS_API.get('/api/v1/data/sources'),CS_API.get('/api/v1/districts')]).then(function(a){DT.wait=false;DT.srcRes=a[0];DT.disRes=a[1];DT.src=a[0].data?CS_DS.sources(a[0].data):null;DT.dis=a[1].data?CS_DS.districts(a[1].data):null;if(cur==='data')renderData()})}
function renderData(){
 var h=dpHead(bi('Officer','কর্মকর্তা'),bi('Data and sources','ডেটা ও উৎস'),bi('Every dataset the app uses, how much of it we really have, and where it comes from.','অ্যাপ যে ডেটা ব্যবহার করে, আমাদের হাতে আসলে কতটা আছে, আর কোথা থেকে এসেছে।'),'page-data');
 dtLoad();
 if(DT.wait&&!DT.src)h+=dpWait();
 else if(!DT.src)h+=dpOff();
 else if(!DT.src.ok)h+=dpErr(DT.src);
 else{var a=DT.src;h+=dpBadge(DT.srcRes);if(a.note)h+='<p style="color:var(--mute)">'+esc(a.note)+'</p>';
  h+='<div class="dpgrid two">'+a.items.map(function(x){return '<div class="card dpcard"><h3>'+esc(x.name)+'</h3><p>'+dpStatus(x.status)+' '+(x.districts!=null?'<span style="color:var(--mute)">'+N(x.districts)+' '+esc(bi('districts','জেলা'))+'</span>':'')+'</p>'+
   (x.coverage?'<p><b>'+esc(bi('Coverage','কভারেজ'))+':</b> '+esc(x.coverage)+'</p>':'')+(x.reason?'<p style="color:var(--mute)">'+esc(x.reason)+'</p>':'')+
   '<p style="font-size:.85em;color:var(--mute)">'+esc(x.units)+(x.resolution?' · '+esc(x.resolution):'')+'</p><p>'+dpLink(x.url)+'</p></div>'}).join('')+'</div>'}
 if(DT.dis&&DT.dis.ok){h+='<h2>'+esc(bi('Where it works: districts','কোথায় কাজ করে: জেলা'))+'</h2>'+dpBadge(DT.disRes)+'<div class="rkbox"><table class="rktab"><thead><tr><th class="rkh">'+esc(bi('District','জেলা'))+'</th><th>'+esc(bi('Rain','বৃষ্টি'))+'</th><th>'+esc(bi('Temperature','তাপমাত্রা'))+'</th><th>'+esc(bi('Soil moisture','মাটির আর্দ্রতা'))+'</th><th>'+esc(bi('Flood maps','বন্যার মানচিত্র'))+'</th><th>'+esc(bi('Crops in the risk calendar','ঝুঁকি ক্যালেন্ডারের ফসল'))+'</th></tr></thead><tbody>'+
  DT.dis.items.map(function(d){var c=d.cov;function per(k){return c[k]&&c[k].period?esc(c[k].period):'<span style="color:var(--mute)">'+esc(bi('not assessed','মূল্যায়ন হয়নি'))+'</span>'}
   return '<tr><th class="rkh">'+esc(d.name?T(d.name):d.id)+(d.covered?'':'<br><small>'+esc(bi('basic mode only','শুধু মৌলিক মোড'))+'</small>')+(d.sharedWith.length?'<br><small>'+esc(bi('weather cell shared with ','আবহাওয়ার সেল একই: '))+esc(d.sharedWith.join(', '))+'</small>':'')+'</th><td class="num dpnum">'+per('rain')+'</td><td class="num dpnum">'+per('temperature')+'</td><td class="num dpnum">'+per('soil_moisture')+'</td><td class="num dpnum">'+per('flood_maps')+'</td><td class="num">'+esc(d.crops.join(', ')||'–')+'</td></tr>'}).join('')+'</tbody></table></div>'}
 h+='<div class="note warn"><span>'+esc(bi('Based on past seasons. Not a forecast.','অতীতের মৌসুমের ভিত্তিতে। পূর্বাভাস নয়।'))+'</span></div>';
 $('#pg-data').innerHTML=h}

/* ---------- #/model ---------- */
function mdLoad(){if(MD.wait||MD.ad)return;MD.wait=true;CS_API.get('/api/v1/models').then(function(r){MD.wait=false;MD.res=r;MD.ad=r.data?CS_MD.adapt(r.data):null;if(cur==='model')renderModel()})}
function mdRow(r){var v=r.v;return '<tr><th class="rkh">'+esc(r.label)+'</th><td class="num">'+dpNum(v.value)+'</td><td class="num dpnum">'+(v.lo!=null?dpNum(v.lo)+' – '+dpNum(v.hi):'–')+'</td><td class="num">'+(v.n!=null?N(v.n):'–')+'</td></tr>'}
function renderModel(){
 var h=dpHead(bi('Officer','কর্মকর্তা'),bi('How good are the models?','মডেলগুলো কতটা ভালো?'),bi('Held-out test results, exactly as the server returns them.','হাতে-রাখা পরীক্ষার ফলাফল, সার্ভার যেভাবে দেয় ঠিক সেভাবে।'),'page-model');
 mdLoad();
 if(MD.wait&&!MD.ad)return $('#pg-model').innerHTML=h+dpWait();
 var a=MD.ad;if(!a)return $('#pg-model').innerHTML=h+dpOff();if(!a.ok)return $('#pg-model').innerHTML=h+dpErr(a);
 h+=dpBadge(MD.res);
 if(a.note)h+='<div class="note warn"><span>'+esc(a.note)+'</span></div>';
 h+='<p style="color:var(--mute);font-size:.85em">'+esc(bi('Districts used','ব্যবহৃত জেলা'))+': '+esc(a.districts.join(', '))+' · seed '+N(a.seed)+'. '+esc(bi('Numbers are shown to 3 decimals; hover a number for the full value.','সংখ্যা ৩ দশমিক পর্যন্ত দেখানো; পুরো মান দেখতে সংখ্যার উপর হোভার করুন।'))+'</p>';
 a.blocks.forEach(function(x){var b=x.b||{};h+='<div class="card"><h3>'+esc(bi(x.title[0],x.title[1]))+'</h3>'+
  (b.use?'<p><b>'+esc(bi('Method shown in the app','অ্যাপে যে পদ্ধতি দেখানো হয়'))+':</b> '+esc(b.use)+'</p>':'')+(b.reason?'<p>'+esc(b.reason)+'</p>':'')+(b.methodAStatus?'<p style="color:var(--mute)">'+esc(b.methodAStatus)+'</p>':'')+
  (b.n?'<p style="color:var(--mute)">n = '+N(b.n)+' '+esc(bi('district-seasons','জেলা-মৌসুম'))+'</p>':'')+
  (b.rows&&b.rows.length?'<div class="rkbox"><table class="rktab"><thead><tr><th class="rkh"></th><th>'+esc(bi('Value','মান'))+'</th><th>95% '+esc(bi('range','পরিসীমা'))+'</th><th>n</th></tr></thead><tbody>'+b.rows.map(mdRow).join('')+'</tbody></table></div>':'')+
  (b.resolution?'<p style="color:var(--mute)">'+esc(b.resolution)+'</p>':'')+(b.caveat?'<div class="note warn"><span>'+esc(b.caveat)+'</span></div>':'')+
  (b.sources&&b.sources.length?'<details><summary>'+esc(bi('Sources','উৎস'))+'</summary>'+b.sources.map(function(z){return '<p>'+esc(z.name||'')+'<br>'+dpLink(z.url)+'</p>'}).join('')+'</details>':'')+'</div>'});
 if(a.stressCaveat)h+='<div class="note warn"><span>'+esc(a.stressCaveat)+'</span></div>';
 var ex=Object.keys(a.excluded);if(ex.length)h+='<div class="card"><h3>'+esc(bi('Left out on purpose','ইচ্ছাকৃতভাবে বাদ'))+'</h3>'+ex.map(function(k){return '<p><b>'+esc(k)+'</b>: '+esc(a.excluded[k])+'</p>'}).join('')+'</div>';
 var cs=Object.keys(a.cards);if(cs.length)h+='<div class="only-officer"><h2>'+esc(bi('Model cards','মডেল কার্ড'))+'</h2>'+cs.map(function(k){return '<details class="card"><summary><b>'+esc(k)+'</b></summary><pre class="json" style="white-space:pre-wrap">'+esc(a.cards[k])+'</pre></details>'}).join('')+'</div>';
 h+='<div class="note warn"><span>'+esc(bi('Based on past seasons. Not a forecast.','অতীতের মৌসুমের ভিত্তিতে। পূর্বাভাস নয়।'))+'</span></div>';
 $('#pg-model').innerHTML=h}

/* ---------- #/strategies and #/evidence (same answer) ---------- */
function rotLabel(o){var sl=(o.rotation&&o.rotation.slots)||[];return sl.map(function(x){var k=x.crop==='boro_rice'?'boro':(x.crop==='aman_rice'?'aman':x.crop);return (typeof CROPS!=='undefined'&&CROPS[k])?T(CROPS[k].n):String(x.crop).replace(/_/g,' ')}).join(' → ')+(sl[0]&&sl[0].sow_mmdd?' ('+sl[0].sow_mmdd+')':'')}
function sgLoad(){var k=JSON.stringify([st.district,SG.cur]);
 if(SG.idsFor!==st.district){if(SG.wait)return;SG.wait=true;SG.idsFor=st.district;
  /* only the list of rotations is needed here, so the priorities are sent equal; the server's order is not shown */
  CS_API.post('/api/v1/rotation/rank',{district:st.district,weights:{save_water:0.25,soil_health:0.25,lowest_risk:0.25,flood_safety:0.25}}).then(function(r){var d=r.data&&r.data.data,l=d?(d.ranked||[]).concat(d.unranked||[]):[];SG.ids=l.map(function(x){return x.id});SG.labels={};l.forEach(function(x){SG.labels[x.id]=x});SG.wait=false;if(!SG.cur||SG.ids.indexOf(SG.cur)<0)SG.cur=SG.ids[0]||null;SG.res=null;SG.ad=null;SG.rankRes=r;SG.key=null;sgRepaint();if(SG.cur)sgLoad()});return}
 if(!SG.cur||SG.key===k)return;SG.key=k;SG.wait=true;SG.ad=null;SG.res=null;sgRepaint();
 CS_API.get('/api/v1/rotation/strategies?district='+st.district+'&current='+encodeURIComponent(SG.cur)).then(function(r){if(SG.key!==k)return;SG.wait=false;SG.res=r;SG.ad=r.data?CS_ST.adapt(r.data):null;sgRepaint()})}
function sgRepaint(){if(cur==='strategies')renderStrategies();else if(cur==='evidence')renderEvidence()}
function sgPick(){return '<p style="margin:6px 0"><b>'+esc(bi('What do you grow now?','এখন কী চাষ করেন?'))+'</b></p><div class="chips">'+SG.ids.map(function(id){return '<button class="chip'+(SG.cur===id?' on':'')+'" data-act="sgcur" data-v="'+esc(id)+'">'+esc(sgLab(id))+'</button>'}).join('')+'</div>'}
function sgState(h){if(SG.wait&&!SG.ad)return h+dpWait();if(!SG.ad)return h+(SG.ids.length?dpOff():(SG.rankRes&&!SG.wait?dpOff():dpWait()));if(!SG.ad.ok)return h+dpErr(SG.ad);return null}
function sgStat(label,html){return '<p style="margin:3px 0"><span style="color:var(--mute)">'+esc(label)+':</span> <b>'+html+'</b></p>'}
function sgCard(o,base){var pr=o.problem;
 var h='<div class="card dpcard"><h3>'+esc(sgLab(o.id))+'</h3><p style="font-size:1.05em"><b>'+esc(o.problemLine)+'</b></p>';
 if(pr&&pr.count)h+=sgStat(bi('Past seasons with a problem','সমস্যার অতীত মৌসুম'),dpMeas(pr.count)+' / '+N(pr.n)+' <span style="color:var(--mute)">(95%: '+N(pr.lo)+'–'+N(pr.hi)+')</span> '+dpSrc(pr.count.prov));
 h+=sgStat(bi('Water needed, driest 20% of seasons','পানি লাগে, সবচেয়ে শুকনো ২০% মৌসুম'),dpMeas(o.waterWorst)+' '+(o.waterWorst?dpSrc(o.waterWorst.prov):'')+(base&&base.waterWorst&&o.waterWorst?' <span style="color:var(--mute)">('+esc(bi('now','এখন'))+' '+dpMeas(base.waterWorst)+')</span>':''));
 if(o.price)h+=csPriceHtml(o.price,o.price.prov?dpSrc(o.price.prov):'');
 if(o.legumes)h+=sgStat(bi('Soil-building (legume) crops','মাটি-উর্বর (ডাল) ফসল'),N(o.legumes.value)+' '+dpSrc(o.legumes.prov));
 if(o.pest)h+=sgStat(bi('Breaks the pest cycle','পোকার চক্র ভাঙে'),esc(o.pest.breaks?bi('yes','হ্যাঁ'):bi('not shown','দেখা যায়নি'))+' <span style="color:var(--mute);font-size:.85em">('+esc(bi('needs local review','স্থানীয় যাচাই দরকার'))+')</span>');
 if(o.why.length)h+='<ul style="padding-left:18px;margin:6px 0">'+o.why.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ul>';
 if(o.gaps.length||o.infoGaps.length)h+='<details><summary>'+esc(bi('Not assessed','মূল্যায়ন হয়নি'))+' ('+N(o.infoGaps.length||o.gaps.length)+')</summary>'+(o.infoGaps.length?o.infoGaps:o.gaps.map(function(g){return g.key+': '+g.reason})).map(function(x){return '<p style="color:var(--mute);margin:4px 0">'+esc(String(x).slice(0,300))+'</p>'}).join('')+'</details>';
 return h+'</div>'}
function renderStrategies(){
 var h=dpHead(bi('Step 4','ধাপ ৪'),bi('Other ways to rotate your crops','ফসল ঘোরানোর অন্য উপায়'),bi('Each option was tried on the past seasons 2001–2024. Based on past seasons. Not a forecast.','প্রতিটি বিকল্প ২০০১–২০২৪ অতীত মৌসুমে পরীক্ষা করা। অতীতের মৌসুমের ভিত্তিতে। পূর্বাভাস নয়।'),'page-strategies');
 sgLoad();var e=sgState(h+(SG.ids.length?sgPick():''));if(e)return $('#pg-strategies').innerHTML=e;
 var a=SG.ad;h+=sgPick()+dpBadge(SG.res);a.notices.forEach(function(x){h+='<div class="note"><span>'+esc(T(x))+'</span></div>'});
 h+='<h3>'+esc(bi('Your current rotation','আপনার বর্তমান ধারা'))+'</h3><div class="dpgrid">'+sgCard(a.baseline,null)+'</div><h3>'+esc(bi('Options to compare','তুলনার বিকল্প'))+'</h3><div class="dpgrid two">'+a.options.map(function(o){return sgCard(o,a.baseline)}).join('')+'</div>';
 if(a.notOffered.length)h+='<details class="card"><summary>'+esc(bi('Crops we do not offer yet, and why','যে ফসল এখনও দিচ্ছি না, কেন'))+'</summary>'+a.notOffered.map(function(x){return '<p style="margin:4px 0"><b>'+esc(String(x.crop).replace(/_/g,' '))+'</b>: <span style="color:var(--mute)">'+esc(x.reason||'')+'</span></p>'}).join('')+'</details>';
 $('#pg-strategies').innerHTML=h}
function renderEvidence(){
 var h=dpHead(bi('Officer','কর্মকর্তা'),bi('The evidence behind the options','বিকল্পগুলোর প্রমাণ'),bi('Water use is a Kc-weighted FAO-56 balance. Counts are over the past seasons 2001–2024.','পানির ব্যবহার Kc-ভিত্তিক FAO-56 হিসাব। গণনা ২০০১–২০২৪ অতীত মৌসুমের।'),'page-evidence');
 sgLoad();var e=sgState(h+(SG.ids.length?sgPick():''));if(e)return $('#pg-evidence').innerHTML=e;
 var a=SG.ad,all=[a.baseline].concat(a.options);h+=sgPick()+dpBadge(SG.res);
 h+='<div class="rkbox"><table class="rktab"><thead><tr><th class="rkh">'+esc(bi('Rotation','ধারা'))+'</th><th>'+esc(bi('Seasons with a problem','সমস্যার মৌসুম'))+'</th><th>95% '+esc(bi('range','পরিসীমা'))+'</th><th>'+esc(bi('Water, median','পানি, মধ্যক'))+'</th><th>'+esc(bi('Water, driest 20%','পানি, সবচেয়ে শুকনো ২০%'))+'</th><th>'+esc(bi('Legume crops','ডাল ফসল'))+'</th></tr></thead><tbody>'+
  all.map(function(o,i){var pr=o.problem;return '<tr><th class="rkh">'+esc(sgLab(o.id))+(i===0?'<br><small>'+esc(bi('current','বর্তমান'))+'</small>':'')+'</th><td class="num dpnum">'+(pr&&pr.count?N(pr.count.value)+' / '+N(pr.n)+' '+dpSrc(pr.count.prov):'<span style="color:var(--mute)">'+esc(bi('not assessed','মূল্যায়ন হয়নি'))+'</span>')+'</td><td class="num dpnum">'+(pr&&pr.count?N(pr.lo)+' – '+N(pr.hi):'–')+'</td><td class="num dpnum">'+dpMeas(o.waterMedian)+'</td><td class="num dpnum">'+dpMeas(o.waterWorst)+' '+(o.waterWorst?dpSrc(o.waterWorst.prov):'')+'</td><td class="num dpnum">'+(o.legumes?N(o.legumes.value):'–')+'</td></tr>'}).join('')+'</tbody></table></div>';
 if(a.baseline.waterNote)h+='<p style="color:var(--mute);font-size:.85em">'+esc(a.baseline.waterNote)+'</p>';
 all.forEach(function(o){if(o.problem&&o.problem.checked.length)h+='<p style="color:var(--mute);font-size:.85em;margin:2px 0">'+esc(sgLab(o.id))+': '+esc(bi('hazards checked','যাচাই করা ঝুঁকি'))+' '+esc(o.problem.checked.join(', '))+'</p>'});
 if(a.assumptions.length)h+='<details class="card"><summary>'+esc(bi('Assumptions we made','যেসব ধরে নেওয়া হয়েছে'))+'</summary><ul style="padding-left:18px">'+a.assumptions.map(function(x){return '<li>'+esc(String(x).slice(0,400))+'</li>'}).join('')+'</ul></details>';
 h+='<div class="note"><span>'+esc(bi('The past-season replay of one field (the analog year) is on the Field Twin page.','একটি জমির অতীত মৌসুমের পুনরাবৃত্তি (অ্যানালগ বছর) জমির টুইন পাতায়।'))+'</span> <button class="pill" data-act="go" data-v="twin">'+esc(bi('Open','খুলুন'))+'</button></div>';
 $('#pg-evidence').innerHTML=h}

/* ---------- #/server (officer): is each endpoint up, slow, or failed? ---------- */
var SV_LIST=['/api/v1/districts','/api/v1/data/sources','/api/v1/data/reference','/api/v1/disease-rules','/api/v1/models','/api/v1/map/layers','/api/v1/warnings?district=cumilla','/api/v1/enso-lens?district=cumilla&crop=mustard','/api/v1/risk-calendar?district=cumilla&crop=mustard','/api/v1/advisory?district=cumilla&prev_harvest=@H'];
function svRun(){if(SV.run||!window.API_BASE)return;SV.run=true;SV.rows={};renderStatus();
 var i=0;(function next(){if(i>=SV_LIST.length){SV.run=false;renderStatus();return}var p=SV_LIST[i++],t0=Date.now();
  fetch(String(API_BASE).replace(/\/$/,'')+p.replace('@H',harvestISO())).then(function(r){return r.text().then(function(txt){var j=null;try{j=JSON.parse(txt)}catch(e){}SV.rows[p]={code:r.status,ms:Date.now()-t0,j:j,txt:txt,mock:j&&j.is_mock===true,mode:j&&j.source_mode,err:j&&j.errors&&j.errors.length?j.errors[0]:null}})}).catch(function(e){SV.rows[p]={code:0,ms:Date.now()-t0,fail:String(e)}}).then(function(){renderStatus();next()})})()}
function svState(r){if(!r)return ['na',bi('waiting','অপেক্ষা')];if(r.fail||r.code===0)return ['bad',bi('failed','ব্যর্থ')];if(r.code>=400||r.err)return ['bad',bi('failed','ব্যর্থ')+' '+r.code];if(r.ms>5000)return ['part',bi('slow','ধীর')];return ['ok',bi('ok','ঠিক আছে')]}
function renderStatus(){
 var h=dpHead(bi('Officer','কর্মকর্তা'),bi('Server status','সার্ভারের অবস্থা'),bi('Asks each part of the server once and shows how it answered. The free server sleeps when idle, so the first answer can take about a minute.','সার্ভারের প্রতিটি অংশকে একবার জিজ্ঞেস করে কী উত্তর দিল দেখায়। বিনামূল্যের সার্ভার অলস থাকলে ঘুমিয়ে যায়, তাই প্রথম উত্তরে প্রায় এক মিনিট লাগতে পারে।'));
 if(!window.API_BASE)return $('#pg-server').innerHTML=h+'<div class="note warn"><span>'+esc(s('notlive'))+'</span></div>';
 h+='<p><button class="btn" data-act="svrun"'+(SV.run?' disabled':'')+'>'+esc(SV.run?bi('Checking…','যাচাই চলছে…'):bi('Check the server now','এখনই সার্ভার যাচাই করুন'))+'</button></p><p style="color:var(--mute);font-size:.85em">'+esc(String(API_BASE))+'</p>';
 h+='<div class="rkbox"><table class="rktab"><thead><tr><th class="rkh">'+esc(bi('Part','অংশ'))+'</th><th>'+esc(bi('State','অবস্থা'))+'</th><th>'+esc(bi('Time','সময়'))+'</th><th>'+esc(bi('Kind of answer','উত্তরের ধরন'))+'</th><th></th></tr></thead><tbody>'+SV_LIST.map(function(p){var r=SV.rows[p],x=svState(r);
  return '<tr><th class="rkh" style="word-break:break-all">'+esc(p.replace('/api/v1','').replace('&prev_harvest=@H',''))+'</th><td class="num">'+'<span class="dpst '+x[0]+'">'+esc(x[1])+'</span></td><td class="num dpnum">'+(r?(r.ms/1000).toFixed(1)+' s':'–')+'</td><td class="num">'+(r&&r.j?esc((r.mock?bi('example data','উদাহরণ তথ্য'):bi('real data','আসল তথ্য'))+(r.mode?' · '+r.mode:'')):'–')+'</td><td class="num">'+(r&&r.txt?'<button class="src" data-act="svraw" data-v="'+esc(p)+'">JSON</button>':'')+'</td></tr>'+
  (SV.open===p&&r?'<tr><td colspan="5"><pre class="json" style="max-height:300px;overflow:auto">'+esc(r.err?JSON.stringify(r.err):(r.txt||'').slice(0,4000))+'</pre></td></tr>':'')}).join('')+'</tbody></table></div>';
 h+='<div class="note"><span>'+esc(bi('Slow = more than 5 seconds. The long Render sleep shows here as slow, not failed.','ধীর = ৫ সেকেন্ডের বেশি। রেন্ডারের দীর্ঘ ঘুম এখানে ব্যর্থ নয়, ধীর হিসেবে দেখায়।'))+'</span></div>';
 $('#pg-server').innerHTML=h}
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-act="dpsrc"],[data-act="sgcur"],[data-act="svrun"],[data-act="svraw"]');if(!b)return;var a=b.dataset.act,v=b.dataset.v;
 if(a==='dpsrc')showSources('x',DP.ads[v]);else if(a==='sgcur'){SG.cur=v;SG.key=null;sgLoad()}else if(a==='svrun')svRun();else if(a==='svraw'){SV.open=SV.open===v?null:v;renderStatus()}});
function moreCard(){return '<h2>'+esc(bi('More','আরও'))+'</h2><div class="card"><div class="chips">'+
 '<button class="chip" data-act="go" data-v="strategies">'+esc(bi('Other ways to rotate','ঘোরানোর অন্য উপায়'))+'</button>'+
 '<button class="chip" data-act="go" data-v="data">'+esc(bi('Data and districts','ডেটা ও জেলা'))+'</button>'+
 '<button class="chip only-officer" data-act="go" data-v="model">'+esc(bi('Model accuracy','মডেলের নির্ভুলতা'))+'</button>'+
 '<button class="chip only-officer" data-act="go" data-v="evidence">'+esc(bi('Evidence','প্রমাণ'))+'</button>'+
 '<button class="chip only-officer" data-act="go" data-v="server">'+esc(bi('Server status','সার্ভারের অবস্থা'))+'</button></div></div>'}
function sgLab(id){var x=SG.labels[id];return x?rotLabel(x):id}
