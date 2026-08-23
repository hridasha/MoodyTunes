(function () {
  var STORAGE_KEY = 'mt_player_state';
  var audio = null;
  var els = {};
  var state = { queue: [], index: -1, currentTime: 0, playing: false, volume: 1 };
  var seeking = false;

  function loadState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        if (parsed && Array.isArray(parsed.queue)) {
          state = parsed;
          if (typeof state.volume !== 'number') state.volume = 1;
        }
      }
    } catch (e) {
      // ignore corrupt/unavailable localStorage
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      // ignore quota/availability errors
    }
  }

  function currentSong() {
    return state.queue[state.index] || null;
  }

  var MOOD_VAR = {
    Happy: '--mood-happy',
    Sad: '--mood-sad',
    Angry: '--mood-angry',
    Fear: '--mood-fear',
    Neutral: '--mood-neutral',
  };

  function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) seconds = 0;
    var m = Math.floor(seconds / 60);
    var s = Math.floor(seconds % 60);
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  function updatePlayPauseIcon() {
    if (!els.playpauseIcon) return;
    els.playpauseIcon.className = state.playing ? 'fa fa-pause' : 'fa fa-play';
  }

  function updateNowPlayingUI() {
    var song = currentSong();
    if (!els.name) return;
    if (song) {
      els.name.textContent = song.name;
      els.artist.textContent = song.artist;
      els.image.src = song.image || '';
      els.bar.classList.add('mt-visible');
      var moodVar = MOOD_VAR[song.mood];
      var root = document.documentElement;
      root.style.setProperty(
        '--current-mood-color',
        moodVar ? 'var(' + moodVar + ')' : 'var(--brand)'
      );
    } else {
      els.bar.classList.remove('mt-visible');
    }
    updatePlayPauseIcon();
    if (els.next) {
      els.next.disabled = state.index + 1 >= state.queue.length;
    }
    if (els.prev) {
      els.prev.disabled = state.index <= 0;
    }
  }

  function loadCurrent(autoplay) {
    var song = currentSong();
    if (!song || !audio) return;
    audio.src = song.url;
    if (els.seek) els.seek.value = 0;
    if (els.timeCurrent) els.timeCurrent.textContent = '0:00';
    if (els.timeDuration) els.timeDuration.textContent = '0:00';
    updateNowPlayingUI();
    if (autoplay) {
      audio.play().catch(function () {
        // autoplay can be blocked by the browser without a user gesture
      });
    }
  }

  function playQueue(queue, startIndex) {
    if (!queue || !queue.length) return;
    state.queue = queue;
    state.index = startIndex || 0;
    state.currentTime = 0;
    state.playing = true;
    saveState();
    loadCurrent(true);
  }

  function shuffleQueue(queue) {
    var copy = queue.slice();
    for (var i = copy.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = copy[i];
      copy[i] = copy[j];
      copy[j] = tmp;
    }
    return copy;
  }

  function playSong(song) {
    playQueue([song], 0);
  }

  function next() {
    if (state.index + 1 < state.queue.length) {
      state.index += 1;
      state.currentTime = 0;
      saveState();
      loadCurrent(true);
    }
  }

  function prev() {
    if (state.index > 0) {
      state.index -= 1;
      state.currentTime = 0;
      saveState();
      loadCurrent(true);
    }
  }

  function togglePlayPause() {
    if (!audio || !currentSong()) return;
    if (audio.paused) {
      audio.play().catch(function () {});
    } else {
      audio.pause();
    }
  }

  function init() {
    audio = document.getElementById('mt-audio');
    if (!audio) return;
    els.bar = document.getElementById('mt-player-bar');
    els.name = document.getElementById('mt-player-song');
    els.artist = document.getElementById('mt-player-artist');
    els.image = document.getElementById('mt-player-image');
    els.playpause = document.getElementById('mt-playpause');
    els.playpauseIcon = document.getElementById('mt-playpause-icon');
    els.prev = document.getElementById('mt-prev');
    els.next = document.getElementById('mt-next');
    els.seek = document.getElementById('mt-seek');
    els.volume = document.getElementById('mt-volume');
    els.timeCurrent = document.getElementById('mt-time-current');
    els.timeDuration = document.getElementById('mt-time-duration');

    loadState();
    audio.volume = state.volume;
    if (els.volume) els.volume.value = state.volume;

    var song = currentSong();
    if (song) {
      audio.src = song.url;
      audio.currentTime = state.currentTime || 0;
      updateNowPlayingUI();
      if (state.playing) {
        audio.play().catch(function () {
          // autoplay can be blocked by the browser without a user gesture
        });
      }
    }

    audio.addEventListener('loadedmetadata', function () {
      if (els.timeDuration) els.timeDuration.textContent = formatTime(audio.duration);
    });
    audio.addEventListener('timeupdate', function () {
      state.currentTime = audio.currentTime;
      saveState();
      if (!seeking && els.seek && audio.duration) {
        els.seek.value = (audio.currentTime / audio.duration) * 100;
      }
      if (els.timeCurrent) els.timeCurrent.textContent = formatTime(audio.currentTime);
    });
    audio.addEventListener('play', function () {
      state.playing = true;
      saveState();
      updatePlayPauseIcon();
    });
    audio.addEventListener('pause', function () {
      state.playing = false;
      saveState();
      updatePlayPauseIcon();
    });
    audio.addEventListener('ended', next);

    if (els.playpause) {
      els.playpause.addEventListener('click', togglePlayPause);
    }
    if (els.prev) {
      els.prev.addEventListener('click', prev);
    }
    if (els.next) {
      els.next.addEventListener('click', next);
    }
    if (els.seek) {
      els.seek.addEventListener('input', function () {
        seeking = true;
        if (els.timeCurrent && audio.duration) {
          els.timeCurrent.textContent = formatTime((els.seek.value / 100) * audio.duration);
        }
      });
      els.seek.addEventListener('change', function () {
        if (audio.duration) {
          audio.currentTime = (els.seek.value / 100) * audio.duration;
        }
        seeking = false;
      });
    }
    if (els.volume) {
      els.volume.addEventListener('input', function () {
        audio.volume = parseFloat(els.volume.value);
        state.volume = audio.volume;
        saveState();
      });
    }
  }

  window.MTPlayer = {
    init: init,
    playQueue: playQueue,
    playSong: playSong,
    shuffleQueue: shuffleQueue,
    next: next,
    prev: prev,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
