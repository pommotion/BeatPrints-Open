const state = {
  mode: "search",
  results: [],
  selected: null,
  lines: [],
  lyricsSource: "",
  poster: null,
};

const $ = (selector) => document.querySelector(selector);

function setStatus(text) {
  $("#status").textContent = text;
}

function fieldValue(selector, fallback = "") {
  return $(selector).value.trim() || fallback;
}

function selectedRange() {
  const start = Number($("#lineStart").value || 1);
  const end = Number($("#lineEnd").value || 4);
  return { start, end };
}

function setMode(mode) {
  state.mode = mode;
  $("#searchTab").classList.toggle("active", mode === "search");
  $("#manualTab").classList.toggle("active", mode === "manual");
  $("#searchForm").hidden = mode !== "search";
  $("#manualPanel").hidden = mode !== "manual";
  $("#resultsBlock").hidden = mode !== "search";
  setStatus(mode === "search" ? "Ready" : "Manual entry");
}

function manualTrack() {
  const name = fieldValue("#manualName");
  const artist = fieldValue("#manualArtist");

  if (!name || !artist) {
    alert("Track name and artist are required.");
    return null;
  }

  return {
    name,
    artist,
    album: fieldValue("#manualAlbum", "Single"),
    released: fieldValue("#manualReleased", "Unreleased"),
    duration: fieldValue("#manualDuration", "00:00"),
    image: fieldValue("#manualImage"),
    label: fieldValue("#manualLabel", "Independent"),
    id: fieldValue("#manualLink"),
  };
}

function applyManualTrack() {
  const track = manualTrack();
  if (!track) return;

  state.selected = track;
  state.lines = [];
  state.lyricsSource = "Manual";
  renderLyrics();
  $("#previewTitle").textContent = `${track.name} · ${track.artist}`;
  $("#previewMeta").textContent = `${track.album} · ${track.released}`;
  $("#lyricsNotice").textContent = "Manual metadata is active. Paste lyrics below or leave them blank.";
  $("#generate").disabled = false;
  setStatus("Manual ready");
}

function filenameFromDisposition(header) {
  if (!header) return "beatprints-poster.png";

  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    return decodeURIComponent(utf8Match[1]);
  }

  const asciiMatch = header.match(/filename="?([^"]+)"?/i);
  return asciiMatch ? asciiMatch[1] : "beatprints-poster.png";
}

function renderResults() {
  const container = $("#results");
  container.innerHTML = "";
  $("#resultCount").textContent = String(state.results.length);

  if (!state.results.length) {
    container.innerHTML = '<p class="muted">No results yet.</p>';
    return;
  }

  state.results.forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `result ${state.selected === item ? "active" : ""}`;
    button.innerHTML = `
      <span>${index + 1}</span>
      <strong>${item.name}</strong>
      <span>${item.artist} · ${item.album}</span>
    `;
    button.addEventListener("click", () => selectTrack(item));
    container.appendChild(button);
  });
}

function renderLyrics() {
  const list = $("#lyrics");
  list.innerHTML = "";
  $("#lyricsCount").textContent = `${state.lines.length} lines`;
  $("#lyricsEmpty").hidden = state.lines.length > 0;
  const { start, end } = selectedRange();

  state.lines.forEach((line, index) => {
    const li = document.createElement("li");
    li.textContent = line;
    const lineNo = index + 1;
    if (lineNo >= start && lineNo <= end) {
      li.className = "selected";
    }
    list.appendChild(li);
  });
}

async function search(event) {
  event.preventDefault();
  const query = $("#query").value.trim();
  if (!query) return;

  setStatus("Searching");
  $("#generate").disabled = true;
  const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=6`);
  const payload = await response.json();

  if (!response.ok || payload.error) {
    setStatus("Search failed");
    alert(payload.error || "Search failed.");
    return;
  }

  state.results = payload.results || [];
  state.selected = null;
  state.lines = [];
  state.lyricsSource = "";
  $("#lyricsNotice").textContent = "Search mode tries LRCLIB, then lyrics.ovh. Manual mode uses this text directly.";
  $("#customLyrics").value = "";
  renderResults();
  renderLyrics();
  setStatus(state.results.length ? "Pick a track" : "No matches");
}

async function selectTrack(track) {
  state.selected = track;
  state.lines = [];
  state.lyricsSource = "";
  $("#customLyrics").value = "";
  $("#lyricsNotice").textContent = "Trying LRCLIB, then lyrics.ovh.";
  renderResults();
  $("#previewTitle").textContent = `${track.name} · ${track.artist}`;
  $("#previewMeta").textContent = `${track.album} · ${track.released}`;
  setStatus("Fetching lyrics");

  const response = await fetch("/api/lyrics", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ track }),
  });
  const payload = await response.json();

  if (!response.ok || payload.error) {
    state.lines = [];
    renderLyrics();
    $("#generate").disabled = false;
    $("#lyricsNotice").textContent = "Lyrics lookup failed. You can still paste lyrics manually.";
    setStatus("Add lyrics");
    return;
  }

  state.lines = payload.lines || [];
  state.lyricsSource = payload.source || "";
  if (state.lines.length >= 4) {
    $("#lineStart").value = 1;
    $("#lineEnd").value = 4;
  }
  renderLyrics();
  $("#generate").disabled = false;
  if (state.lines.length) {
    $("#lyricsNotice").textContent = `Lyrics loaded from ${state.lyricsSource}. Edit manual lyrics only if you want to override.`;
    setStatus("Ready");
  } else {
    $("#lyricsNotice").textContent =
      payload.warning || "No lyrics found in available libraries. Paste lyrics manually to generate.";
    setStatus("Add lyrics");
  }
}

async function generatePoster() {
  if (state.mode === "manual") {
    const track = manualTrack();
    if (!track) return;
    state.selected = track;
  }

  if (!state.selected) return;

  setStatus("Generating");
  $("#generate").disabled = true;
  const { start, end } = selectedRange();
  const response = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      track: state.selected,
      lines: state.lines,
      start,
      end,
      customLyrics: $("#customLyrics").value,
      theme: $("#theme").value,
      accent: $("#accent").checked,
    }),
  });
  $("#generate").disabled = false;

  if (!response.ok) {
    const payload = response.headers.get("Content-Type")?.includes("application/json")
      ? await response.json()
      : { error: await response.text() };
    setStatus("Generate failed");
    alert(payload.error || "Poster generation failed.");
    return;
  }

  if (state.poster) {
    URL.revokeObjectURL(state.poster);
  }

  const blob = await response.blob();
  const imageUrl = URL.createObjectURL(blob);
  const filename = filenameFromDisposition(response.headers.get("Content-Disposition"));

  state.poster = imageUrl;
  const poster = $("#poster");
  poster.src = imageUrl;
  poster.hidden = false;
  $("#emptyState").hidden = true;
  $("#download").href = imageUrl;
  $("#download").download = filename;
  $("#download").classList.remove("disabled");
  setStatus("Poster ready");
}

$("#searchForm").addEventListener("submit", search);
$("#generate").addEventListener("click", generatePoster);
$("#searchTab").addEventListener("click", () => setMode("search"));
$("#manualTab").addEventListener("click", () => setMode("manual"));
$("#applyManual").addEventListener("click", applyManualTrack);
$("#lineStart").addEventListener("input", renderLyrics);
$("#lineEnd").addEventListener("input", renderLyrics);

renderResults();
setMode("search");
