from __future__ import annotations

import base64
import hashlib
import logging
import re
import time
from datetime import datetime, timezone
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GithubServiceError(RuntimeError):
    pass


class GithubRateLimitError(GithubServiceError):
    pass


class GithubService:
    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "skillvault-mvp",
        }
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        self.client = httpx.Client(base_url=self.BASE_URL, headers=headers, timeout=30)
        self._last_request_at_monotonic: float | None = None

    @staticmethod
    def parse_repo_url(repo_url: str) -> tuple[str, str]:
        pattern = r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"
        match = re.match(pattern, repo_url.strip())
        if not match:
            raise GithubServiceError("Invalid GitHub repo URL")
        return match.group(1), match.group(2)

    @staticmethod
    def normalize_repo_full_name(repo_url: str) -> str:
        owner, repo = GithubService.parse_repo_url(repo_url)
        return f"{owner.lower()}/{repo.lower()}"

    def _respect_min_request_interval(self) -> None:
        if self._last_request_at_monotonic is None:
            return
        min_interval = max(0, settings.github_min_request_interval_seconds)
        elapsed = time.monotonic() - self._last_request_at_monotonic
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    @staticmethod
    def _header_int(headers: httpx.Headers, key: str) -> int | None:
        value = headers.get(key)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _reset_datetime(headers: httpx.Headers) -> datetime | None:
        reset_ts = GithubService._header_int(headers, "x-ratelimit-reset")
        if reset_ts is None:
            return None
        return datetime.fromtimestamp(reset_ts, tz=timezone.utc)

    def _log_rate_limit(self, headers: httpx.Headers) -> None:
        remaining = self._header_int(headers, "x-ratelimit-remaining")
        reset_at = self._reset_datetime(headers)
        limit = self._header_int(headers, "x-ratelimit-limit")
        used = self._header_int(headers, "x-ratelimit-used")
        logger.info(
            "GitHub rate limit: remaining=%s used=%s limit=%s reset_at=%s",
            remaining,
            used,
            limit,
            reset_at.isoformat() if reset_at else None,
        )

    @staticmethod
    def _is_secondary_rate_limit(status_code: int, body_text: str) -> bool:
        if status_code not in {403, 429}:
            return False
        lower = (body_text or "").lower()
        return "secondary rate limit" in lower or "abuse detection" in lower

    def _is_rate_limited(self, response: httpx.Response) -> bool:
        if response.status_code == 429:
            return True
        if response.status_code != 403:
            return False
        if response.headers.get("retry-after"):
            return True
        remaining = self._header_int(response.headers, "x-ratelimit-remaining")
        if remaining == 0:
            return True
        body = response.text.lower()
        return "rate limit" in body or "abuse detection" in body

    def _sleep_until_reset(self, headers: httpx.Headers, *, fallback_seconds: int = 60) -> int:
        reset_at = self._reset_datetime(headers)
        if reset_at is None:
            sleep_seconds = fallback_seconds
        else:
            delta = (reset_at - datetime.now(timezone.utc)).total_seconds()
            sleep_seconds = max(0, int(delta)) + settings.github_rate_limit_sleep_buffer_seconds
        time.sleep(sleep_seconds)
        return sleep_seconds

    def _maybe_proactive_sleep(self, headers: httpx.Headers) -> None:
        remaining = self._header_int(headers, "x-ratelimit-remaining")
        if remaining is None:
            return
        if remaining <= settings.github_rate_limit_remaining_threshold:
            slept = self._sleep_until_reset(headers)
            logger.warning(
                "GitHub remaining=%s <= threshold=%s, proactive sleep=%ss",
                remaining,
                settings.github_rate_limit_remaining_threshold,
                slept,
            )

    def _rate_limit_backoff_seconds(self, response: httpx.Response, attempt: int) -> int:
        retry_after = self._header_int(response.headers, "retry-after")
        if retry_after is not None:
            return max(1, retry_after)

        remaining = self._header_int(response.headers, "x-ratelimit-remaining")
        if remaining == 0 and self._reset_datetime(response.headers):
            return self._sleep_until_reset(response.headers)

        if self._is_secondary_rate_limit(response.status_code, response.text):
            # 60, 120, 240...
            return 60 * (2**attempt)

        return 60

    def _github_request(self, path: str, *, method: str = "GET", attempt: int = 0) -> dict:
        self._respect_min_request_interval()
        self._last_request_at_monotonic = time.monotonic()
        try:
            response = self.client.request(method, path)
        except httpx.RequestError as exc:
            if attempt < settings.github_max_retries:
                backoff = 2**attempt
                logger.warning("GitHub network error on %s, retry in %ss: %s", path, backoff, exc)
                time.sleep(backoff)
                return self._github_request(path, method=method, attempt=attempt + 1)
            raise GithubServiceError(f"GitHub API request failed after retries: {exc}") from exc

        self._log_rate_limit(response.headers)

        if 200 <= response.status_code < 300:
            self._maybe_proactive_sleep(response.headers)
            return response.json()

        if self._is_rate_limited(response):
            remaining = self._header_int(response.headers, "x-ratelimit-remaining")
            reset_at = self._reset_datetime(response.headers)
            is_secondary = self._is_secondary_rate_limit(response.status_code, response.text)
            if attempt < settings.github_max_retries:
                backoff_seconds = self._rate_limit_backoff_seconds(response, attempt)
                if retry_after := response.headers.get("retry-after"):
                    logger.warning("GitHub rate limited. retry-after=%s, sleep=%ss", retry_after, backoff_seconds)
                elif is_secondary:
                    logger.warning("GitHub secondary rate limit triggered. Backoff applied. sleep=%ss", backoff_seconds)
                else:
                    logger.warning(
                        "GitHub rate limit exceeded. remaining=%s reset_at=%s sleep=%ss",
                        remaining,
                        reset_at.isoformat() if reset_at else None,
                        backoff_seconds,
                    )
                if response.headers.get("retry-after") or (remaining != 0):
                    time.sleep(backoff_seconds)
                return self._github_request(path, method=method, attempt=attempt + 1)

            if is_secondary:
                raise GithubRateLimitError("GitHub secondary rate limit triggered. Backoff applied.")
            raise GithubRateLimitError(
                "GitHub rate limit exceeded. "
                f"remaining={remaining} reset_at={reset_at.isoformat() if reset_at else None}"
            )

        if response.status_code >= 500 and attempt < settings.github_max_retries:
            backoff = 2**attempt
            logger.warning("GitHub API %s on %s, retry in %ss", response.status_code, path, backoff)
            time.sleep(backoff)
            return self._github_request(path, method=method, attempt=attempt + 1)

        if response.status_code == 404:
            raise GithubServiceError(f"GitHub API 404: {path}")
        if response.status_code == 403:
            raise GithubServiceError(f"GitHub API forbidden (403): {path}")
        raise GithubServiceError(f"GitHub API error {response.status_code}: {response.text}")

    def fetch_repo_metadata(self, owner: str, repo: str) -> dict:
        return self._github_request(f"/repos/{owner}/{repo}")

    def fetch_readme(self, owner: str, repo: str) -> dict:
        payload = self._github_request(f"/repos/{owner}/{repo}/readme")
        encoded = payload.get("content", "")
        content = base64.b64decode(encoded).decode("utf-8", errors="ignore") if encoded else ""
        return {
            "content": content,
            "path": payload.get("path", "README.md"),
            "download_url": payload.get("download_url"),
            "sha": payload.get("sha"),
        }

    def fetch_license(self, owner: str, repo: str) -> str | None:
        try:
            payload = self._github_request(f"/repos/{owner}/{repo}/license")
            license_info = payload.get("license") or {}
            return license_info.get("spdx_id") or license_info.get("name")
        except GithubServiceError:
            return None

    def fetch_latest_commit_sha(self, owner: str, repo: str, branch: str) -> str | None:
        payload = self._github_request(f"/repos/{owner}/{repo}/commits/{branch}")
        return payload.get("sha")

    @staticmethod
    def calculate_content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def normalize_repo_data(self, repo_url: str) -> dict:
        owner, repo = self.parse_repo_url(repo_url)
        meta = self.fetch_repo_metadata(owner, repo)
        readme = self.fetch_readme(owner, repo)
        branch = meta.get("default_branch") or "main"
        commit_sha = self.fetch_latest_commit_sha(owner, repo, branch)
        license_name = (meta.get("license") or {}).get("spdx_id") or self.fetch_license(owner, repo)

        content_hash = self.calculate_content_hash(readme["content"])
        collected_at = datetime.now(timezone.utc).isoformat()

        return {
            "full_name": meta.get("full_name"),
            "description": meta.get("description"),
            "stars": meta.get("stargazers_count", 0),
            "forks": meta.get("forks_count", 0),
            "language": meta.get("language"),
            "topics": meta.get("topics") or [],
            "license": license_name,
            "default_branch": branch,
            "pushed_at": meta.get("pushed_at"),
            "html_url": meta.get("html_url"),
            "readme_content": readme["content"],
            "readme_source_url": readme.get("download_url") or f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md",
            "commit_sha": commit_sha,
            "content_hash": content_hash,
            "collected_at": collected_at,
            "repo": meta.get("full_name"),
            "file_path": readme.get("path", "README.md"),
            "source_url": meta.get("html_url"),
            "source_type": "github_api",
            "owner": owner,
            "metadata": {
                "usage_scope": "personal_reference_only" if not license_name or license_name in {"NOASSERTION", "NONE"} else "license_defined",
                "repo_url": repo_url,
            },
        }
