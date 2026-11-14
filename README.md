# Portfolio

Personal site of Mohammad Taha Alhmad, AI Engineer. Each project shows its real architecture as a stage-by-stage trace, with decisions, evidence and limits.

It is a static page with no framework, tracking or third-party requests.

## Edit

All content lives in [content/profile.json](content/profile.json). Edit it, then rebuild:

```bash
python src/build.py
```

`unconfirmed` in that file lists facts the owner still has to confirm. Before a deploy, this must succeed:

```bash
python src/build.py --strict
```

## Replace the photograph

From the workspace root, crop so that no other people are visible:

```bash
tools/.venv/Scripts/python tools/prepare_photo.py "inputs/photo.jpg" --box LEFT TOP RIGHT BOTTOM
```

Then run `tools/.venv/Scripts/python tools/make_og.py` and `python src/build.py`.

## Test

```bash
pip install pytest
python -m pytest
```

The tests check the built page: links, headings, banned text, color contrast and the content security policy.
They do not replace looking at the page in a browser.
