# cyberbara-cli

Official command-line interface for CyberBara. Generate images, videos, audio, and music directly from your terminal with **API key auth only**.

This CLI is intentionally simpler than account-driven tools:

- supported: **API key**
- not supported: email registration
- not supported: password login
- not supported: OTP auth flows

If you already have a CyberBara API key, this is the fastest path from terminal to generation.

## Why Use It

- Generate images, videos, audio, and music without leaving the terminal
- Upload local reference images and videos automatically
- Quote credits before submission
- Wait for tasks, save outputs locally, and optionally auto-open them
- Use one API key across direct CLI, scripts, and automation

## Install

```bash
# Python package
pip install cyberbara-cli

# npm package
npm install -g cyberbara-cli
```

Notes:

- The npm package is a thin wrapper around the Python CLI and requires `python3` to be available on your machine.
- The CLI talks to the CyberBara public API at `https://cyberbara.com`.

## Quick Start

Create an account and get an [API key](https://cyberbara.com/settings/apikeys?utm_source=github&utm_medium=referral&utm_campaign=cyberbara-cli&utm_content=quick-start). Then configure it once:

```bash
cyberbara auth configure --api-key "YOUR_API_KEY"
```

Check the saved key in a new terminal process:

```bash
cyberbara auth whoami
```

Check current models and balance before generating:

```bash
cyberbara models list --media-type image
cyberbara account balance
```

Generate across media types (each command quotes credits and asks for confirmation):

```bash
cyberbara image generate "A cinematic product shot of a silver watch" \
  --model nano-banana-2 \
  --aspect-ratio 1:1 \
  --resolution 1k

cyberbara video generate "A creator-style portrait shot with realistic motion" \
  --model seedance-2-stable \
  --duration 10 \
  --aspect-ratio 9:16 \
  --resolution 1080p

cyberbara audio generate "A short cinematic whoosh" \
  --model suno-sound-v5-5

cyberbara music generate "Warm lo-fi study music" \
  --model suno-music-v5 \
  --instrumental
```

## Auth

### Configure API key

```bash
cyberbara auth configure --api-key "YOUR_API_KEY"
```

Or load from environment:

```bash
export CYBERBARA_API_KEY="YOUR_API_KEY"
cyberbara auth configure --from-env
```

### Check current key

```bash
cyberbara auth whoami
```

### Remove cached key

```bash
cyberbara auth logout
```

Resolution order for API keys:

1. `--api-key`
2. `CYBERBARA_API_KEY`
3. cached key at `~/.config/cyberbara/api_key`

## Commands

### `cyberbara auth`

| Command | Description |
| --- | --- |
| `cyberbara auth configure --api-key ...` | Save an API key locally |
| `cyberbara auth configure --from-env` | Save API key from `CYBERBARA_API_KEY` |
| `cyberbara auth whoami` | Show current API key source and masked value |
| `cyberbara auth logout` | Delete cached API key |

### `cyberbara models`

| Command | Description |
| --- | --- |
| `cyberbara models list` | List all available public models |
| `cyberbara models list --media-type video` | Filter by media type |

### `cyberbara account`

| Command | Description |
| --- | --- |
| `cyberbara account balance` | Show current credit balance |
| `cyberbara account usage` | Show recent usage records |

### `cyberbara image`

| Command | Description |
| --- | --- |
| `cyberbara image generate <prompt>` | Text-to-image generation |
| `cyberbara image edit <prompt> --image <path-or-url>` | Image-to-image generation |

Examples:

```bash
cyberbara image generate "Luxury perfume bottle on reflective glass" \
  --model nano-banana-2 \
  --aspect-ratio 4:5 \
  --resolution 1k

cyberbara image edit "Turn this sketch into a polished product render" \
  --model nano-banana-pro \
  --image ./concept.png \
  --aspect-ratio 1:1 \
  --resolution 1k
```

### `cyberbara video`

| Command | Description |
| --- | --- |
| `cyberbara video generate <prompt>` | Text-to-video generation |
| `cyberbara video from-image <prompt> --image <path-or-url>` | Image-to-video generation |
| `cyberbara video from-video <prompt> --video <path-or-url>` | Video-to-video generation |

Examples:

```bash
cyberbara video generate "Creator-style portrait with realistic motion and natural skin texture" \
  --model seedance-2-stable \
  --duration 10 \
  --aspect-ratio 9:16 \
  --resolution 1080p

cyberbara video from-image "Quick portrait motion with subtle blinking and head turn" \
  --model seedance-2-mini \
  --image ./portrait.png \
  --duration 5 \
  --aspect-ratio 9:16

cyberbara video from-video "Keep the motion but restyle it as a glossy commercial clip" \
  --model seedance-2-fast-stable \
  --video ./input.mp4 \
  --duration 10
```

### `cyberbara audio`

| Command | Description |
| --- | --- |
| `cyberbara audio generate <prompt>` | Text-to-audio generation |

Example:

```bash
cyberbara audio generate "A short cinematic whoosh with soft digital sparkle" \
  --model suno-sound-v5-5
```

### `cyberbara music`

| Command | Description |
| --- | --- |
| `cyberbara music generate <prompt>` | Text-to-music generation |

Examples:

```bash
cyberbara music generate "Warm lo-fi study music with mellow keys" \
  --model suno-music-v5 \
  --instrumental

cyberbara music generate "Dreamy synth-pop chorus with female vocals" \
  --model suno-music-v5 \
  --lyrics "City lights are fading into blue..."
```

### `cyberbara upload`

| Command | Description |
| --- | --- |
| `cyberbara upload images <files...>` | Upload local image files |
| `cyberbara upload videos <files...>` | Upload local video files |

### `cyberbara task`

| Command | Description |
| --- | --- |
| `cyberbara task get <task_id>` | Fetch current task payload |
| `cyberbara task wait <task_id>` | Poll until completion, then optionally save outputs |

### `cyberbara quote`

Quote credits using a raw JSON body:

```bash
cyberbara quote --json '{
  "model": "seedance-2-stable",
  "media_type": "video",
  "scene": "text-to-video",
  "prompt": "Creator-style portrait motion",
  "options": { "duration": "10", "aspect_ratio": "9:16", "resolution": "1080p" }
}'
```

### `cyberbara raw`

Call any CyberBara public endpoint directly:

```bash
cyberbara raw --method GET --path /api/v1/models
```

## Common Flags

These flags apply to most generation commands:

| Flag | Description |
| --- | --- |
| `--yes` | Skip interactive confirmation after quote |
| `--async` | Submit task and return immediately |
| `--interval` | Polling interval while waiting |
| `--wait-timeout` | Maximum total wait time |
| `--timeout-per-request` | HTTP timeout for each polling request |
| `--output-dir` | Local directory for saved outputs |
| `--no-save` | Do not save outputs locally |
| `--no-open` | Save outputs but do not auto-open them |
| `--compact` | Print compact JSON |

## Behavior Notes

- Local image and video paths are uploaded automatically before generation.
- Generation commands quote credits first, then require confirmation unless `--yes` is set.
- Final outputs are saved under `media_outputs` by default.
- `cyberbara task wait` exits non-zero when a task fails or times out.
- The CLI only supports API key auth. There is no account registration or password flow built into this tool.

## Related Resources

- [CyberBara API](https://cyberbara.com/api)
- [CyberBara API Reference](https://cyberbara.com/docs/api-reference)
- [Ultimate AI Media Generator Skill](https://github.com/ZeroLu/Ultimate-AI-Media-Generator-Skill)

## Troubleshooting your first run

- `python3` not found after npm install: install Python 3.10 or newer, then run `cyberbara --help` again. The npm launcher uses Python.
- Key missing after configuration: verify with `cyberbara auth whoami` in a new process. If using version 0.1.0, set `CYBERBARA_API_KEY` as a workaround; that version can report a saved key without writing it.
- HTTP 401/403: check the key, account access, and any network restrictions. Do not paste your key into an issue.
- Model rejected: list current models for that media type instead of assuming an example model is still available.
- Non-interactive generation stops after quoting: run interactively to review the quote, or use `--yes` after accepting the cost.
- Task times out: retain its task ID and use `cyberbara task get <task_id>` before submitting another paid task.

A quote is an estimate in credits, not a measured currency cost. Use `cyberbara account usage` and billing records to check actual consumption.

For maintainers, offline first-run regression checks require no API key or generation spend:

```bash
python3 -m unittest discover -s tests -v
```
