const statusEl   = document.getElementById('status');
const video      = document.getElementById('video');
const canvas     = document.getElementById('canvas');
const ctx        = canvas.getContext('2d');
const result     = document.getElementById('result');
const results    = document.getElementById('results');
const captureBtn = document.getElementById('capture');
const autoBtn    = document.getElementById('auto');
const stopBtn    = document.getElementById('stop');
const fileInput  = document.getElementById('fileInput');

let modelReady = false;
let autoInterval;

// Verificar modelo listo
fetch("/ready")
  .then(r => r.json())
  .then(data => {
    if (data.ready) {
      modelReady = true;
      statusEl.className = "alert alert-success";
      statusEl.textContent = "Listo";
      captureBtn.disabled = false;
      autoBtn.disabled = false;
      return navigator.mediaDevices.getUserMedia({video:true});
    } else {
      throw new Error(data.error || "Modelo no disponible");
    }
  })
  .then(stream => video.srcObject = stream)
  .catch(err => {
    statusEl.className = "alert alert-danger";
    statusEl.textContent = "Error: " + err.message;
  });

// Captura manual
captureBtn.addEventListener('click', () => {
  if (!modelReady) return alert("Modelo no listo");
  ctx.drawImage(video, 0, 0, 640, 480);
  detect();
});

// Auto cada 3 s
autoBtn.addEventListener('click', () => {
  if (!modelReady) return alert("Modelo no listo");
  autoInterval = setInterval(() => {
    ctx.drawImage(video, 0, 0, 640, 480);
    detect();
  }, 3000);
  autoBtn.style.display = 'none';
  stopBtn.style.display = 'inline-block';
});
stopBtn.addEventListener('click', () => {
  clearInterval(autoInterval);
  autoBtn.style.display = 'inline-block';
  stopBtn.style.display = 'none';
});

// Subir archivo
fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  fetch('/upload', {method:'POST', body:form})
    .then(r => r.json())
    .then(d => {
      const res = document.getElementById('uploadResult');
      if (d.error) res.innerHTML = `<div class="alert alert-danger">${d.error}</div>`;
      else res.innerHTML = `<div class="alert alert-success">${d.msg}</div>`;
    });
});

// Detectar
function detect() {
  fetch('/detect', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({image: canvas.toDataURL('image/jpeg')})
  })
  .then(r => r.json())
  .then(d => {
    if (d.error) { results.innerHTML = `<div class="alert alert-danger">${d.error}</div>`; return; }
    result.src = d.image; result.style.display='block';
    results.innerHTML = '<h5>Detecciones</h5><ul>' +
      d.detections.map(x => `<li>${x.class} → <strong>${x.ripeness}</strong> (${(x.confidence*100).toFixed(0)}%)</li>`).join('') +
      '</ul>';
    drawChart(d.detections);
  })
  .catch(err => {
    results.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
  });
}

// Gráfico
function drawChart(detections) {
  const stats = {RIPEN:0, UNRIPEN:0, OVERRIPE:0};
  detections.forEach(x => stats[x.ripeness]++);
  const labels = Object.keys(stats);
  const data   = Object.values(stats);
  const cfg = {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{ data: data, backgroundColor: ['#4CAF50','#F44336','#FFC107'] }]
    },
    options: { responsive: false, plugins: { legend: { position: 'bottom' } } }
  };
  if (window.statsChart) window.statsChart.destroy();
  window.statsChart = new Chart(document.getElementById('statsChart'), cfg);
}
