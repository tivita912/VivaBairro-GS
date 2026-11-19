import { readServerTiming, turnMetrics } from "./latency.mjs";

const byId = (id) => document.getElementById(id);
const steps = [...document.querySelectorAll(".steps li")];
const consent = byId("consent-form");
const upload = byId("upload");
const record = byId("record");
const preview = byId("preview");
const player = byId("answer-audio");
const formats = new Set(["wav", "mp3", "m4a", "mp4", "webm", "ogg", "flac"]);
const canRecord = Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);

let info;
let session = "";
let authorized = false;
let busy = false;
let startingMic = false;
let recording = null;
let selected = null;
let previewUrl = "";
let playbackUrl = "";
let playbackMeasurement = null;
let expiryTimer;

function status(message = "") {
  byId("status").textContent = message;
}

function error(message = "") {
  byId("error").textContent = message;
}

function step(index) {
  steps.forEach((item, i) => {
    item.toggleAttribute("data-complete", i < index);
    if (i === index) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
}

function controls() {
  byId("consent-fields").disabled = !info?.available || busy;
  byId("consent-confirmed").hidden = !authorized;
  consent.hidden = authorized;
  byId("capture-locked").hidden = authorized;
  byId("capture-controls").hidden = !authorized;
  byId("clear").disabled = !authorized || busy;
  byId("retry").disabled = busy || Boolean(recording);
  record.disabled = !canRecord || busy || startingMic;
  upload.disabled = busy || startingMic || Boolean(recording);
  byId("send").disabled = busy || startingMic || Boolean(recording) || !selected;
  byId("capture-controls").setAttribute("aria-busy", String(busy));
}

async function request(url, options = {}, timing) {
  const headers = new Headers(options.headers);
  if (session) headers.set("X-VivaBairro-Session", session);
  const response = await fetch(url, { ...options, headers, cache: "no-store" });
  if (timing) Object.assign(timing, readServerTiming(response.headers.get("Server-Timing")));
  if (response.ok && url.startsWith("/api/audio/")) return response.blob();
  const data = await response.json();
  if (response.ok) return data;
  const failure = new Error(data.detail || "Não foi possível concluir a solicitação.");
  failure.status = response.status;
  failure.data = data;
  throw failure;
}

function clearMedia(element, url) {
  element.pause();
  element.removeAttribute("src");
  element.load();
  if (url) URL.revokeObjectURL(url);
}

function resetSelection() {
  selected = null;
  if (previewUrl) clearMedia(preview, previewUrl);
  previewUrl = "";
  upload.value = "";
  byId("selection").hidden = true;
}

function stopRecording(discard = false) {
  if (!recording) return;
  recording.discard ||= discard;
  if (recording.recorder.state !== "inactive") {
    recording.stopped = performance.now();
    recording.recorder.stop();
  }
  recording.stream.getTracks().forEach((track) => track.stop());
}

function resetLocal() {
  authorized = false;
  stopRecording(true);
  clearTimeout(expiryTimer);
  consent.reset();
  resetSelection();
  showResult({});
  showHistory([]);
  showMetrics({});
  byId("retry").hidden = true;
  step(0);
  controls();
}

function scheduleExpiry() {
  clearTimeout(expiryTimer);
  expiryTimer = setTimeout(() => {
    resetLocal();
    status("A sessão expirou. Confirme novamente o consentimento para continuar.");
  }, info.retention_seconds * 1000);
}

function handleFailure(failure) {
  if (failure.status === 410) {
    resetLocal();
    session = "";
  }
  status();
  error(failure.status ? failure.message : "Confira a conexão com o aplicativo e tente novamente.");
}

function selectAudio(file, format, source, capture = {}) {
  if (!formats.has(format)) {
    resetSelection();
    error("Escolha um arquivo WAV, MP3, M4A, MP4, WebM, OGG ou FLAC.");
  } else if (!file.size || file.size > info.max_audio_mb * 1024 * 1024) {
    resetSelection();
    error("O áudio está vazio ou ultrapassa o limite de tamanho.");
  } else {
    if (previewUrl) clearMedia(preview, previewUrl);
    selected = { file, format, source, capture: { ...capture, selected: performance.now() } };
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    byId("selection-name").textContent = source === "microphone" ? "Gravação pronta para enviar" : file.name;
    byId("selection").hidden = false;
    error();
    status("Áudio pronto. Você pode ouvir a prévia ou enviar para transcrição.");
  }
  controls();
}

function showResult(data) {
  playbackMeasurement = null;
  if (playbackUrl) clearMedia(player, playbackUrl);
  playbackUrl = "";
  byId("playback").hidden = true;
  byId("transcription").textContent = data.transcription || "";
  byId("answer").textContent = data.response || "";
  byId("transcription-block").hidden = !data.transcription;
  byId("response-block").hidden = !data.response;
  byId("result-empty").hidden = Boolean(data.transcription || data.response);
}

function showHistory(history) {
  const list = byId("history");
  byId("history-empty").hidden = history.length > 0;
  list.replaceChildren();
  for (const message of history) {
    const entry = document.createElement("li");
    const label = document.createElement("strong");
    label.textContent = message.role === "user" ? "Você" : "Orientação";
    entry.append(label, document.createTextNode(message.content));
    list.append(entry);
  }
}

function showMetrics(metrics) {
  const names = {
    input: "Preparação do áudio", stt: "Transcrição", context: "Preparação do contexto",
    llm: "Geração da resposta", speech_text: "Texto para fala", tts: "Síntese de voz",
    processing_total: "Processamento total", elapsed_to_failure: "Tempo até a interrupção",
    capture: "Duração da captura", capture_finalize: "Finalização da captura",
    before_send: "Seleção até envio", request_body_receive: "Recebimento do áudio pelo servidor",
    server_turn: "Rota do turno no servidor", turn_http: "Requisição completa do turno",
    audio_download: "Requisição do áudio da resposta", player_prepare: "Preparação no navegador",
    playback_start: metrics.input_source === "upload" ? "Seleção do arquivo até reprodução" : "Início da captura até reprodução",
    question_end_to_playing: "Fim da captura até reprodução", send_to_playing: "Envio até reprodução",
  };
  const list = byId("metrics");
  list.replaceChildren();
  for (const [key, name] of Object.entries(names)) {
    const value = metrics.stage_seconds?.[key] ?? metrics[key + "_seconds"];
    if (typeof value !== "number") continue;
    const row = document.createElement("div");
    const title = document.createElement("dt");
    const time = document.createElement("dd");
    title.textContent = name;
    time.textContent = value.toLocaleString("pt-BR", { maximumFractionDigits: 2 }) + " s";
    row.append(title, time);
    list.append(row);
  }
  const hasMetrics = Object.keys(metrics).length > 0;
  byId("metrics-empty").hidden = hasMetrics;
  byId("metrics-more").hidden = !hasMetrics;
  byId("metrics-json").textContent = hasMetrics ? JSON.stringify(metrics, null, 2) : "";
}

function updateTurnMetrics(measurement) {
  showMetrics({ ...measurement.base, ...turnMetrics(measurement.times, measurement.server, measurement.source) });
}

for (const [event, key] of [["loadeddata", "ready"], ["play", "play"], ["playing", "playing"]]) {
  player.addEventListener(event, () => {
    const measurement = playbackMeasurement;
    if (!measurement || player.currentSrc !== measurement.url || key in measurement.times) return;
    measurement.times[key] = performance.now();
    updateTurnMetrics(measurement);
  });
}

consent.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  busy = true;
  controls();
  error();
  try {
    // Ler os valores explicitamente, inclusive enquanto o fieldset está desabilitado.
    const data = await request("/api/consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        accepted: consent.elements.accepted.checked,
        external_audio: consent.elements.external_audio.checked,
        external_text: consent.elements.external_text.checked,
        notice_version: info.notice_version,
      }),
    });
    session = data.session;
    authorized = true;
    scheduleExpiry();
    step(1);
    status("Consentimento confirmado. Você já pode gravar ou escolher um arquivo.");
  } catch (failure) {
    handleFailure(failure);
  } finally {
    busy = false;
    controls();
    if (authorized) byId("capture-title").focus();
  }
});

upload.addEventListener("change", () => {
  const file = upload.files[0];
  if (authorized && file) selectAudio(file, file.name.split(".").pop().toLowerCase(), "upload");
  else if (!file) resetSelection();
  controls();
});

record.addEventListener("click", async () => {
  if (recording) {
    stopRecording();
    return;
  }
  if (!authorized || busy || startingMic) return;
  startingMic = true;
  controls();
  error();
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (!authorized) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    const mimeType = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"]
      .find((candidate) => MediaRecorder.isTypeSupported(candidate));
    if (!mimeType) throw new Error("unsupported");
    const recorder = new MediaRecorder(stream, { mimeType });
    const chunks = [];
    const current = { recorder, stream, discard: false };
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    recorder.onerror = () => {
      stopRecording(true);
      status();
      error("A gravação foi interrompida. Tente novamente ou envie um arquivo.");
    };
    recorder.onstop = () => {
      clearTimeout(current.timer);
      stream.getTracks().forEach((track) => track.stop());
      recording = null;
      byId("record-label").textContent = "Gravar pelo microfone";
      if (authorized && !current.discard) {
        const format = mimeType.split("/")[1].split(";")[0];
        selectAudio(new Blob(chunks, { type: mimeType }), format, "microphone", {
          started: current.started, stopped: current.stopped ?? performance.now(),
        });
      }
      controls();
    };
    resetSelection();
    current.started = performance.now();
    recorder.start();
    recording = current;
    current.timer = setTimeout(() => stopRecording(), info.max_audio_seconds * 1000);
    byId("record-label").textContent = "Parar gravação";
    status("Gravando. Use Parar gravação quando terminar de falar.");
  } catch (failure) {
    stream?.getTracks().forEach((track) => track.stop());
    status();
    error("Não foi possível usar o microfone. Confira a permissão do navegador ou escolha um arquivo.");
  } finally {
    startingMic = false;
    controls();
  }
});

byId("send").addEventListener("click", async () => {
  if (!authorized || !selected || busy || recording || startingMic) return;
  const { file, format, source, capture } = selected;
  const measurement = { times: { ...capture }, source, server: {}, base: {} };
  busy = true;
  clearTimeout(expiryTimer);
  controls();
  step(2);
  error();
  status("Processando seu áudio. Aguarde a transcrição e a orientação.");
  showResult({});
  showMetrics({});
  try {
    measurement.times.sent = performance.now();
    const data = await request("/api/turn?" + new URLSearchParams({ format, source }), {
      method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file,
    }, measurement.server);
    measurement.times.received = performance.now();
    showResult(data);
    showHistory(data.history);
    measurement.base = data.metrics;
    updateTurnMetrics(measurement);
    resetSelection();
    step(3);
    status("Resposta pronta. Confira a transcrição antes de usar a orientação.");
    try {
      measurement.times.download = performance.now();
      const audio = await request(data.audio_url, {}, measurement.server);
      measurement.times.downloaded = performance.now();
      playbackUrl = URL.createObjectURL(audio);
      measurement.url = playbackUrl;
      measurement.times.attached = performance.now();
      playbackMeasurement = measurement;
      player.src = playbackUrl;
      byId("playback").hidden = false;
      updateTurnMetrics(measurement);
    } catch {
      error("A resposta em texto está disponível. O áudio não pôde ser carregado.");
    }
    byId("result-title").focus();
  } catch (failure) {
    handleFailure(failure);
    if (authorized) {
      const data = failure.data || {};
      showResult(data);
      measurement.base = { ...data.metrics, failed: true };
      measurement.times.received = performance.now();
      updateTurnMetrics(measurement);
      if (data.history) showHistory(data.history);
      step(data.transcription ? 2 : 1);
      // Em falha transitória do provedor, preserve o áudio local.
      // Uma segunda tentativa só acontece se o usuário clicar em Enviar áudio.
      const retryable = ["network", "timeout", "unavailable"].includes(data.error_code);
      if (failure.status === 502 && retryable && !data.transcription && selected) {
        status("Seu áudio continua selecionado. Você pode reenviar ou gravar outro. Reenviar poderá consumir uma nova chamada à API.");
      } else {
        resetSelection();
      }
    }
  } finally {
    busy = false;
    byId("retry").hidden = !authorized;
    if (authorized) scheduleExpiry();
    controls();
  }
});

byId("retry").addEventListener("click", () => {
  error();
  status("Grave ou escolha outro áudio para continuar a conversa.");
  step(1);
  byId("capture-title").focus();
});

byId("clear").addEventListener("click", async () => {
  if (busy || !authorized) return;
  stopRecording(true);
  busy = true;
  controls();
  error();
  try {
    await request("/api/clear", { method: "POST" });
    resetLocal();
    status("Conversa limpa. Confirme novamente o consentimento para continuar.");
    byId("consent-title").focus();
  } catch (failure) {
    handleFailure(failure);
  } finally {
    busy = false;
    controls();
  }
});

byId("privacy-link").addEventListener("click", () => { byId("privacy-details").open = true; });
window.addEventListener("pagehide", () => {
  stopRecording(true);
  if (authorized) {
    fetch("/api/clear", { method: "POST", headers: { "X-VivaBairro-Session": session }, keepalive: true }).catch(() => {});
    resetLocal();
  }
});

async function initialize() {
  try {
    info = await request("/api/info");
    byId("privacy-notice").textContent = info.notice;
    byId("retention").textContent = "A sessão expira após " + info.retention_seconds + " segundos de inatividade.";
    byId("audio-limits").textContent = "Até " + info.max_audio_seconds + " segundos e " + info.max_audio_mb
      + " MiB por áudio." + (canRecord ? "" : " O microfone não está disponível neste navegador. Use o envio de arquivo.");
    for (const detail of document.querySelectorAll("[data-topic]")) {
      const topic = info.topics[detail.dataset.topic];
      if (!topic) continue;
      detail.querySelector("p").textContent = topic.text;
      const link = detail.querySelector("a");
      link.href = topic.source_url;
      link.textContent = "Fonte: " + topic.source_title;
      link.hidden = false;
    }
    if (!info.available) error(info.configuration_message || "O atendimento está indisponível.");
  } catch (failure) {
    handleFailure(failure);
  } finally {
    controls();
  }
}
initialize();
