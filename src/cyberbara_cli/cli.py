"""Command-line interface for CyberBara."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from cyberbara_cli.config import (
    API_KEY_ENV_VAR,
    clear_cached_api_key,
    current_api_key_info,
    resolve_api_key,
    setup_api_key,
)
from cyberbara_cli.constants import DEFAULT_BASE_URL, DEFAULT_OUTPUT_DIR
from cyberbara_cli.gateways import CyberbaraClient
from cyberbara_cli.output import print_payload
from cyberbara_cli.usecases.generation import generate_media_with_credit_guard
from cyberbara_cli.usecases.media_output import persist_and_open_task_output
from cyberbara_cli.usecases.wait_task import wait_for_task, wait_for_task_payload


DEFAULT_IMAGE_MODEL = "nano-banana-2"
DEFAULT_VIDEO_MODEL = "seedance-2-stable"
DEFAULT_VIDEO_IMAGE_MODEL = "seedance-2-mini"
DEFAULT_VIDEO_EDIT_MODEL = "seedance-2-fast-stable"
DEFAULT_AUDIO_MODEL = "suno-sound-v5-5"
DEFAULT_MUSIC_MODEL = "suno-music-v5"


def _extract_task_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    task_id = data.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        return task_id.strip()
    return None


def _collect_submitted_tasks(submit_payload: Any) -> list[dict[str, Any]]:
    single_task_id = _extract_task_id(submit_payload)
    if single_task_id:
        return [{"index": 1, "task_id": single_task_id, "estimated_credits": None}]

    if not isinstance(submit_payload, dict):
        return []
    data = submit_payload.get("data")
    if not isinstance(data, dict):
        return []
    items = data.get("items")
    if not isinstance(items, list):
        return []

    tasks: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        generation_response = item.get("generation_response")
        task_id = _extract_task_id(generation_response)
        if not task_id:
            continue
        tasks.append(
            {
                "index": index,
                "task_id": task_id,
                "estimated_credits": item.get("estimated_credits"),
            }
        )
    return tasks


def _finalize_submitted_tasks(
    *,
    client: CyberbaraClient,
    submit_payload: Any,
    interval: float,
    wait_timeout: int,
    timeout_per_request: int,
    save_outputs: bool,
    open_outputs: bool,
    output_dir: str,
) -> Any:
    tasks = _collect_submitted_tasks(submit_payload)
    if not tasks:
        return submit_payload

    final_items: list[dict[str, Any]] = []
    for task_meta in tasks:
        task_payload = wait_for_task_payload(
            client=client,
            task_id=task_meta["task_id"],
            interval=interval,
            timeout=wait_timeout,
            timeout_per_request=timeout_per_request,
        )
        saved_files: list[str] = []
        if save_outputs:
            saved_files = persist_and_open_task_output(
                task_payload=task_payload,
                output_dir=output_dir,
                open_files=open_outputs,
            )

        final_items.append(
            {
                "index": task_meta["index"],
                "task_id": task_meta["task_id"],
                "estimated_credits": task_meta.get("estimated_credits"),
                "saved_files": saved_files,
                "task_payload": task_payload,
            }
        )

    if len(final_items) == 1:
        return final_items[0]["task_payload"]

    return {"data": {"count": len(final_items), "items": final_items}}


def _normalize_url_or_upload(
    client: CyberbaraClient,
    value: str,
    *,
    kind: str,
    timeout: int,
) -> str:
    text = value.strip()
    if text.startswith(("http://", "https://")):
        return text

    path = Path(text).expanduser()
    if not path.is_file():
        raise SystemExit(f"{kind} file not found: {path}")

    if kind == "image":
        payload = client.upload_images([str(path)], timeout=timeout)
    elif kind == "video":
        payload = client.upload_videos([str(path)], timeout=timeout)
    else:
        raise SystemExit(f"Unsupported upload kind: {kind}")

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    urls = data.get("urls") if isinstance(data, dict) else None
    if not isinstance(urls, list) or not urls or not isinstance(urls[0], str):
        raise SystemExit(f"Upload response missing URL for {path}.")
    return urls[0]


def _common_generation_flags(cmd: argparse.ArgumentParser) -> None:
    cmd.add_argument("--yes", action="store_true", help="Skip interactive confirmation after quote.")
    cmd.add_argument("--async", dest="async_mode", action="store_true", help="Submit only, do not wait for final outputs.")
    cmd.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds.")
    cmd.add_argument("--wait-timeout", type=int, default=900, help="Max seconds to wait for completion.")
    cmd.add_argument("--timeout-per-request", type=int, default=120, help="HTTP timeout per polling request in seconds.")
    cmd.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help=f"Directory to save outputs (default: {DEFAULT_OUTPUT_DIR}).")
    cmd.add_argument("--no-save", action="store_true", help="Do not save output files locally.")
    cmd.add_argument("--no-open", action="store_true", help="Save output files but do not auto-open them.")


def _run_generation_command(
    *,
    client: CyberbaraClient,
    media_label: str,
    payload: dict[str, Any],
    yes: bool,
    async_mode: bool,
    interval: float,
    wait_timeout: int,
    timeout_per_request: int,
    save_outputs: bool,
    open_outputs: bool,
    output_dir: str,
    timeout: int,
    compact: bool,
) -> None:
    submit_payload = generate_media_with_credit_guard(
        client=client,
        media_label=media_label,
        payload_body=payload,
        yes=yes,
        timeout=timeout,
    )
    if async_mode:
        print_payload(submit_payload, compact)
        return

    final_payload = _finalize_submitted_tasks(
        client=client,
        submit_payload=submit_payload,
        interval=interval,
        wait_timeout=wait_timeout,
        timeout_per_request=timeout_per_request,
        save_outputs=save_outputs,
        open_outputs=open_outputs,
        output_dir=output_dir,
    )
    print_payload(final_payload, compact)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cyberbara",
        description="Generate images, videos, audio, and music with CyberBara using API key auth only.",
    )
    parser.add_argument("--api-key", default=None, help=f"CyberBara API key. Falls back to {API_KEY_ENV_VAR} or local cache.")
    parser.add_argument("--timeout", type=int, default=120, help="HTTP request timeout in seconds.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON.")

    subparsers = parser.add_subparsers(dest="group", required=True)

    auth = subparsers.add_parser("auth", help="Configure API key auth.")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    auth_configure = auth_sub.add_parser("configure", help="Save an API key locally.")
    auth_configure.add_argument("--api-key", dest="input_api_key", default=None, help="API key to save.")
    auth_configure.add_argument("--from-env", action="store_true", help=f"Read API key from {API_KEY_ENV_VAR}.")
    auth_sub.add_parser("whoami", help="Show the current configured API key (masked).")
    auth_sub.add_parser("logout", help="Delete the cached API key.")

    models = subparsers.add_parser("models", help="Model operations.")
    models_sub = models.add_subparsers(dest="models_command", required=True)
    models_list = models_sub.add_parser("list", help="List available models.")
    models_list.add_argument("--media-type", choices=["image", "video", "audio", "music"], help="Optional media type filter.")

    account = subparsers.add_parser("account", help="Account operations.")
    account_sub = account.add_subparsers(dest="account_command", required=True)
    account_sub.add_parser("balance", help="Show current credit balance.")
    usage = account_sub.add_parser("usage", help="Show usage history.")
    usage.add_argument("--page", type=int, default=1)
    usage.add_argument("--limit", type=int, default=20)
    usage.add_argument("--from-date")
    usage.add_argument("--to-date")

    quote = subparsers.add_parser("quote", help="Quote credits from a raw JSON request.")
    quote.add_argument("--json", help="Inline JSON payload.")
    quote.add_argument("--file", help="JSON payload file.")

    upload = subparsers.add_parser("upload", help="Upload local media.")
    upload_sub = upload.add_subparsers(dest="upload_command", required=True)
    up_images = upload_sub.add_parser("images", help="Upload image files.")
    up_images.add_argument("files", nargs="+")
    up_videos = upload_sub.add_parser("videos", help="Upload video files.")
    up_videos.add_argument("files", nargs="+")

    task = subparsers.add_parser("task", help="Task operations.")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    task_get = task_sub.add_parser("get", help="Fetch task status.")
    task_get.add_argument("task_id")
    task_wait = task_sub.add_parser("wait", help="Wait for task completion.")
    task_wait.add_argument("task_id")
    task_wait.add_argument("--interval", type=float, default=5.0)
    task_wait.add_argument("--timeout", type=int, default=900)
    task_wait.add_argument("--timeout-per-request", type=int, default=120)
    task_wait.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    task_wait.add_argument("--no-save", action="store_true")
    task_wait.add_argument("--no-open", action="store_true")

    image = subparsers.add_parser("image", help="Image generation commands.")
    image_sub = image.add_subparsers(dest="image_command", required=True)
    image_generate = image_sub.add_parser("generate", help="Text-to-image generation.")
    image_generate.add_argument("prompt")
    image_generate.add_argument("--model", default=DEFAULT_IMAGE_MODEL)
    image_generate.add_argument("--aspect-ratio")
    image_generate.add_argument("--resolution")
    image_generate.add_argument("--count", type=int)
    _common_generation_flags(image_generate)

    image_edit = image_sub.add_parser("edit", help="Image-to-image editing.")
    image_edit.add_argument("prompt")
    image_edit.add_argument("--model", default="nano-banana-pro")
    image_edit.add_argument("--image", action="append", required=True, help="Image URL or local path. Repeatable.")
    image_edit.add_argument("--aspect-ratio")
    image_edit.add_argument("--resolution")
    image_edit.add_argument("--count", type=int)
    _common_generation_flags(image_edit)

    video = subparsers.add_parser("video", help="Video generation commands.")
    video_sub = video.add_subparsers(dest="video_command", required=True)
    video_generate = video_sub.add_parser("generate", help="Text-to-video generation.")
    video_generate.add_argument("prompt")
    video_generate.add_argument("--model", default=DEFAULT_VIDEO_MODEL)
    video_generate.add_argument("--duration")
    video_generate.add_argument("--aspect-ratio")
    video_generate.add_argument("--resolution")
    _common_generation_flags(video_generate)

    video_from_image = video_sub.add_parser("from-image", help="Image-to-video generation.")
    video_from_image.add_argument("prompt")
    video_from_image.add_argument("--model", default=DEFAULT_VIDEO_IMAGE_MODEL)
    video_from_image.add_argument("--image", action="append", required=True, help="Image URL or local path. Repeatable.")
    video_from_image.add_argument("--duration")
    video_from_image.add_argument("--aspect-ratio")
    video_from_image.add_argument("--resolution")
    _common_generation_flags(video_from_image)

    video_from_video = video_sub.add_parser("from-video", help="Video-to-video generation.")
    video_from_video.add_argument("prompt")
    video_from_video.add_argument("--model", default=DEFAULT_VIDEO_EDIT_MODEL)
    video_from_video.add_argument("--video", action="append", required=True, help="Video URL or local path. Repeatable.")
    video_from_video.add_argument("--duration")
    video_from_video.add_argument("--resolution")
    _common_generation_flags(video_from_video)

    audio = subparsers.add_parser("audio", help="Audio generation commands.")
    audio_sub = audio.add_subparsers(dest="audio_command", required=True)
    audio_generate = audio_sub.add_parser("generate", help="Text-to-audio generation.")
    audio_generate.add_argument("prompt")
    audio_generate.add_argument("--model", default=DEFAULT_AUDIO_MODEL)
    audio_generate.add_argument("--duration")
    _common_generation_flags(audio_generate)

    music = subparsers.add_parser("music", help="Music generation commands.")
    music_sub = music.add_subparsers(dest="music_command", required=True)
    music_generate = music_sub.add_parser("generate", help="Text-to-music generation.")
    music_generate.add_argument("prompt")
    music_generate.add_argument("--model", default=DEFAULT_MUSIC_MODEL)
    music_generate.add_argument("--instrumental", action="store_true")
    music_generate.add_argument("--lyrics")
    _common_generation_flags(music_generate)

    raw = subparsers.add_parser("raw", help="Call any endpoint directly.")
    raw.add_argument("--method", required=True)
    raw.add_argument("--path", required=True)
    raw.add_argument("--json")
    raw.add_argument("--file")

    return parser


def _load_json_payload(inline_json: str | None, json_file: str | None) -> Any:
    import json

    if inline_json:
        try:
            return json.loads(inline_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid --json payload: {exc}") from exc
    if json_file:
        path = Path(json_file)
        if not path.is_file():
            raise SystemExit(f"JSON file not found: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON file {path}: {exc}") from exc
    raise SystemExit("JSON payload is required. Use --json or --file.")


def _maybe_load_json_payload(inline_json: str | None, json_file: str | None) -> Any | None:
    if inline_json or json_file:
        return _load_json_payload(inline_json, json_file)
    return None


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.group == "auth":
        if args.auth_command == "configure":
            payload = {"data": setup_api_key(input_api_key=args.input_api_key, from_env=args.from_env)}
            print_payload(payload, args.compact)
            return
        if args.auth_command == "whoami":
            payload = {"data": current_api_key_info(args.api_key)}
            print_payload(payload, args.compact)
            return
        if args.auth_command == "logout":
            payload = {"data": {"removed": clear_cached_api_key()}}
            print_payload(payload, args.compact)
            return

    api_key = resolve_api_key(args.api_key)
    client = CyberbaraClient(api_key=api_key, base_url=DEFAULT_BASE_URL)

    if args.group == "models":
        payload = client.models(media_type=args.media_type, timeout=args.timeout)
        print_payload(payload, args.compact)
        return

    if args.group == "account":
        if args.account_command == "balance":
            print_payload(client.balance(timeout=args.timeout), args.compact)
            return
        if args.account_command == "usage":
            payload = client.usage(
                page=args.page,
                limit=args.limit,
                from_date=args.from_date,
                to_date=args.to_date,
                timeout=args.timeout,
            )
            print_payload(payload, args.compact)
            return

    if args.group == "quote":
        payload = _load_json_payload(args.json, args.file)
        print_payload(client.quote(payload, timeout=args.timeout), args.compact)
        return

    if args.group == "upload":
        if args.upload_command == "images":
            print_payload(client.upload_images(args.files, timeout=args.timeout), args.compact)
            return
        if args.upload_command == "videos":
            print_payload(client.upload_videos(args.files, timeout=args.timeout), args.compact)
            return

    if args.group == "task":
        if args.task_command == "get":
            print_payload(client.task(args.task_id, timeout=args.timeout), args.compact)
            return
        if args.task_command == "wait":
            wait_for_task(
                client=client,
                task_id=args.task_id,
                interval=args.interval,
                timeout=args.timeout,
                timeout_per_request=args.timeout_per_request,
                compact=args.compact,
                auto_save=not args.no_save,
                open_files=not args.no_open,
                output_dir=args.output_dir,
            )
            return

    if args.group == "image":
        payload: dict[str, Any] = {
            "model": args.model,
            "prompt": args.prompt,
            "scene": "text-to-image" if args.image_command == "generate" else "image-to-image",
            "options": {},
        }
        if args.aspect_ratio:
            payload["options"]["aspect_ratio"] = args.aspect_ratio
        if args.resolution:
            payload["options"]["resolution"] = args.resolution
        if args.count:
            payload["options"]["count"] = args.count
        if args.image_command == "edit":
            payload["options"]["image_input"] = [
                _normalize_url_or_upload(client, image, kind="image", timeout=args.timeout)
                for image in args.image
            ]
        _run_generation_command(
            client=client,
            media_label="image",
            payload=payload,
            yes=args.yes,
            async_mode=args.async_mode,
            interval=args.interval,
            wait_timeout=args.wait_timeout,
            timeout_per_request=args.timeout_per_request,
            save_outputs=not args.no_save,
            open_outputs=not args.no_open,
            output_dir=args.output_dir,
            timeout=args.timeout,
            compact=args.compact,
        )
        return

    if args.group == "video":
        payload = {
            "model": args.model,
            "prompt": args.prompt,
            "scene": "text-to-video",
            "options": {},
        }
        if args.duration:
            payload["options"]["duration"] = args.duration
        if getattr(args, "aspect_ratio", None):
            payload["options"]["aspect_ratio"] = args.aspect_ratio
        if getattr(args, "resolution", None):
            payload["options"]["resolution"] = args.resolution

        if args.video_command == "from-image":
            payload["scene"] = "image-to-video"
            payload["options"]["image_input"] = [
                _normalize_url_or_upload(client, image, kind="image", timeout=args.timeout)
                for image in args.image
            ]
        elif args.video_command == "from-video":
            payload["scene"] = "video-to-video"
            payload["options"]["video_input"] = [
                _normalize_url_or_upload(client, video, kind="video", timeout=args.timeout)
                for video in args.video
            ]

        _run_generation_command(
            client=client,
            media_label="video",
            payload=payload,
            yes=args.yes,
            async_mode=args.async_mode,
            interval=args.interval,
            wait_timeout=args.wait_timeout,
            timeout_per_request=args.timeout_per_request,
            save_outputs=not args.no_save,
            open_outputs=not args.no_open,
            output_dir=args.output_dir,
            timeout=args.timeout,
            compact=args.compact,
        )
        return

    if args.group == "audio":
        payload = {
            "model": args.model,
            "prompt": args.prompt,
            "scene": "text-to-audio",
            "options": {},
        }
        if args.duration:
            payload["options"]["duration"] = args.duration
        _run_generation_command(
            client=client,
            media_label="audio",
            payload=payload,
            yes=args.yes,
            async_mode=args.async_mode,
            interval=args.interval,
            wait_timeout=args.wait_timeout,
            timeout_per_request=args.timeout_per_request,
            save_outputs=not args.no_save,
            open_outputs=not args.no_open,
            output_dir=args.output_dir,
            timeout=args.timeout,
            compact=args.compact,
        )
        return

    if args.group == "music":
        payload = {
            "model": args.model,
            "prompt": args.prompt,
            "scene": "text-to-music",
            "options": {},
        }
        if args.instrumental:
            payload["options"]["instrumental"] = True
        if args.lyrics:
            payload["options"]["lyrics"] = args.lyrics
        _run_generation_command(
            client=client,
            media_label="music",
            payload=payload,
            yes=args.yes,
            async_mode=args.async_mode,
            interval=args.interval,
            wait_timeout=args.wait_timeout,
            timeout_per_request=args.timeout_per_request,
            save_outputs=not args.no_save,
            open_outputs=not args.no_open,
            output_dir=args.output_dir,
            timeout=args.timeout,
            compact=args.compact,
        )
        return

    if args.group == "raw":
        payload = _maybe_load_json_payload(args.json, args.file)
        print_payload(
            client.raw(method=args.method, path=args.path, payload=payload, timeout=args.timeout),
            args.compact,
        )
        return

    parser.error(f"Unsupported command group: {args.group}")


if __name__ == "__main__":
    main()
