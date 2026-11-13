# make_voice.py - run in Google Colab (free). Makes audio/{id}.{lang}.mp3 from narration_manifest.json using ElevenLabs.
# BEFORE RUNNING: on elevenlabs.io check (1) your free credits cover ~4,800 characters, (2) the free plan's licence allows
# your use (many free plans need credit/attribution or forbid commercial use), (3) Bengali works with the model below.
# NOTE (13 Nov 2026): on 13 Nov a free account got 402 'paid_plan_required' for voices added from the Voice Library via the API.
# Free accounts can only use premade voices (check Bengali quality first, one clip, with a native speaker), or the team lead pays.
# If anything costs money, STOP and tell the team lead. Never paste your key into the website or GitHub.
import json, os, requests
try:
    from google.colab import userdata
    KEY = userdata.get('ELEVEN_API_KEY')      # Colab: left sidebar > key icon > add secret ELEVEN_API_KEY
except Exception:
    KEY = os.environ.get('ELEVEN_API_KEY')
assert KEY, 'Add your ElevenLabs key as a Colab secret named ELEVEN_API_KEY'
VOICE = {'en': 'eXpIbVcVbLo8ZJQDlDnl', 'bn': 'AyRPttdqoCVGu6Ae3lPx'}   # pick in the ElevenLabs voice library (filter: Bengali)
MODEL = 'eleven_v3'    # check the docs: the model must list Bengali
LANGS = ['bn', 'en']
man = json.load(open('narration_manifest.json', encoding='utf-8'))
total = sum(len(m[l]) for m in man for l in LANGS)
print('clips:', len(man) * len(LANGS), ' characters:', total)
if input('Does your ElevenLabs plan cover this for free? type yes: ').strip().lower() != 'yes':
    raise SystemExit('Stopped. Nothing was generated.')
os.makedirs('audio', exist_ok=True)
for m in man:
    for l in LANGS:
        out = f"audio/{m['id']}.{l}.mp3"
        if os.path.exists(out): continue
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE[l]}",
            headers={'xi-api-key': KEY, 'Content-Type': 'application/json'},
            json={'text': m[l], 'model_id': MODEL}, timeout=120)
        if r.status_code != 200:
            print('FAILED', out, r.status_code, r.text[:200]); raise SystemExit
        open(out, 'wb').write(r.content); print('ok', out)
print('Done. Upload the audio folder next to modes.html (or into web/audio/).')
