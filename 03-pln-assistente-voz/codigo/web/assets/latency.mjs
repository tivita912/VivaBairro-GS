export function duration(start, end) {
  return Number.isFinite(start) && Number.isFinite(end) && end >= start ? (end - start) / 1000 : null;
}

export function turnMetrics(times, server, source) {
  const mic = source === 'microphone';
  const http = duration(times.sent, times.received);
  const download = duration(times.download, times.downloaded);
  return {
    input_source: source,
    question_started_at: mic && Number.isFinite(times.started)
      ? new Date(performance.timeOrigin + times.started).toISOString() : null,
    capture_seconds: mic ? duration(times.started, times.stopped) : null,
    capture_finalize_seconds: mic ? duration(times.stopped, times.selected) : null,
    before_send_seconds: duration(times.selected, times.sent),
    turn_http_seconds: http,
    server_turn_seconds: server.handler ?? null,
    request_body_receive_seconds: server.body ?? null,
    turn_http_overhead_seconds: http !== null && Number.isFinite(server.handler) ? Math.max(0, http - server.handler) : null,
    audio_download_seconds: download,
    server_audio_seconds: server.audio ?? null,
    audio_download_overhead_seconds: download !== null && Number.isFinite(server.audio) ? Math.max(0, download - server.audio) : null,
    player_prepare_seconds: duration(times.attached, times.ready),
    ready_to_play_request_seconds: duration(times.ready, times.play),
    play_request_to_playing_seconds: duration(times.play, times.playing),
    send_to_playing_seconds: duration(times.sent, times.playing),
    question_end_to_playing_seconds: mic ? duration(times.stopped, times.playing) : null,
    playback_start_seconds: duration(mic ? times.started : times.selected, times.playing),
    playback_boundary: mic ? 'capture_start_to_playing' : 'file_selected_to_playing',
    playback_measurement: Number.isFinite(times.playing) ? 'player_event_proxy' : 'pending_player_event',
  };
}

export function readServerTiming(value) {
  const result = {};
  for (const entry of (value || '').split(',')) {
    const match = /^\s*(handler|body|audio);dur=(\d+(?:\.\d+)?)\s*$/.exec(entry);
    if (match && Number.isFinite(Number(match[2]))) result[match[1]] = Number(match[2]) / 1000;
  }
  return result;
}
