# Fashionista (Streamlit app)

A GUI version of `wardrobe_app.ipynb`, with four tabs: **Closet**, **Today**, **Shop** and **Stylist**.

## Run it (Windows)
```powershell
cd path\to\streamlit_app
pip install -r requirements.txt
streamlit run app.py
```
Your browser opens at http://localhost:8501 with a sample closet. Tap **Start my own closet** to begin with an empty one.

## Turn on the LLM stylist (xAI Grok)
Without a key the Stylist tab runs in **Offline mode** and uses the built-in rules. To use Grok, run these in PowerShell:
```powershell
setx OPENAI_API_KEY "xai-..."          # your xAI API key (never put it in the code)
setx OPENAI_BASE_URL "https://api.x.ai/v1"
setx OPENAI_MODEL "grok-4.3"           # optional (this is the default); check docs.x.ai for current model names
```
`setx` only affects **new** windows, so close and reopen the terminal (or VS Code) and run `streamlit run app.py` again. The Stylist tab should then say **Online · model ...**. Any OpenAI-compatible provider works if you change `OPENAI_BASE_URL`.

Privacy note: in online mode, a summary of your closet and style profile is sent to the provider.

## Iteration 1 features
- **Stylist always builds a full look.** If your closet can't cover a slot for the occasion (e.g. no leggings for a workout), the reply still gives a complete outfit: the suitable pieces you own plus "Not in closet, shop this" cards, a short "why" line, and **Add missing to Shop list** (shown on the Shop tab). Works with Grok and offline.
- **AI photo tagging.** Uploading a photo pre-fills Type and Color ("Looks right? Save, or edit"). It first tries the vision model (secret `VISION_MODEL`, default = `OPENAI_MODEL`; set `VISION_TAGGING = "off"` to skip); if the model refuses images or errors, it falls back to offline dominant-colour detection (Pillow, ~30 named shades mapped to 12 colour groups) and a type guess from the file name / shape. A refused vision call is refunded and not retried until the app restarts.
- **Today occasion picker:** Work, Interview, Date, Workout, Weekend, using the same item rules as the Stylist. Interviews never get sneakers, running shoes or athletic pieces.
- **Saved closet.** See `storage.py`: the closet is saved as JSON on the app server under a random id kept in the URL (`?c=...`), so a refresh (or a bookmark) brings it back. Trade-offs: Streamlit Community Cloud's disk is ephemeral, so a redeploy/reboot/sleep clears saved closets; anyone with the full link can open that closet; only thumbnails are stored. (Browser localStorage would survive restarts but needs a third-party component and an extra rerun; a hosted database needs an account and secrets.) A saved-closet link also skips the class passcode on refresh.

## Files
## Files
- `app.py`: the Streamlit UI
- `wardrobe_core.py`: the logic (garments, outfit engine, style profile, gap analysis, chat stylist)
- `.streamlit/config.toml`: theme (cream `#f8f5f0`, terracotta `#c47a6c`)
- `storage.py`: saved closets (JSON per closet id; folder `FASHIONISTA_DATA_DIR`, default the system temp dir)
- `tagging.py`: photo auto-tagging (vision model + offline colour detection)
- `guards.py`: secrets, Grok budgets, passcode, photo checks (5 MB limit)
- `tests/`: automated tests (`pytest`), including Streamlit AppTest smoke tests in `tests/test_app.py`
