import assert from "node:assert/strict";
import test from "node:test";
import { readServerTiming, turnMetrics } from "../web/assets/latency.mjs";

const server = readServerTiming("handler;dur=2000.0, body;dur=35.0, audio;dur=10.0, unknown;dur=3");
const events = {
  started: 100, stopped: 1100, selected: 1200, sent: 1500, received: 3800,
  download: 3805, downloaded: 3965, attached: 3970, ready: 4000, play: 4300, playing: 4420,
};

test("mede captura, servidor, arquivo e reprodução com origens explícitas", () => {
  const data = turnMetrics(events, server, "microphone");
  assert.equal(data.capture_seconds, 1);
  assert.equal(data.capture_finalize_seconds, .1);
  assert.equal(data.request_body_receive_seconds, .035);
  assert.equal(data.audio_download_seconds, .16);
  assert.equal(data.player_prepare_seconds, .03);
  assert.equal(data.playback_start_seconds, 4.32);
  assert.equal(data.question_end_to_playing_seconds, 3.32);
  assert.equal(data.playback_boundary, "capture_start_to_playing");
  assert.equal(data.playback_measurement, "player_event_proxy");
});

test("upload usa seleção como origem e não inventa captação", () => {
  const data = turnMetrics(events, server, "upload");
  assert.equal(data.playback_start_seconds, 3.22);
  assert.equal(data.capture_seconds, null);
  assert.equal(data.question_end_to_playing_seconds, null);
  assert.equal(data.playback_boundary, "file_selected_to_playing");
});

test("áudio recebido sem playing deixa o início pendente", () => {
  const { playing, ...pending } = events;
  const data = turnMetrics(pending, {}, "microphone");
  assert.equal(data.playback_start_seconds, null);
  assert.equal(data.ready_to_play_request_seconds, .3);
  assert.equal(data.turn_http_overhead_seconds, null);
  assert.equal(data.playback_measurement, "pending_player_event");
});

test("cabeçalho ruim e evento fora de ordem não criam tempos", () => {
  assert.deepEqual(readServerTiming("handler;dur=NaN, body;dur=-5"), {});
  assert.equal(turnMetrics({ selected: 200, playing: 190 }, {}, "upload").playback_start_seconds, null);
});
