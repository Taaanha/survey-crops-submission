/* Voice control: instant start, one stop for everything, Farmer-only pictures and Learn.
   Loaded after the main script in modes.html. It only plays recordings and reads the page text; it computes nothing.
   - audio/*.mp3 clips are preloaded after first paint (low priority) and kept as Audio objects.
   - play() is called straight inside the click, with no fetch or await first, so the browser allows it and it starts at once.
   - If an English clip is not loaded yet, the browser's own speech starts at once instead of waiting.
     Bangla never uses the phone's robot voice (see speakText in modes.html), so it plays the clip as soon as it loads.
   - Every voice button toggles: a second tap stops. Changing page, language or mode also stops. */
(function(){
 var cache={},cacheLang=null,cur=null,curBtn=null,bad={};
 function warmVoices(){try{if(window.speechSynthesis){speechSynthesis.getVoices();speechSynthesis.onvoiceschanged=function(){speechSynthesis.getVoices()}}}catch(e){}}
 function clip(id){var k=id+'.'+lang;if(cache[k])return cache[k];var a=new Audio();a.preload='auto';a.addEventListener('error',function(){bad[k]=1});a.src='audio/'+k+'.mp3';cache[k]=a;return a}
 function preload(){
  cacheLang=lang;var ids=[];
  fetch('audio/narration_manifest.json').then(function(r){return r.json()}).then(function(m){ids=m.map(function(x){return x.id});var i=0;
   (function next(){if(cacheLang!==lang||i>=ids.length)return;clip(ids[i++]);(window.requestIdleCallback||function(f){setTimeout(f,40)})(next)})()}).catch(function(){})}
 function paint(on,btn){
  var h=document.querySelector('[data-act="speak"]');
  if(h){h.classList.toggle('stopmode',on&&(!btn||btn===h));h.setAttribute('aria-pressed',on&&(!btn||btn===h)?'true':'false');
   var u=h.querySelector('use');if(u)u.setAttribute('href',on&&(!btn||btn===h)?'#i-stop':'#i-spk')}
  document.querySelectorAll('[data-act="say"].playing,[data-act="pgsay"].playing,[data-act="vhear"].playing').forEach(function(b){b.classList.remove('playing');b.removeAttribute('aria-pressed')});
  if(on&&btn&&btn.dataset&&btn.dataset.act!=='speak'){btn.classList.add('playing');btn.setAttribute('aria-pressed','true')}}
 window.stopVoice=function(){
  try{if(window.speechSynthesis)speechSynthesis.cancel()}catch(e){}
  try{if(window.ChatVoice&&ChatVoice.stop)ChatVoice.stop()}catch(e){}
  if(cur){try{cur.pause();cur.currentTime=0}catch(e){}cur=null}
  curBtn=null;paint(false)};
 function done(){cur=null;curBtn=null;paint(false)}
 function say(t,id,btn){
  if(btn&&btn===curBtn){window.stopVoice();return}
  window.stopVoice();
  var k=id+'.'+lang;
  if(bad[k]){noVoice(t);return}
  var a=clip(id);cur=a;curBtn=btn||null;paint(true,btn);
  var early=a.readyState<2;
  if(early&&lang==='en'&&window.speechSynthesis){/* clip still loading: speak now, never wait */
   cur=null;var u=new SpeechSynthesisUtterance(t);u.lang='en-GB';u.onend=u.onerror=done;speechSynthesis.speak(u);return}
  a.onended=done;a.onerror=function(){bad[k]=1;done();noVoice(t)};
  try{a.currentTime=0}catch(e){}
  var p=a.play();if(p&&p.catch)p.catch(function(){if(cur===a){done();noVoice(t)}})}
 var lastBtn=null;
 document.addEventListener('click',function(e){lastBtn=e.target.closest?e.target.closest('[data-act]'):null},true);
 window.speakText=function(t,id){var b=lastBtn&&(lastBtn.dataset.act==='say'||lastBtn.dataset.act==='pgsay')?lastBtn:null;say(t,id,b)};
 window.togglePageSpeak=function(btn){
  if(curBtn===btn){window.stopVoice();return}
  if(lang==='bn'){toast(s('noBnTts'));return}
  if(!window.speechSynthesis){toast('No speech here');return}
  window.stopVoice();var el=document.getElementById('pg-'+cur_page());
  var u=new SpeechSynthesisUtterance(((el&&el.innerText)||'').slice(0,900));u.lang='en-GB';u.onend=u.onerror=done;
  curBtn=btn;paint(true,btn);speechSynthesis.speak(u)};
 function cur_page(){return window.cur}
 /* stop whenever the page changes (this also covers language and mode switches, which re-render through show) */
 var _show=window.show;window.show=function(p){window.stopVoice();if(document.body.dataset.mode==='officer'&&(p==='learn'||p==='pictures')){p='field';if(location.hash!=='#/field')history.replaceState(null,'','#/field')}
  if(lang!==cacheLang)preload();return _show(p)};
 var _vc=window.vidClose;window.vidClose=function(){window.stopVoice();return _vc()};
 document.addEventListener('visibilitychange',function(){if(document.hidden)window.stopVoice()});
 /* mode switch while sitting on a Farmer-only page: go home */
 var _am=window.applyMode;window.applyMode=function(){var r=_am();if(document.body.dataset.mode==='officer'&&(window.cur==='learn'||window.cur==='pictures')){history.replaceState(null,'','#/field');window.show('field')}return r};
 if(document.body.dataset.mode==='officer'&&(window.cur==='learn'||window.cur==='pictures'))window.show('field');
 function start(){warmVoices();setTimeout(preload,300)}
 if(document.readyState==='complete')start();else window.addEventListener('load',start);
})();
