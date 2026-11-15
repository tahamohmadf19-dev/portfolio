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

## Contact form

The form posts to Web3Forms (`contact_form` in `content/profile.json`). With JavaScript it sends JSON with `fetch`; without it, the browser posts the same form and Web3Forms redirects to `contact-sent.html`. The page's Content Security Policy allows exactly one extra origin, `https://api.web3forms.com`, for `connect-src` and `form-action`. `python src/build.py --strict` refuses to build while the access key is empty.

**The access key is public by design.** Web3Forms documents it as safe to place in the page, and the form cannot work without it, so it is in `content/profile.json` and in the built `index.html`. It identifies where messages go. It does not sign in to the Web3Forms account.

Limits of that design on the free plan (checked on web3forms.com, 2026-11-15):

- Anyone can copy the key from the page and send messages to the same inbox. Restricting the key to this domain is a paid feature.
- The free plan allows 250 submissions a month. Abuse could use that up and block real messages until the month resets.
- Web3Forms filters spam on its side. The page adds a honeypot (`botcheck`), a 3-second check and duplicate prevention. There is no captcha, so that no third-party script runs.

If the key is abused: create a new one at web3forms.com, put it in `content/profile.json`, rebuild with `--strict`, test, and publish. A copied old key keeps working until it is disabled in the Web3Forms account (or by Web3Forms support), so disable it there as well. The email address the key sends to is already public on the site.
