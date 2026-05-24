const state = {
  results: [],
  selected: null,
  lines: [],
  poster: null,
};

const $ = (selector) => document.querySelector(selector);

function setStatus(text) {
  $("#status").textContent = text;
}

function selectedRange() {
  const start = Number($("#lineStart").value || 1);
  const end = Number($("#lineEnd").value || 4);
  return { start, end };
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
  renderResults();
  renderLyrics();
  setStatus(state.results.length ? "Pick a track" : "No matches");
}

async function selectTrack(track) {
  state.selected = track;
  state.lines = [];
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
    setStatus("Lyrics failed");
    alert(payload.error || "Lyrics lookup failed.");
    return;
  }

  state.lines = payload.lines || [];
  if (state.lines.length >= 4) {
    $("#lineStart").value = 1;
    $("#lineEnd").value = 4;
  }
  renderLyrics();
  $("#generate").disabled = false;
  setStatus(state.lines.length ? "Ready" : "Add lyrics");
}

async function generatePoster() {
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
  const payload = await response.json();
  $("#generate").disabled = false;

  if (!response.ok || payload.error) {
    setStatus("Generate failed");
    alert(payload.error || "Poster generation failed.");
    return;
  }

  state.poster = payload.image;
  const poster = $("#poster");
  poster.src = `${payload.image}?t=${Date.now()}`;
  poster.hidden = false;
  $("#emptyState").hidden = true;
  $("#download").href = payload.image;
  $("#download").download = payload.filename;
  $("#download").classList.remove("disabled");
  setStatus("Poster ready");
}

$("#searchForm").addEventListener("submit", search);
$("#generate").addEventListener("click", generatePoster);
$("#lineStart").addEventListener("input", renderLyrics);
$("#lineEnd").addEventListener("input", renderLyrics);

renderResults();
