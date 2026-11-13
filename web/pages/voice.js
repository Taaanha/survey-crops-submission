/* Voice lines for the newer pages (risk calendar, warnings, El Nino context, data, model, strategies, evidence).
   Each line has an id; the page plays audio/{id}.{lang}.mp3 and, if that file is missing, shows "Voice file not added yet"
   (Bangla never uses the phone's robot voice). The same lines are in audio/narration_manifest.json, which is what
   notebooks/make_voice.py reads to make the mp3 files. tests/test_voice_manifest.py checks the two lists match.
   Lines contain no numbers and no promises about the weather: those come from the server and change.
   The Bangla is AI-written and needs native review. Uses globals from modes.html: lang, bi, esc, speakText. */
var PV = {
 "page-risk": {"en": "This table shows how many past seasons had a problem for each sowing date. Grey means we could not check it.", "bn": "এই ছকে দেখানো হয়েছে প্রতিটি বপনের তারিখে অতীতের কতটি মৌসুমে সমস্যা হয়েছে। ধূসর মানে আমরা যাচাই করতে পারিনি।"},
 "page-warnings": {"en": "These are weather warnings for the next few days, and what you can do. Today they are example data.", "bn": "এগুলো আগামী কয়েক দিনের আবহাওয়া সতর্কতা, আর আপনি কী করতে পারেন। আজ এগুলো উদাহরণ তথ্য।"},
 "page-enso": {"en": "This compares El Niño years with all years. It is context from past seasons, not a forecast.", "bn": "এখানে এল নিনো বছরের সঙ্গে সব বছরের তুলনা। এটি অতীতের প্রেক্ষাপট, পূর্বাভাস নয়।"},
 "page-strategies": {"en": "Pick what you grow now. We show other ways to rotate your crops, tested on past seasons. Fewer problem years is better.", "bn": "এখন কী চাষ করেন তা বেছে নিন। অতীতের মৌসুমে পরীক্ষা করা ফসল ঘোরানোর অন্য উপায় দেখানো হয়েছে। সমস্যার বছর কম হলে ভালো।"},
 "page-data": {"en": "This page lists the data we use and how much of it we really have. Missing data is marked, never shown as zero.", "bn": "এই পাতায় আমাদের ব্যবহৃত ডেটা এবং তার কতটা আসলে আছে তা দেখানো হয়েছে। যা নেই তা চিহ্নিত, কখনও শূন্য নয়।"},
 "page-model": {"en": "These are test results of our models on seasons they had not seen. The sample is small, so the ranges are wide.", "bn": "এগুলো আমাদের মডেলের পরীক্ষার ফলাফল, যে মৌসুম তারা আগে দেখেনি তার ওপর। নমুনা ছোট, তাই পরিসীমা বড়।"},
 "page-evidence": {"en": "This table compares the options on the same past seasons: problem years and water needed.", "bn": "এই ছকে একই অতীত মৌসুমে বিকল্পগুলোর তুলনা: সমস্যার বছর ও পানি কত লাগে।"}
};
function voiceBtn(id){if(!PV[id])return '';return ' <button class="pill" data-act="pgsay" data-v="'+id+'" aria-label="'+esc(bi('Hear this','এটি শুনুন'))+'" title="'+esc(bi('Hear this','এটি শুনুন'))+'"><svg class="ic"><use href="#i-spk"/></svg></button>'}
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-act="pgsay"]');if(!b)return;var l=PV[b.dataset.v];if(l)speakText(l[lang]||l.en,b.dataset.v)});
