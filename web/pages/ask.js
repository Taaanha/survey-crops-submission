/* Ask page (#/ask). Renders the answer of POST /api/v1/ask and nothing else:
   no numbers are computed here, no model is called here, no NASA/HF call.
   The mic language follows the page language (bn-BD / en-US); the speaker
   button hides itself if the device has no voice for the answer's language.
   Uses globals from modes.html: lang, st, esc, bi, ic, toast, CS_API, and
   ChatVoice from app/chat_voice.js. Bangla strings need native review. */
(function(){var c=document.createElement('style');c.textContent=
 '.ask-log{display:grid;gap:10px;margin:12px 0}.ask-msg{border-radius:16px;padding:12px 14px;max-width:62ch;line-height:1.5}'+
 '.ask-msg.me{justify-self:end;background:rgba(242,193,78,.16);border:1px solid rgba(242,193,78,.4)}'+
 '.ask-msg.bot{border:1px solid var(--line);background:rgba(255,255,255,.05)}'+
 '.ask-msg small{display:block;color:var(--mute);margin-top:8px;font-size:.82em}.ask-msg a{color:var(--water)}'+
 '.ask-row{display:flex;gap:8px;align-items:center;margin-top:8px;position:sticky;bottom:8px}.ask-row .btn{flex:0 0 auto;width:auto;margin:0;padding:12px 22px}.ask-row input{flex:1 1 auto;width:auto;min-width:0;min-height:48px;padding:12px 14px;border-radius:14px;border:1px solid var(--line);background:rgba(255,255,255,.06);color:var(--ink);font:inherit}'+
 '.ask-chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.ask-chips button{padding:8px 12px;border-radius:99px;border:1px solid var(--line);background:rgba(255,255,255,.05);color:var(--ink);font:inherit;cursor:pointer}'+
 '.ask-spk{display:flex;margin-top:8px}';
 document.head.appendChild(c)})();

var ASK={msgs:[],busy:false,mic:null};

function askChips(){return lang==='bn'?
 ['আমার জমিতে এবার কী লাগাবো?','সরিষা বুনলে ঝুঁকি কেমন?','কোন ফসলে সেচ কম লাগে?','আমার মাটি কেমন?','আবহাওয়ার সতর্কতা আছে?']:
 ['What should I plant this year?','Is mustard risky to sow?','Which crops need less irrigation?','What is my soil like?','Any weather warnings?']}

function askSources(list){
 var out=(list||[]).filter(function(p){return p&&p.dataset}).slice(0,4).map(function(p){
  var u=p.url||p.source_url;var ok=typeof u==='string'&&/^https:\/\//.test(u);
  return ok?'<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(p.dataset)+'</a>':esc(p.dataset)});
 return out.length?'<small>'+esc(bi('Sources: ','তথ্যসূত্র: '))+out.join('; ')+'</small>':''}

function askMsgHtml(m,i){
 if(m.role==='me')return '<div class="ask-msg me">'+esc(m.text)+'</div>';
 var spk=(window.ChatVoice&&ChatVoice.findVoice(m.lang))?'<button class="pill ask-spk" data-ask="speak" data-i="'+i+'" aria-label="'+esc(bi('Hear this','এটি শুনুন'))+'">'+ic('spk')+'</button>':'';
 return '<div class="ask-msg bot">'+esc(m.text)+spk+(m.note?'<small>'+esc(m.note)+'</small>':'')+askSources(m.sources)+'</div>'}

function renderAsk(){
 var el=document.getElementById('pg-ask');if(!el)return;
 var chips=ASK.msgs.length?'':'<div class="ask-chips">'+askChips().map(function(q){return '<button data-ask="chip" data-q="'+esc(q)+'">'+esc(q)+'</button>'}).join('')+'</div>';
 var mic=(window.ChatVoice&&ChatVoice.makeMic)?ChatVoice.makeMic(function(){return lang},function(){},function(){}):null;
 el.innerHTML='<div class="eyebrow">'+esc(bi('Ask','জিজ্ঞাসা'))+'</div>'+
  '<h1 style="font-size:clamp(1.5rem,5.5vw,2.1rem);margin-top:6px">'+esc(bi('Ask about your crops','আপনার ফসল নিয়ে জিজ্ঞাসা করুন'))+'</h1>'+
  '<p class="lead">'+esc(bi('Type or speak, in English or Bangla. Answers use NASA satellite data and the app’s checked numbers. They show what past seasons show, not a forecast.','ইংরেজি বা বাংলায় লিখুন বা বলুন। উত্তর আসে নাসার স্যাটেলাইট তথ্য ও অ্যাপের যাচাই করা সংখ্যা থেকে। এটি গত মৌসুমগুলোর তথ্য, ভবিষ্যতের পূর্বাভাস নয়।'))+'</p>'+
  chips+'<div class="ask-log" aria-live="polite">'+ASK.msgs.map(askMsgHtml).join('')+(ASK.busy?'<div class="ask-msg bot">'+esc(bi('Checking the data…','তথ্য দেখা হচ্ছে…'))+'</div>':'')+'</div>'+
  '<div class="ask-row"><input id="ask-in" type="text" maxlength="400" autocomplete="off" aria-label="'+esc(bi('Your question','আপনার প্রশ্ন'))+'" placeholder="'+esc(bi('Your question','আপনার প্রশ্ন'))+'">'+
  (mic?'<button class="pill" id="ask-mic" data-ask="mic" aria-label="'+esc(bi('Speak','বলুন'))+'">'+ic('spk')+'</button>':'')+
  '<button class="btn" data-ask="send">'+esc(bi('Ask','জিজ্ঞাসা'))+'</button></div>'}

function askSend(q){
 q=String(q||'').trim();if(!q||ASK.busy)return;
 ASK.msgs.push({role:'me',text:q});ASK.busy=true;renderAsk();
 CS_API.post('/api/v1/ask',{question:q,district:st.district,lang:lang}).then(function(r){
  ASK.busy=false;var d=r&&r.data,n=d&&d.narration,al=d&&d.data&&d.data.answer_lang;
  if(!r||r.source!=='live'||!n||!(n.en||n.bn)){
   var e=d&&d.errors&&d.errors[0];
   ASK.msgs.push({role:'bot',lang:lang,text:e?(lang==='bn'?e.bn:e.en):bi('The server could not be reached, so there is no answer right now. Please try again in a minute.','সার্ভারে পৌঁছানো যায়নি, তাই এখন উত্তর নেই। এক মিনিট পরে আবার চেষ্টা করুন।'),sources:[]});
  }else{
   var l=al==='bn'?'bn':'en';
   var note=(d.notices||[]).some(function(x){return x.code==='RULE_ROUTER'})?bi('Answered from the app’s own rules and data.','অ্যাপের নিজস্ব নিয়ম ও ডেটা থেকে উত্তর।'):'';
   ASK.msgs.push({role:'bot',lang:l,text:n[l]||n.en||n.bn,sources:d.provenance,note:note});
  }
  renderAsk();var i=document.getElementById('ask-in');if(i)i.focus()})}

document.addEventListener('click',function(e){
 var b=e.target.closest&&e.target.closest('[data-ask]');if(!b)return;var a=b.dataset.ask;
 if(a==='send'){var i=document.getElementById('ask-in');askSend(i&&i.value)}
 else if(a==='chip')askSend(b.dataset.q);
 else if(a==='speak'){var m=ASK.msgs[+b.dataset.i];if(m&&!ChatVoice.speakAnswer(m.text,m.lang))toast(bi('No voice for this language on this device.','এই ডিভাইসে এই ভাষার কণ্ঠ নেই।'))}
 else if(a==='mic'){
  if(ASK.mic){ASK.mic.stop();ASK.mic=null;return}
  ASK.mic=ChatVoice.makeMic(function(){return lang},function(t){ASK.mic=null;var i=document.getElementById('ask-in');if(i)i.value=t;askSend(t)},function(){ASK.mic=null;toast(bi('Could not hear you. Please type instead.','শোনা যায়নি। দয়া করে লিখুন।'))});
  if(ASK.mic)ASK.mic.start()}
});
document.addEventListener('keydown',function(e){if(e.key==='Enter'&&e.target&&e.target.id==='ask-in'){e.preventDefault();askSend(e.target.value)}});
window.renderAsk=renderAsk;
