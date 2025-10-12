const statusEl   = document.getElementById('status');
const video      = document.getElementById('video');
const canvas     = document.getElementById('canvas');
const ctx        = canvas.getContext('2d');
const result     = document.getElementById('result');
const results    = document.getElementById('results');
const captureBtn = document.getElementById('capture');
const autoBtn    = document.getElementById('auto');
const stopBtn    = document.getElementById('stop');
const toggleBtn  = document.getElementById('toggleCam');
const fileInput  = document.getElementById('fileInput');

let modelReady = false;
let autoInterval = null;
let stream = null;

// Verificar modelo
fetch("/ready")
  .then(r => r.json())
  .then(data => {
    if (data.ready) {
      modelReady = true;
      statusEl.className = "alert alert-success";
      statusEl.textContent = "Listo - Presiona Encender Cámara";
      captureBtn.disabled = false;
      autoBtn.disabled = false;
    } else {
      throw new Error(data.error || "Modelo no disponible");
    }
  })
  .catch(err => {
    statusEl.className = "alert alert-danger";
    statusEl.textContent = "Error: " + err.message;
  });

// Encender/apagar cámara
toggleBtn.addEventListener('click', async () => {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
    video.srcObject = null;
    toggleBtn.textContent = "🟢 Encender Cámara";
    statusEl.textContent = "Cámara apagada";
    autoBtn.disabled = true;
    captureBtn.disabled = true;
  } else {
    try {
      stream = await navigator.mediaDevices.getUserMedia({video:true});
      video.srcObject = stream;
      toggleBtn.textContent = "🔴 Apagar Cámara";
      statusEl.textContent = "Cámara encendida";
      autoBtn.disabled = false;
      captureBtn.disabled = false;
    } catch (e) {
      statusEl.textContent = "Error de cámara: " + e.message;
    }
  }
});

// Captura manual
captureBtn.addEventListener('click', () => {
  if (!modelReady || !stream) return alert("Modelo o cámara no listos");
  ctx.drawImage(video, 0, 0, 640, 480);
  detect();
});

// Auto cada 3 s
autoBtn.addEventListener('click', () => {
  if (!modelReady || !stream) return alert("Modelo o cámara no listos");
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
    results.innerHTML = '<h5>Resultados</h5><ul>' +
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
  const stats = {RIPEN:0, UNRIPEN:0, OVERRIPE:0, "NO-FRUIT":0};
  detections.forEach(x => stats[x.ripeness]++);
  const labels = Object.keys(stats);
  const data   = Object.values(stats);
  const cfg = {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{ data: data, backgroundColor: ['#4CAF50','#F44336','#FFC107','#808080'] }]
    },
    options: { responsive: false, plugins: { legend: { position: 'bottom' } } }
  };
  if (window.statsChart) window.statsChart.destroy();
  window.statsChart = new Chart(document.getElementById('statsChart'), cfg);
}
