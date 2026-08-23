(function () {
  var player = null;
  var deviceId = null;
  var els = {};
  var retriedAuth = false;

  function getCookie(name) {
    var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? match.pop() : '';
  }

  function fetchToken() {
    return fetch('/spotify/token/').then(function (resp) {
      if (!resp.ok) throw new Error('no token');
      return resp.json();
    }).then(function (data) {
      return data.access_token;
    });
  }

  function showStatus(message) {
    if (els.status) els.status.textContent = message;
  }

  function playTrack(uri) {
    if (!deviceId) {
      showStatus('Spotify player is not ready yet — wait a moment and try again.');
      return;
    }
    fetchToken().then(function (token) {
      return fetch('https://api.spotify.com/v1/me/player/play?device_id=' + deviceId, {
        method: 'PUT',
        headers: {
          'Authorization': 'Bearer ' + token,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ uris: [uri] }),
      });
    }).then(function (resp) {
      if (resp.status === 403 || resp.status === 404) {
        showStatus('Playback failed — this Spotify account may not have Premium, which the Web Playback SDK requires.');
      }
    }).catch(function () {
      showStatus('Could not start playback.');
    });
  }

  function initPlayer() {
    window.onSpotifyWebPlaybackSDKReady = function () {
      player = new Spotify.Player({
        name: 'MoodyTunes',
        getOAuthToken: function (cb) {
          fetchToken().then(cb).catch(function () {
            showStatus('Could not get a Spotify token. Try reconnecting your account.');
          });
        },
        volume: 0.8,
      });

      player.addListener('ready', function (event) {
        deviceId = event.device_id;
        showStatus('Ready to play.');
      });
      player.addListener('not_ready', function () {
        deviceId = null;
        showStatus('Spotify player disconnected.');
      });
      player.addListener('initialization_error', function (e) {
        showStatus('Could not initialize the Spotify player: ' + e.message);
      });
      player.addListener('authentication_error', function (e) {
        if (!retriedAuth) {
          retriedAuth = true;
          showStatus('Refreshing Spotify session…');
        } else {
          showStatus('Spotify session expired. Try reconnecting your account.');
        }
      });
      player.addListener('account_error', function () {
        showStatus('This Spotify account does not have Premium, which the Web Playback SDK requires for in-app playback.');
      });
      player.addListener('player_state_changed', function (state) {
        if (!state || !els.nowPlaying) return;
        var track = state.track_window.current_track;
        els.nowPlaying.textContent = track ? (track.name + ' — ' + track.artists.map(function (a) { return a.name; }).join(', ')) : '';
      });

      player.connect();
    };

    var script = document.createElement('script');
    script.src = 'https://sdk.scdn.co/spotify-player.js';
    document.head.appendChild(script);
  }

  window.MTSpotify = {
    init: function (elements) {
      els = elements || {};
      initPlayer();
    },
    playTrack: playTrack,
  };
})();
