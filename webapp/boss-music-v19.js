(() => {
  'use strict';

  const NativeAudio = window.Audio;
  const MUSIC_SRC = '/boss-app/assets/boss_music.mp3';
  const bossMusic = new NativeAudio(MUSIC_SRC);

  bossMusic.loop = true;
  bossMusic.volume = 0.35;
  bossMusic.preload = 'auto';
  bossMusic.setAttribute('playsinline', '');

  let hasStarted = false;

  function removeStartListeners() {
    document.removeEventListener('pointerup', tryStartMusic, true);
    document.removeEventListener('touchend', tryStartMusic, true);
    document.removeEventListener('click', tryStartMusic, true);
  }

  async function tryStartMusic() {
    if (!bossMusic.paused) {
      hasStarted = true;
      removeStartListeners();
      return;
    }

    try {
      await bossMusic.play();
      hasStarted = true;
      removeStartListeners();
    } catch (error) {
      console.warn('Не удалось запустить музыку босса, повторим после следующего нажатия.', error);
    }
  }

  // Telegram WebView может отклонить первое событие. Поэтому пробуем снова
  // после каждого типа пользовательского нажатия, пока воспроизведение не начнётся.
  document.addEventListener('pointerup', tryStartMusic, true);
  document.addEventListener('touchend', tryStartMusic, true);
  document.addEventListener('click', tryStartMusic, true);

  // Возвращаем музыку после сворачивания и повторного открытия Mini App.
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && hasStarted && bossMusic.paused) {
      tryStartMusic();
    }
  });

  // app.js уже создаёт Audio с этим же адресом. Возвращаем ему тот же объект,
  // чтобы не запустились две одинаковые композиции одновременно.
  function AudioProxy(src) {
    if (typeof src === 'string' && (src === MUSIC_SRC || src.endsWith('/boss_music.mp3'))) {
      return bossMusic;
    }
    return new NativeAudio(src);
  }

  AudioProxy.prototype = NativeAudio.prototype;
  Object.setPrototypeOf(AudioProxy, NativeAudio);
  window.Audio = AudioProxy;
  window.__bossMusic = bossMusic;
})();
