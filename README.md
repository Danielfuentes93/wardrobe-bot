# Fashionista (Streamlit app)

A GUI version of `wardrobe_app.ipynb`, with four tabs: **Closet**, **Today**, **Shop** and **Stylist**.

## Run it (Windows)
```powershell
cd path\to\streamlit_app
pip install -r requirements.txt
streamlit run app.py
```
Your browser opens at http://localhost:8501. The first time it runs, the app sets up a sample closet in `data\`.

## Turn on the LLM stylist (xAI Grok)
Without a key the Stylist tab runs in **Offline mode** and uses the built-in rules. To use Grok, run these in PowerShell:
```powershell
setx OPENAI_API_KEY "xai-..."          # your xAI API key (never put it in the code)
setx OPENAI_BASE_URL "https://api.x.ai/v1"
setx OPENAI_MODEL "grok-3-mini"        # optional; check docs.x.ai for current model names
```
`setx` only affects **new** windows, so close and reopen the terminal (or VS Code) and run `streamlit run app.py` again. The Stylist tab should then say **Online · model ...**. Any OpenAI-compatible provider works if you change `OPENAI_BASE_URL`.

Privacy note: in online mode, a summary of your closet and style profile is sent to the provider.

## Files
- `app.py`: the Streamlit UI
- `wardrobe_core.py`: the logic (garments, outfit engine, style profile, gap analysis, chat stylist)
- `.streamlit/config.toml`: theme (cream `#f8f5f0`, terracotta `#c47a6c`)
- `data/`: `closet.json`, `style_profile.json`, `photos/` (created automatically). Use **Reset demo data** in the sidebar to start over.
- `tests/test_app.py`: automated tests (`python tests/test_app.py`)
