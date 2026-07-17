# cyberbara-cli

Command-line interface for CyberBara. Generate images, videos, audio, and music directly from your terminal with **API key auth only**.

This CLI is modeled after the ergonomics of `muapi-cli`, but it is intentionally simpler on auth:

- supported: **API key**
- not supported: email registration
- not supported: password login
- not supported: OTP auth flows

## Install

```bash
# pip
pip install cyberbara-cli

# npm
npm install -g cyberbara-cli
```

## Quick Start

```bash
cyberbara auth configure --api-key "YOUR_API_KEY"

cyberbara image generate "A cinematic product shot of a silver watch" --model nano-banana-2
cyberbara video generate "A creator-style portrait shot with realistic motion" --model seedance-2-stable
cyberbara audio generate "A short cinematic whoosh" --model suno-sound-v5-5
cyberbara music generate "Warm lo-fi study music" --model suno-music-v5
```

## Commands

- `cyberbara auth configure`
- `cyberbara auth whoami`
- `cyberbara auth logout`
- `cyberbara models list`
- `cyberbara account balance`
- `cyberbara account usage`
- `cyberbara image generate`
- `cyberbara image edit`
- `cyberbara video generate`
- `cyberbara video from-image`
- `cyberbara video from-video`
- `cyberbara audio generate`
- `cyberbara music generate`
- `cyberbara upload images`
- `cyberbara upload videos`
- `cyberbara task get`
- `cyberbara task wait`
- `cyberbara quote`
- `cyberbara raw`

## Notes

- Local image and video paths are uploaded automatically before generation.
- Generation commands quote credits first, then require confirmation unless `--yes` is set.
- Outputs can be auto-saved locally.
