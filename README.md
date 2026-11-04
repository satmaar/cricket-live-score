# cricket-live-score

Capture a rendered Cricbuzz score card with Playwright's synchronous Python API.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Run

The default run opens Chromium visibly so you can watch the page load, waits for
the score element, prints its text, and saves a full-page screenshot as
`score.png`.

```sh
python cricbuzz_score.py
```

For headless use, or to change the screenshot path and wait limit:

```sh
python cricbuzz_score.py --headless --screenshot score.png --timeout 20000
```

If Cricbuzz has no score card, the script reports that state and still saves a
screenshot. A browser or navigation failure is reported on stderr with a
nonzero exit status.

## Checks

```sh
python -m unittest discover -s tests -v
```
