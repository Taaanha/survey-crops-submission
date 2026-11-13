/* web/app/chat_voice.js
   Chat voice helpers. Renders only; no API calls, no computing of numbers.
   Mic language follows the page language (bn-BD or en-US); the speaker reads
   the answer in the same language and hides itself if no voice exists.
   Bangla text here needs native review. Not yet wired into a chat panel. */
(function (root) {
  'use strict';

  function recogLang(pageLang) { return pageLang === 'bn' ? 'bn-BD' : 'en-US'; }

  /* Same rule as src/agents/language.py detect_language (the server is the
     source of truth; this only picks the mic/speaker before an answer). */
  function detectLang(text, pageLang) {
    var bn = (String(text).match(/[ঀ-৿]/g) || []).length;
    var en = (String(text).match(/[A-Za-z]/g) || []).length;
    if (bn > en) return 'bn';
    if (en > bn) return 'en';
    return pageLang === 'bn' ? 'bn' : 'en';
  }

  function findVoice(lang) {
    if (!('speechSynthesis' in root)) return null;
    var re = lang === 'bn' ? /^bn/i : /^en/i;
    var vs = root.speechSynthesis.getVoices() || [];
    for (var i = 0; i < vs.length; i++) if (re.test(vs[i].lang)) return vs[i];
    return null;
  }

  /* Show the speaker button only if a voice exists for this language. */
  function syncSpeakerButton(btn, lang) {
    if (!btn) return;
    btn.hidden = !findVoice(lang);
  }

  function speakAnswer(text, lang) {
    var v = findVoice(lang);
    if (!v) return false;
    root.speechSynthesis.cancel();
    var u = new root.SpeechSynthesisUtterance(text);
    u.voice = v; u.lang = v.lang; u.rate = 0.95;
    root.speechSynthesis.speak(u);
    return true;
  }

  /* Returns {start, stop} or null when the browser has no recognition.
     onText(text, lang) is called with the transcript. */
  function makeMic(getPageLang, onText, onError) {
    var SR = root.SpeechRecognition || root.webkitSpeechRecognition;
    if (!SR) return null;
    var rec = null;
    return {
      start: function () {
        rec = new SR();
        rec.lang = recogLang(getPageLang());
        rec.interimResults = false;
        rec.onresult = function (e) {
          var t = e.results[0][0].transcript;
          onText(t, detectLang(t, getPageLang()));
        };
        rec.onerror = function (e) { onError && onError(e.error); };
        rec.start();
      },
      stop: function () { if (rec) rec.stop(); }
    };
  }

  root.ChatVoice = { recogLang: recogLang, detectLang: detectLang,
    findVoice: findVoice, syncSpeakerButton: syncSpeakerButton,
    speakAnswer: speakAnswer, makeMic: makeMic };
  if (typeof module !== 'undefined') module.exports = root.ChatVoice;
})(typeof window !== 'undefined' ? window : globalThis);
