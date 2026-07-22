from __future__ import annotations

import html
import json
import logging
import os
import shutil
import tempfile
import threading
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


LOGGER = logging.getLogger(__name__)
PUBLIC_BUILD_URL = os.getenv(
    "GODOT_ROOFTOP_TEST_BUILD_URL",
    "https://disk.yandex.ru/d/BqIWuMe6OHAnSg",
).strip()
BUILD_VERSION = "godot-rooftop-test-2026-07-22-v3"
BASE_DIR = Path(__file__).resolve().parent
TARGET_DIR = BASE_DIR / "games" / "rooftop-godot-test"
PERSIST_ROOT = (
    Path("/data") / "godot_rooftop_test_v155"
    if Path("/data").exists()
    else BASE_DIR / ".runtime" / "godot_rooftop_test_v155"
)
CACHE_DIR = PERSIST_ROOT / BUILD_VERSION
CACHE_BUILD_DIR = CACHE_DIR / "build"
MARKER_PATH = CACHE_DIR / "build.json"


TELEGRAM_AND_DIAGNOSTICS = r'''
<!-- main-hero-godot-test-v155 -->
<script>
(function () {
  const showFailure = function (message) {
    let box = document.getElementById("godot-test-error");
    if (!box) {
      box = document.createElement("pre");
      box.id = "godot-test-error";
      box.style.cssText = "position:fixed;z-index:999999;left:12px;right:12px;bottom:12px;max-height:45vh;overflow:auto;margin:0;padding:12px;border:1px solid #ff668e;border-radius:12px;background:#210914ee;color:#ffd9e4;font:12px/1.4 monospace;white-space:pre-wrap";
      document.documentElement.appendChild(box);
    }
    box.textContent = "Ошибка запуска Godot:\n" + String(message || "Неизвестная ошибка");
  };

  window.addEventListener("error", function (event) {
    showFailure(event.message || event.error || "JavaScript error");
  });
  window.addEventListener("unhandledrejection", function (event) {
    showFailure(event.reason || "Unhandled promise rejection");
  });

  window.addEventListener("load", function () {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (!tg) return;

    tg.expand();
    tg.disableVerticalSwipes?.();
    tg.setHeaderColor?.("#070511");
    tg.setBackgroundColor?.("#070511");
    tg.setBottomBarColor?.("#070511");

    if (tg.BackButton) {
      tg.BackButton.show();
      tg.BackButton.onClick(function () {
        window.location.href = "/games/";
      });
    }

    tg.ready();
  });
})();
</script>
'''.strip()


PLACEHOLDER_TEMPLATE = '''<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#070511">
  <title>Godot-тест загружается</title>
  <script src="https://telegram.org/js/telegram-web-app.js?63"></script>
  <style>
    html,body{{margin:0;min-height:100%;background:#070511;color:#fff;font-family:system-ui,sans-serif}}
    body{{display:grid;place-items:center;padding:24px;text-align:center}}
    .card{{max-width:420px;padding:26px;border:1px solid #6531a8;border-radius:22px;background:#160d29;box-shadow:0 0 40px #712de044}}
    .spinner{{width:44px;height:44px;margin:0 auto 18px;border:4px solid #ffffff22;border-top-color:#bd7cff;border-radius:50%;animation:spin 1s linear infinite}}
    h1{{font-size:21px;margin:0 0 10px}}p{{color:#c8b9dc;line-height:1.5;margin:0}}code{{display:block;margin-top:14px;color:#ffd365;white-space:pre-wrap}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
  </style>
</head>
<body>
  <main class="card">
    {spinner}
    <h1>{title}</h1>
    <p>{message}</p>
    {details}
  </main>
  <script>
    const tg = window.Telegram?.WebApp;
    tg?.expand(); tg?.ready(); tg?.disableVerticalSwipes?.();
    {reload_script}
  </script>
</body>
</html>
'''


def _write_placeholder(*, failed: bool = False, details: str = "") -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    if failed:
        title = "Не удалось подготовить Godot-тест"
        message = "Рабочая старая игра не затронута. Передай текст ошибки разработчику."
        spinner = ""
        detail_html = f"<code>{html.escape(details)}</code>" if details else ""
        reload_script = ""
    else:
        title = "Загружаем тестовую Godot-версию"
        message = "Сервер скачивает и распаковывает Web-сборку. Страница обновится автоматически."
        spinner = '<div class="spinner"></div>'
        detail_html = ""
        reload_script = "setTimeout(() => location.reload(), 5000);"

    (TARGET_DIR / "index.html").write_text(
        PLACEHOLDER_TEMPLATE.format(
            spinner=spinner,
            title=title,
            message=message,
            details=detail_html,
            reload_script=reload_script,
        ),
        encoding="utf-8",
    )


def _is_valid_build(directory: Path) -> bool:
    required = {
        "index.html": 500,
        "index.js": 10_000,
        "index.wasm": 5_000_000,
        "index.pck": 1_000_000,
    }
    return all(
        (directory / name).is_file()
        and (directory / name).stat().st_size >= minimum_size
        for name, minimum_size in required.items()
    )


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
        raise RuntimeError("Яндекс Диск не вернул ссылку скачивания.")
    return href


def _download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 MainHeroBot/1.0"},
    )
    with urllib.request.urlopen(request, timeout=360) as response:
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)


def _find_build_dir(extracted_dir: Path) -> Path:
    candidates = []
    for index_path in extracted_dir.rglob("index.html"):
        parent = index_path.parent
        if all((parent / name).is_file() for name in ("index.js", "index.wasm", "index.pck")):
            candidates.append(parent)
    if not candidates:
        raise RuntimeError("В ZIP не найдены index.html, index.js, index.wasm и index.pck в одной папке.")
    return min(candidates, key=lambda path: len(path.parts))


def _patch_index(index_path: Path) -> None:
    text = index_path.read_text(encoding="utf-8")
    text = text.replace('<html lang="en">', '<html lang="ru">', 1)
    text = text.replace(
        "<title>hero runner</title>",
        "<title>Главный герой — Godot-тест</title>",
        1,
    )
    if "telegram-web-app.js" not in text:
        text = text.replace(
            "</head>",
            '<script src="https://telegram.org/js/telegram-web-app.js?63"></script>\n</head>',
            1,
        )
    if "main-hero-godot-test-v155" not in text:
        text = text.replace("</head>", TELEGRAM_AND_DIAGNOSTICS + "\n</head>", 1)
    index_path.write_text(text, encoding="utf-8")


def _prepare_cache() -> None:
    if _is_valid_build(CACHE_BUILD_DIR):
        return
    if not PUBLIC_BUILD_URL:
        raise RuntimeError("GODOT_ROOFTOP_TEST_BUILD_URL не задан.")

    PERSIST_ROOT.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="godot-rooftop-test-", dir=PERSIST_ROOT))
    archive_path = work_dir / "build.zip"
    extracted_dir = work_dir / "extracted"
    prepared_dir = work_dir / "prepared"

    try:
        _download_file(_public_download_url(PUBLIC_BUILD_URL), archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extracted_dir)

        source_dir = _find_build_dir(extracted_dir)
        prepared_dir.mkdir(parents=True, exist_ok=True)
        for source_path in source_dir.iterdir():
            if source_path.is_file() and not source_path.name.endswith(".import"):
                shutil.copy2(source_path, prepared_dir / source_path.name)

        _patch_index(prepared_dir / "index.html")
        if not _is_valid_build(prepared_dir):
            raise RuntimeError("Скачанный ZIP не прошёл проверку Web-сборки Godot.")

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
    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = TARGET_DIR.with_name(f"{TARGET_DIR.name}.new")
    if staging_dir.exists() or staging_dir.is_symlink():
        if staging_dir.is_symlink():
            staging_dir.unlink(missing_ok=True)
        else:
            shutil.rmtree(staging_dir)
    shutil.copytree(CACHE_BUILD_DIR, staging_dir)
    if TARGET_DIR.exists() or TARGET_DIR.is_symlink():
        if TARGET_DIR.is_symlink():
            TARGET_DIR.unlink(missing_ok=True)
        else:
            shutil.rmtree(TARGET_DIR)
    staging_dir.replace(TARGET_DIR)


def _install_worker() -> None:
    try:
        _prepare_cache()
        _activate_build()
        LOGGER.info("Godot rooftop test activated at %s", TARGET_DIR)
    except Exception as exc:
        LOGGER.exception("Could not install Godot rooftop test build")
        _write_placeholder(failed=True, details=f"{type(exc).__name__}: {exc}")


def start_godot_rooftop_test_install() -> None:
    """Expose a placeholder immediately and install the test build in background."""
    if _is_valid_build(TARGET_DIR):
        return
    _write_placeholder()
    threading.Thread(
        target=_install_worker,
        name="godot-rooftop-test-installer",
        daemon=True,
    ).start()
