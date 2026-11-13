/* Survey Crops website config (modes.html). The only place the server address is set.
   - API_BASE: the live API on Render (the free server sleeps and can take about a minute to wake).
   - API_SAMPLES: real sample answers saved in web/mock/live/, used only if the live server cannot
     be reached. Pages that use them keep the DEMO badge.
   For testing, add ?api=<url> to the page address to use a different server. */
window.API_BASE = "https://cropshift-api-eg28.onrender.com";
window.API_SAMPLES = "mock/live/";
try { var _o = new URLSearchParams(location.search).get("api"); if (_o) window.API_BASE = _o; } catch (e) {}
