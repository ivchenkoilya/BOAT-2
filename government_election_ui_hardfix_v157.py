from __future__ import annotations

from typing import Any, Callable

import government_mandate_luxury_v147 as luxury


VERSION = "Reality 157 · Подкуп голосов без старого кэша"


def _inject_clean_ui(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)

    # Старые поверхностные скрипты больше не нужны: вся логика встроена
    # непосредственно в election-shadow-v153.js. Удаляем их, чтобы они не
    # перерисовывали окно и не создавали второй обработчик отправки формы.
    obsolete_scripts = (
        '  <script src="/government-v154/election-offer-duration-v154.js?v=154"></script>\n',
        '  <script src="/government-v155/election-bribe-label-v155.js?v=155"></script>\n',
        '  <script src="/government-v156/election-message-v156.js?v=156"></script>\n',
    )
    for script in obsolete_scripts:
        source = source.replace(script, "")

    # Новый query string заставляет Telegram WebView запросить свежий основной
    # файл, а не использовать сохранённую копию с надписью «Купить голос».
    source = source.replace(
        "/government-v153/election-shadow-v153.js?v=153",
        "/government-v153/election-shadow-v153.js?v=157",
    )
    return source


def install_government_election_ui_hardfix_v157(core: Any) -> None:
    if getattr(core, "_government_election_ui_hardfix_v157_installed", False):
        return
    core._government_election_ui_hardfix_v157_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_inject = luxury._inject_assets

    def inject_without_obsolete_layers(source: str) -> str:
        return _inject_clean_ui(previous_inject, source)

    luxury._inject_assets = inject_without_obsolete_layers
