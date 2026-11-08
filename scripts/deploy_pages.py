#!/usr/bin/env python3
"""Deploy a built static directory to an existing Cloudflare Pages project.

Cloudflare's Pages Direct Upload API is a three-step protocol:

1. exchange the account API token for a short-lived upload JWT;
2. ask which content hashes are missing, upload only those assets;
3. create a deployment with a manifest mapping paths to hashes.

The official 'cf' CLI creates the Pages deployment (it supports Direct
Upload manifests and the special '_headers' file), while this script uses
the documented Direct Upload API to exchange the token for an upload JWT,
upload only missing BLAKE3-addressed assets, poll the deployment, and verify
the published bytes.  It does not use Wrangler or any npm package at
runtime; 'scripts/blake3.py' implements the exact asset hash Cloudflare uses.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from blake3 import pages_hash

API_BASE = "https://api.cloudflare.com/client/v4"
DEFAULT_ACCOUNT_ID = "09c58146832fbea01ce12d3e316a1d4d"
DEFAULT_PROJECT = "lingxifox-apps"
DEFAULT_PAGES_URL = "https://lingxifox-apps.pages.dev/"
DEFAULT_CUSTOM_URL = "https://apps.lingxifox.cn/"


class ApiError(RuntimeError):
    """A Cloudflare API request failed."""


def log(message: str) -> None:
    print(message, flush=True)


def _request(
    method: str,
    path: str,
    token: str,
    *,
    json_body: Any | None = None,
    data: bytes | None = None,
    content_type: str | None = None,
    timeout: int = 90,
    retries: int = 4,
) -> bytes:
    """Perform an API request, retrying transient failures.

    The token is only placed in the Authorization header.  It is never logged
    or included in an exception message.
    """
    url = API_BASE + path
    body = data
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "LingXiFox-apps-site-deploy/1.0",
    }
    if json_body is not None:
        body = json.dumps(json_body, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if content_type:
        headers["Content-Type"] = content_type

    last_error: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:2000]
            last_error = ApiError(
                f"{method} {path} returned HTTP {exc.code}: {detail}"
            )
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                wait = 2 ** attempt
                log(f"  transient HTTP {exc.code}; retrying in {wait}s")
                time.sleep(wait)
                continue
            raise last_error from None
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = ApiError(f"{method} {path} failed: {exc}")
            if attempt < retries - 1:
                wait = 2 ** attempt
                log(f"  network error; retrying in {wait}s")
                time.sleep(wait)
                continue
            raise last_error from None
    raise last_error or ApiError(f"{method} {path} failed")


def _json_request(
    method: str,
    path: str,
    token: str,
    *,
    json_body: Any | None = None,
    data: bytes | None = None,
    content_type: str | None = None,
    timeout: int = 90,
    retries: int = 4,
) -> Any:
    raw = _request(
        method,
        path,
        token,
        json_body=json_body,
        data=data,
        content_type=content_type,
        timeout=timeout,
        retries=retries,
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError(f"{method} {path} returned non-JSON data") from exc
    if not payload.get("success", False):
        errors = payload.get("errors") or payload.get("messages") or []
        raise ApiError(f"{method} {path} failed: {json.dumps(errors)[:2000]}")
    return payload.get("result")


def _content_type(path: Path) -> str:
    if path.suffix == ".webmanifest":
        return "application/manifest+json"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _collect_files(dist: Path) -> list[Path]:
    if not dist.is_dir():
        raise SystemExit(f"dist directory not found: {dist}")
    files = sorted((path for path in dist.rglob("*") if path.is_file()), key=lambda p: p.as_posix())
    if not files:
        raise SystemExit(f"dist directory is empty: {dist}")
    return files


def _manifest(dist: Path, files: list[Path]) -> tuple[dict[str, str], dict[str, Path]]:
    manifest: dict[str, str] = {}
    by_hash: dict[str, Path] = {}
    for path in files:
        relative = path.relative_to(dist).as_posix()
        key = "/" + relative
        digest = pages_hash(str(path))
        manifest[key] = digest
        by_hash[digest] = path
    return manifest, by_hash


def _upload_assets(
    token: str, account_id: str, project: str, files_by_hash: dict[str, Path]
) -> None:
    upload_token = _json_request(
        "GET",
        f"/accounts/{account_id}/pages/projects/{project}/upload-token",
        token,
    )
    if not isinstance(upload_token, dict) or not upload_token.get("jwt"):
        raise ApiError("upload-token response did not contain a JWT")

    hashes = list(files_by_hash)
    missing = _json_request(
        "POST",
        "/pages/assets/check-missing",
        upload_token["jwt"],
        json_body={"hashes": hashes},
    )
    missing_hashes = [item for item in (missing or []) if item in files_by_hash]
    log(f"Assets: {len(hashes)} total, {len(missing_hashes)} missing")

    batch_size = 8
    for start in range(0, len(missing_hashes), batch_size):
        batch = missing_hashes[start : start + batch_size]
        payload = []
        for digest in batch:
            path = files_by_hash[digest]
            payload.append(
                {
                    "key": digest,
                    "value": base64.b64encode(path.read_bytes()).decode("ascii"),
                    "metadata": {"contentType": _content_type(path)},
                    "base64": True,
                }
            )
        result = _json_request(
            "POST",
            "/pages/assets/upload",
            upload_token["jwt"],
            json_body=payload,
            timeout=180,
        )
        result = result or {}
        unsuccessful = result.get("unsuccessful_keys") or []
        if unsuccessful:
            raise ApiError(f"asset upload rejected {len(unsuccessful)} key(s)")
        log(
            f"  uploaded {result.get('successful_key_count', len(batch))}/"
            f"{len(batch)} asset(s)"
        )

    try:
        _json_request(
            "POST",
            "/pages/assets/upsert-hashes",
            upload_token["jwt"],
            json_body={"hashes": hashes},
        )
    except ApiError as exc:
        log(f"  warning: upsert-hashes failed (deployment can continue): {exc}")


def _cf_binary() -> str:
    configured = os.environ.get("CF_BIN")
    if configured:
        return configured
    binary = shutil.which("cf")
    if not binary:
        raise ApiError(
            "cf CLI not found. Install Node.js 22 or newer and run "
            "'npm install --global cf'."
        )
    return binary


def _parse_cf_json(output: str) -> dict[str, Any]:
    text = output.strip()
    if not text:
        raise ApiError("cf CLI returned no JSON output")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ApiError("cf CLI returned non-JSON output") from None
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ApiError("cf CLI returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise ApiError("cf CLI returned an unexpected JSON value")
    result = payload.get("result", payload)
    if not isinstance(result, dict):
        raise ApiError("cf CLI response did not contain a deployment object")
    return result


def _create_deployment(
    token: str,
    account_id: str,
    project: str,
    manifest: dict[str, str],
    dist: Path,
    *,
    branch: str,
    commit_hash: str,
    commit_message: str,
    commit_dirty: bool,
) -> dict[str, Any]:
    if (dist / "_redirects").is_file():
        raise ApiError(
            "cf pages deployments create cannot attach _redirects; "
            "extend the deployer before adding that file"
        )

    command = [
        _cf_binary(),
        "pages",
        "deployments",
        "create",
        project,
        "--manifest",
        json.dumps(manifest, separators=(",", ":"), sort_keys=True),
        "--branch",
        branch,
        "--commit-message",
        commit_message,
        "--commit-dirty",
        "true" if commit_dirty else "false",
    ]
    if commit_hash:
        command.extend(["--commit-hash", commit_hash])

    headers = dist / "_headers"
    if headers.is_file():
        command.extend(["--file", str(headers.resolve())])

    env = os.environ.copy()
    env["CLOUDFLARE_API_TOKEN"] = token
    env["CLOUDFLARE_ACCOUNT_ID"] = account_id

    log("Creating deployment via cf CLI")
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
    except FileNotFoundError:
        raise ApiError("cf CLI not found on PATH") from None
    except subprocess.TimeoutExpired:
        raise ApiError("cf pages deployments create timed out after 180s") from None

    if completed.returncode != 0:
        detail = (completed.stderr.strip() or completed.stdout.strip() or "no output")
        raise ApiError(
            f"cf pages deployments create failed (exit {completed.returncode}): "
            f"{detail[:2000]}"
        )

    result = _parse_cf_json(completed.stdout)
    if not result.get("id"):
        raise ApiError("cf CLI deployment response did not contain an id")
    return result


def _poll_deployment(
    token: str, account_id: str, project: str, deployment_id: str, timeout: int
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_status = ""
    while time.monotonic() < deadline:
        result = _json_request(
            "GET",
            f"/accounts/{account_id}/pages/projects/{project}/deployments/{deployment_id}",
            token,
        )
        if not isinstance(result, dict):
            raise ApiError("deployment lookup returned an unexpected response")
        stage = result.get("latest_stage") or {}
        status = str(stage.get("status") or "")
        if status != last_status:
            log(f"Deployment stage: {status or 'unknown'}")
            last_status = status
        if status == "success":
            return result
        if status in {"failure", "canceled", "cancelled"}:
            raise ApiError(f"deployment {deployment_id} ended with status {status}")
        time.sleep(5)
    raise ApiError(f"deployment {deployment_id} did not finish within {timeout}s")


def _fetch(url: str, timeout: int = 30) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "LingXiFox-apps-site-deploy/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _verify(url: str, local_index: bytes, attempts: int = 6) -> None:
    expected = hashlib.sha256(local_index).hexdigest()
    last: tuple[int, str] | None = None
    for attempt in range(attempts):
        status, body = _fetch(url)
        actual = hashlib.sha256(body).hexdigest()
        if status == 200 and actual == expected:
            log(f"Verified {url}: HTTP 200, SHA-256 {actual[:12]}...")
            return
        last = (status, actual)
        if attempt < attempts - 1:
            time.sleep(5)
    status, actual = last or (0, "")
    raise ApiError(
        f"verification failed for {url}: HTTP {status}, "
        f"SHA-256 {actual[:12]}... (expected {expected[:12]}...)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy dist/ to Cloudflare Pages Direct Upload")
    parser.add_argument("--dist", default="dist", help="built static directory")
    parser.add_argument("--account", default=os.environ.get("CLOUDFLARE_ACCOUNT_ID") or DEFAULT_ACCOUNT_ID)
    parser.add_argument("--project", default=os.environ.get("CLOUDFLARE_PAGES_PROJECT") or DEFAULT_PROJECT)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--commit-hash", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--commit-message", default=os.environ.get("GITHUB_COMMIT_MESSAGE", ""))
    parser.add_argument("--commit-dirty", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--pages-url", default=DEFAULT_PAGES_URL)
    parser.add_argument("--custom-url", default=DEFAULT_CUSTOM_URL)
    parser.add_argument("--skip-custom-verify", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        print(
            "CLOUDFLARE_API_TOKEN is required. Create a scoped token with "
            "Account > Cloudflare Pages > Edit permission and store it as a "
            "repository secret.",
            file=sys.stderr,
        )
        return 2

    dist = Path(args.dist).resolve()
    files = _collect_files(dist)
    manifest, files_by_hash = _manifest(dist, files)
    log(f"Deploying {len(files)} files from {dist} to {args.project} ({args.branch})")

    try:
        _upload_assets(token, args.account, args.project, files_by_hash)
        deployment = _create_deployment(
            token,
            args.account,
            args.project,
            manifest,
            dist,
            branch=args.branch,
            commit_hash=args.commit_hash,
            commit_message=args.commit_message or "Deploy from apps-site CLI",
            commit_dirty=args.commit_dirty,
        )
        deployment_id = str(deployment["id"])
        log(f"Created deployment {deployment_id}")
        finished = _poll_deployment(
            token, args.account, args.project, deployment_id, args.timeout
        )
        deployment_url = finished.get("url") or deployment.get("url") or ""
        if deployment_url:
            log(f"Deployment URL: {deployment_url}")

        local_index = (dist / "index.html").read_bytes()
        _verify(args.pages_url, local_index)
        if not args.skip_custom_verify:
            _verify(args.custom_url, local_index)
    except ApiError as exc:
        print(f"deploy: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
