/* Future features page (#/future). Static: no server call, no numbers, nothing computed.
   Explains the accounts / saved-field-history feature the team did not have time to build.
   Uses globals from modes.html: lang, esc, bi, ic. */
(function(){var c=document.createElement('style');c.textContent=
 '.ff-hero{position:relative;overflow:hidden;border:1px solid rgba(242,193,78,.45);border-radius:24px;padding:22px 20px;margin:12px 0 6px;background:radial-gradient(120% 140% at 100% 0%,rgba(242,193,78,.16),transparent 55%),radial-gradient(90% 120% at 0% 100%,rgba(43,179,163,.2),transparent 60%),linear-gradient(170deg,rgba(255,255,255,.09),rgba(255,255,255,.03))}'+
 '.ff-hero h1{font-size:clamp(1.55rem,5.6vw,2.3rem);margin:8px 0 8px}.ff-hero p{color:var(--mute);margin:0;max-width:62ch}'+
 '.ff-chip{display:inline-flex;align-items:center;gap:6px;margin-top:14px;padding:4px 12px;border-radius:99px;border:1px solid rgba(242,193,78,.5);background:rgba(242,193,78,.12);color:var(--gold);font-size:.78rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase}'+
 '.ff-sec{display:flex;align-items:center;gap:10px;margin:28px 0 12px}.ff-sec h2{margin:0;font-size:1.2rem}.ff-sec::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,var(--line),transparent)}'+
 '.ff-grid{display:grid;gap:12px}@media(min-width:760px){.ff-grid.two{grid-template-columns:1fr 1fr}.ff-grid.three{grid-template-columns:repeat(3,1fr)}}'+
 '.ff-card{border:1px solid var(--line);border-radius:20px;padding:18px;background:linear-gradient(170deg,rgba(255,255,255,.08),rgba(255,255,255,.025))}'+
 '.ff-card h3{margin:10px 0 6px}.ff-card p{margin:0;color:var(--mute);font-size:.95em}'+
 '.ff-ico{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;background:rgba(242,193,78,.13);color:var(--gold);border:1px solid rgba(242,193,78,.3)}'+
 '.ff-ico.leaf{background:rgba(123,211,137,.13);color:var(--leaf);border-color:rgba(123,211,137,.35)}.ff-ico.water{background:rgba(79,195,247,.13);color:var(--water);border-color:rgba(79,195,247,.35)}'+
 '.ff-ico svg{width:22px;height:22px}'+
 '.ff-card ul{list-style:none;margin:10px 0 0;padding:0;display:grid;gap:8px}.ff-card li{position:relative;padding-left:20px;color:var(--ink);font-size:.93em}.ff-card li::before{content:"";position:absolute;left:2px;top:.55em;width:8px;height:8px;border-radius:50%;background:var(--leaf)}'+
 '.ff-steps{counter-reset:ff;display:grid;gap:0;margin:0;padding:0;list-style:none}'+
 '.ff-steps li{counter-increment:ff;position:relative;padding:0 0 20px 54px}.ff-steps li:last-child{padding-bottom:0}'+
 '.ff-steps li::before{content:counter(ff);position:absolute;left:0;top:0;width:36px;height:36px;border-radius:50%;display:grid;place-items:center;font:700 1rem var(--head);color:#10202A;background:var(--gold)}'+
 '.ff-steps li::after{content:"";position:absolute;left:17px;top:40px;bottom:4px;width:2px;background:linear-gradient(var(--line),transparent)}.ff-steps li:last-child::after{display:none}'+
 '.ff-steps b{display:block;font-family:var(--head);margin-bottom:2px}.ff-steps span{color:var(--mute);font-size:.95em}'+
 '.ff-trust{border-left:4px solid var(--leaf);background:rgba(123,211,137,.08);border-radius:14px;padding:14px 16px}.ff-trust b{font-family:var(--head)}.ff-trust p{margin:6px 0 0;color:var(--mute);font-size:.95em}'+
 '.ff-foot{margin-top:24px;text-align:center;color:var(--mute);font-size:.88em}'+
 '.ff-sat{position:absolute;right:-8px;top:-6px;width:130px;opacity:.5;pointer-events:none}@media(max-width:520px){.ff-sat{width:90px}}';
 document.head.appendChild(c)})();

function ffSec(t){return '<div class="ff-sec"><h2>'+esc(t)+'</h2></div>'}
function ffCard(ico,cls,t,p){return '<div class="ff-card"><div class="ff-ico '+cls+'">'+ic(ico)+'</div><h3>'+esc(t)+'</h3><p>'+esc(p)+'</p></div>'}
function ffList(ico,cls,t,items){return '<div class="ff-card"><div class="ff-ico '+cls+'">'+ic(ico)+'</div><h3>'+esc(t)+'</h3><ul>'+items.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ul></div>'}

function renderFuture(){
 var h='';
 h+='<div class="eyebrow">'+esc(bi('Future features','ভবিষ্যৎ সুবিধা'))+'</div>'+
 '<div class="ff-hero">'+(window.SATART||'').replace('class="satart"','class="ff-sat"')+
 '<h1>'+esc(bi('A planner that learns your field, season after season','এমন পরিকল্পনা যা মৌসুমে মৌসুমে আপনার জমিকে আরও চেনে'))+'</h1>'+
 '<p>'+esc(bi('Today, Survey Crops uses NASA satellite data, soil and the answers you give each time. Accounts for farmers and agriculture officers are the next step. They would let the app keep each field’s history and give better suggestions over time.','আজ Survey Crops NASA-র স্যাটেলাইট তথ্য, মাটি এবং প্রতিবার আপনার দেওয়া উত্তর ব্যবহার করে। কৃষক ও কৃষি কর্মকর্তাদের জন্য অ্যাকাউন্ট হলো পরের ধাপ। এতে অ্যাপ প্রতিটি জমির ইতিহাস মনে রাখবে এবং সময়ের সাথে আরও ভালো পরামর্শ দেবে।'))+'</p>'+
 '<span class="ff-chip">'+esc(bi('Planned, not built yet','পরিকল্পনায় আছে, এখনো তৈরি হয়নি'))+'</span></div>';

 h+=ffSec(bi('Sign-up and saved fields','সাইন-আপ ও সংরক্ষিত জমি'));
 h+='<div class="ff-grid two">'+
 ffList('field','leaf',bi('For farmers','কৃষকদের জন্য'),lang==='bn'?
  ['প্রতিটি জমি একবার নাম দিয়ে সংরক্ষণ, প্রতিবার আবার লিখতে হবে না','আগের মৌসুমে কী লাগিয়েছিলেন ও কীভাবে, তা আবার দেখা','নিজের ফলন জানানো ও রেটিং দেওয়া, এবং চাইলে অন্যদের সাথে ভাগ করা','আপনার ফলাফল অ্যালগরিদমকে আরও ভালো হতে সাহায্য করে','বন্যার পর জমির অবস্থা জানিয়ে আপডেট করা পরিকল্পনা']:
  ['Save each field once, with no re-typing every visit','Revisit what you planted in earlier seasons, and how you grew it','Rate your yield and, if you wish, share it with others','Your results help the algorithm get better for everyone','Updated plans after floodwater leaves, using what you reported'])+
 ffList('info','water',bi('For agriculture officers','কৃষি কর্মকর্তাদের জন্য'),lang==='bn'?
  ['নিজের এলাকার জমি ও কৃষকের তালিকা এক জায়গায়','কোন এলাকায় কোন ফসল ভালো বা খারাপ গেল তার সারসংক্ষেপ','বন্যার পর ক্ষতির খবর দ্রুত সংগ্রহ','স্যাটেলাইট ক্ষতির মানচিত্রের সাথে মাঠের খবর মেলানো']:
  ['One place for the fields and farmers in your area','A summary of which crops did well or badly where','Faster collection of flood-damage reports','Field reports checked against the satellite damage map'])+
 '</div>';

 h+=ffSec(bi('How it would help future suggestions','এটি কীভাবে ভবিষ্যতের পরামর্শ ভালো করবে'));
 h+='<div class="card"><ol class="ff-steps">'+
 [[bi('Farmers record what happened','কৃষক কী হলো তা লিখে রাখেন'),bi('Crop sown and how it was grown, rough harvest date, any flood or dry spell, and a yield rating at the end of the season.','কোন ফসল ও কীভাবে বোনা হলো, মোটামুটি কাটার তারিখ, বন্যা বা খরা, এবং মৌসুম শেষে ফলনের রেটিং।')],
  [bi('Records are joined with NASA data','রেকর্ড NASA তথ্যের সাথে মেলানো হয়'),bi('Each season is placed next to rainfall, soil moisture and flood scenes for that area.','প্রতিটি মৌসুম ওই এলাকার বৃষ্টি, মাটির আর্দ্রতা ও বন্যার ছবির পাশে রাখা হয়।')],
  [bi('The rotation tests get sharper','ফসল-ঘূর্ণনের পরীক্ষা আরও নির্ভুল হয়'),bi('Real outcomes from real fields can sit beside the 24 past seasons we test on today.','বাস্তব জমির ফলাফল আজকের ২৪টি অতীত মৌসুমের পরীক্ষার পাশে যুক্ত হতে পারে।')],
  [bi('Suggestions fit your field better','পরামর্শ আপনার জমির সাথে আরও মানানসই হয়'),bi('Plans lean on what happened on fields like yours, and we say how many records back each one. Your own history stays one tap away to revisit.','আপনার মতো জমিতে কী হয়েছে তার ওপর ভিত্তি করে পরিকল্পনা হয়, আর কতগুলো রেকর্ডের ওপর ভিত্তি তা আমরা জানাই। আপনার নিজের ইতিহাস এক ট্যাপেই দেখা যাবে।')]
 ].map(function(x){return '<li><b>'+esc(x[0])+'</b><span>'+esc(x[1])+'</span></li>'}).join('')+'</ol></div>';

 h+=ffSec(bi('Our promises about your data','আপনার তথ্য নিয়ে আমাদের অঙ্গীকার'));
 h+='<div class="ff-grid three">'+
 ffCard('info','leaf',bi('Your choice','আপনার সিদ্ধান্ত'),bi('Sign-up would be optional. The planner would keep working without an account, as it does today.','সাইন-আপ ঐচ্ছিক হবে। আজকের মতোই অ্যাকাউন্ট ছাড়াও পরিকল্পনাকারী কাজ করবে।'))+
 ffCard('field','water',bi('Your field, your record','আপনার জমি, আপনার রেকর্ড'),bi('You could see, correct and delete what is saved about your fields.','আপনার জমি সম্পর্কে যা সংরক্ষিত, তা দেখা, ঠিক করা ও মুছে ফেলা যাবে।'))+
 ffCard('alert','',bi('Shared only as a summary','শুধু সারসংক্ষেপ হিসেবে ভাগ হবে'),bi('Learning would use grouped results, not names or exact plot locations.','শেখার কাজে গোষ্ঠীবদ্ধ ফলাফল ব্যবহার হবে, নাম বা জমির সঠিক অবস্থান নয়।'))+
 '</div>';

 h+=ffSec(bi('Also on the roadmap','রোডম্যাপে আরও আছে'));
 h+='<div class="ff-grid two">'+
 ffCard('pin','leaf',bi('More districts','আরও জেলা'),bi('Live today in Cumilla, Feni, Brahmanbaria, Noakhali and Sylhet. Chattogram, Khulna, Rajshahi and Barishal are planned next. Other places stay in basic mode, with NASA weather and soil moisture only.','আজ চালু আছে কুমিল্লা, ফেনী, ব্রাহ্মণবাড়িয়া, নোয়াখালী ও সিলেটে। এরপর পরিকল্পনায় আছে চট্টগ্রাম, খুলনা, রাজশাহী ও বরিশাল। অন্য জায়গায় সাধারণ ধাপ থাকবে, শুধু NASA-র আবহাওয়া ও মাটির আর্দ্রতা নিয়ে।'))+
 ffCard('rot','',bi('Sharper field-level view','জমি-স্তরে আরও স্পষ্ট চিত্র'),bi('A 30 m water profile for individual fields, so more numbers can say “your field” and fewer say “the area around your field”.','আলাদা জমির জন্য ৩০ মিটারের পানির চিত্র, যাতে আরও বেশি সংখ্যা “আপনার জমি” বলতে পারে, “জমির আশপাশের এলাকা” নয়।'))+
 '</div>';

 h+='<p class="ff-foot">'+esc(bi('These features are not part of the current app. This page describes where we want to take it.','এই সুবিধাগুলো বর্তমান অ্যাপে নেই। এই পাতায় আমরা কোথায় পৌঁছাতে চাই তা বলা হয়েছে।'))+'</p>';
 var e=document.getElementById('pg-future');if(e)e.innerHTML=h;
}
window.renderFuture=renderFuture;
