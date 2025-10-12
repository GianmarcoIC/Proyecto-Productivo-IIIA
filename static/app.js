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

let modelLoaded = false;
let autoInterval;

// Verificar disponibilidad de cámara
navigator.mediaDevices.getUserMedia({video:true})
  .then(s => {
    video.srcObject = s;
    statusEl.textContent = "Modelo cargando...";
    return fetch('/detect', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({image: canvas.toDataURL('image/jpeg')})});
  })
  .then(r => r.json())
  .then(() => { modelLoaded = true; statusEl.className="alert alert-success"; statusEl.textContent="Listo"; captureBtn.disabled=false; autoBtn.disabled=false; })
  .catch(e => { statusEl.className="alert alert-danger"; statusEl.textContent="Error: "+e; });

captureBtn.addEventListener('click', () => {
  if (!modelLoaded) return alert("Modelo no listo");
  ctx.drawImage(video,0,0,640,480);
  detect();
});

autoBtn.addEventListener('click', () => {
  if (!modelLoaded) return alert("Modelo no listo");
  autoInterval = setInterval(() => { ctx.drawImage(video,0,0,640,480); detect(); }, 3000);
  autoBtn.style.display='none'; stopBtn.style.display='inline-block';
});
stopBtn.addEventListener('click', () => {
  clearInterval(autoInterval);
  autoBtn.style.display='inline-block'; stopBtn.style.display='none';
});

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    fetch('/upload', {method:'POST', body: new FormData(document.createElement('form').append('file', file))})
      .then(r => r.json()).then(d => alert(d.msg || d.error));
  };
  reader.readAsDataURL(file);
});

function detect() {
  fetch('/detect', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({image: canvas.toDataURL('image/jpeg')})
  })
  .then(r => r.json())
  .then(d => {
    if (d.error) return alert(d.error);
    result.src = d.image; result.style.display='block';
    results.innerHTML = '<h5>Detecciones</h5><ul>' +
      d.detections.map(x => `<li>${x.class} → <strong>${x.ripeness}</strong> (${(x.confidence*100).toFixed(0)}%)</li>`).join('') +
      '</ul>';
  });
}
