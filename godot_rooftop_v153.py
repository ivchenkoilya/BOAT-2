from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


LOGGER = logging.getLogger(__name__)
PUBLIC_BUILD_URL = os.getenv(
    "GODOT_ROOFTOP_BUILD_URL",
    "https://disk.yandex.ru/d/eAlpDbXh9AfiRg",
).strip()
BUILD_VERSION = "godot-rooftop-2026-07-22-v2"
BASE_DIR = Path(__file__).resolve().parent
TARGET_DIR = BASE_DIR / "games" / "rooftop"
PERSIST_ROOT = (
    Path("/data") / "godot_rooftop_v153"
    if Path("/data").exists()
    else BASE_DIR / ".runtime" / "godot_rooftop_v153"
)
CACHE_DIR = PERSIST_ROOT / BUILD_VERSION
CACHE_BUILD_DIR = CACHE_DIR / "build"
MARKER_PATH = CACHE_DIR / "build.json"


TELEGRAM_HEAD = r'''
<script src="https://telegram.org/js/telegram-web-app.js?63"></script>
<script>
window.addEventListener("load", function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (!tg) return;

  tg.expand();
  if (tg.disableVerticalSwipes) tg.disableVerticalSwipes();
  tg.setHeaderColor?.("#070511");
  tg.setBackgroundColor?.("#070511");

  if (tg.BackButton) {
    tg.BackButton.show();
    tg.BackButton.onClick(function () {
      window.location.href = "/games/";
    });
  }

  tg.ready();
});
</script>
'''.strip()


def _is_valid_build(directory: Path) -> bool:
    required = {
        "index.html": 1_000,
        "index.js": 100_000,
        "index.wasm": 30_000_000,
        "index.pck": 10_000_000,
    }
    for name, minimum_size in required.items():
        path = directory / name
        if not path.is_file() or path.stat().st_size < minimum_size:
            return False
    return True


def _public_download_url(public_url: str) -> str:
    api_url = (
        "https://cloud-api.yandex.net/v1/disk/public/resources/download?"
        + urllib.parse.urlencode({"public_key": public_url})
    )
    request = urllib.request.Request(
        api_url,
        headers={"User-Agent": "Mozilla/5.0 MainHeroBot/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    href = str(payload.get("href") or "").strip()
    if not href:
        raise RuntimeError("Яндекс Диск не вернул ссылку скачивания Godot-сборки.")
    return href


def _download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 MainHeroBot/1.0"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)


def _patch_index(index_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    html = html.replace('<html lang="en">', '<html lang="ru">', 1)
    html = html.replace(
        "<title>hero runner</title>",
        "<title>Главный герой — Бег по крышам</title>",
        1,
    )
    if "telegram-web-app.js" not in html:
        closing_head = "\n\t</head>"
        if closing_head in html:
            html = html.replace(
                closing_head,
                f"\n{TELEGRAM_HEAD}{closing_head}",
                1,
            )
        else:
            html = html.replace("</head>", f"{TELEGRAM_HEAD}\n</head>", 1)
    index_path.write_text(html, encoding="utf-8")


def _prepare_cache() -> None:
    if _is_valid_build(CACHE_BUILD_DIR):
        return
    if not PUBLIC_BUILD_URL:
        raise RuntimeError("GODOT_ROOFTOP_BUILD_URL не задан.")

    PERSIST_ROOT.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="godot-rooftop-", dir=PERSIST_ROOT))
    archive_path = work_dir / "web_build.zip"
    extracted_dir = work_dir / "extracted"
    prepared_dir = work_dir / "prepared"

    try:
        download_url = _public_download_url(PUBLIC_BUILD_URL)
        _download_file(download_url, archive_path)

        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extracted_dir)

        source_dir = extracted_dir / "web_build"
        if not source_dir.is_dir():
            source_dir = extracted_dir

        prepared_dir.mkdir(parents=True, exist_ok=True)
        for source_path in source_dir.iterdir():
            if not source_path.is_file() or source_path.name.endswith(".import"):
                continue
            shutil.copy2(source_path, prepared_dir / source_path.name)

        _patch_index(prepared_dir / "index.html")
        if not _is_valid_build(prepared_dir):
            raise RuntimeError("Скачанный архив не похож на полную Web-сборку Godot.")

        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(prepared_dir), str(CACHE_BUILD_DIR))
        MARKER_PATH.write_text(
            json.dumps(
                {
                    "version": BUILD_VERSION,
                    "source": PUBLIC_BUILD_URL,
                    "wasm_size": (CACHE_BUILD_DIR / "index.wasm").stat().st_size,
                    "pck_size": (CACHE_BUILD_DIR / "index.pck").stat().st_size,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _activate_build() -> None:
    """Copy the cached build into the served directory.

    aiohttp static routes may reject files reached through a symlink outside the
    configured web root. That allowed index.html to open while index.js, WASM
    and PCK stayed unavailable, producing a completely black Telegram screen.
    A normal directory copy avoids that restriction.
    """
    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = TARGET_DIR.with_name(f"{TARGET_DIR.name}.new")

    if staging_dir.is_symlink():
        staging_dir.unlink(missing_ok=True)
    elif staging_dir.exists():
        shutil.rmtree(staging_dir)

    shutil.copytree(CACHE_BUILD_DIR, staging_dir)

    if TARGET_DIR.is_symlink():
        TARGET_DIR.unlink(missing_ok=True)
    elif TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)

    staging_dir.replace(TARGET_DIR)


def install_godot_rooftop() -> None:
    """Download, verify and activate the Godot Web build before aiohttp starts."""
    try:
        _prepare_cache()
        _activate_build()
        LOGGER.info(
            "Godot rooftop build activated: %s (%s)",
            BUILD_VERSION,
            TARGET_DIR,
        )
    except Exception:
        # The old HTML game remains available when an external download fails.
        LOGGER.exception("Could not activate the Godot rooftop build; keeping fallback game.")
