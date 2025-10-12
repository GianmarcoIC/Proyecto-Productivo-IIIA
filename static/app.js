const video  = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx    = canvas.getContext('2d');
const result = document.getElementById('result');
const out    = document.getElementById('results');
const btn    = document.getElementById('capture');
const auto   = document.getElementById('auto');
const stop   = document.getElementById('stop');

let statsChart;
let autoInterval;

navigator.mediaDevices.getUserMedia({video:true})
  .then(s => video.srcObject = s)
  .catch(e => console.error(e));

function drawChart(stats){
  const labels = Object.keys(stats);
  const data   = Object.values(stats);
  const cfg = {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: ['#4CAF50','#FFC107','#F44336']
      }]
    },
    options: { responsive: false, plugins: { legend: { position: 'bottom' } } }
  };
  if(statsChart) statsChart.destroy();
  statsChart = new Chart(document.getElementById('statsChart'), cfg);
}

function detect() {
  ctx.drawImage(video, 0, 0, 640, 480);
  fetch('/detect', {
    method : 'POST',
    headers: {'Content-Type':'application/json'},
    body   : JSON.stringify({image: canvas.toDataURL('image/jpeg')})
  })
  .then(r => r.json())
  .then(d => {
    if(d.error) return out.innerHTML = `<p>Error: ${d.error}</p>`;
    result.src = d.image;
    result.style.display = 'block';
    out.innerHTML = '<h3>Resultados:</h3><ul>' +
      d.detections.map(x =>
        `<li>${x.class} → <strong>${x.ripeness}</strong> (${(x.confidence*100).toFixed(0)}%)</li>`).join('') +
      '</ul>';
    drawChart(d.stats);
    updateGallery(d.library);
  });
}

function updateGallery(lib) {
  const gallery = document.getElementById('gallery');
  gallery.innerHTML = '';
  lib.forEach(item => {
    gallery.innerHTML += `
      <div class="col-md-3 mb-4">
        <div class="card">
          <img src="${item.url}" class="card-img-top" alt="${item.fruit}">
          <div class="card-body">
            <h5 class="card-title">${item.fruit}</h5>
            <p class="card-text">Estado: <strong>${item.ripeness}</strong></p>
            <p class="text-muted">${item.date}</p>
          </div>
        </div>
      </div>
    `;
  });
}

btn.addEventListener('click', detect);

auto.addEventListener('click', () => {
  autoInterval = setInterval(detect, 3000);
  auto.style.display = 'none';
  stop.style.display = 'inline-block';
});

stop.addEventListener('click', () => {
  clearInterval(autoInterval);
  auto.style.display = 'inline-block';
  stop.style.display = 'none';
});
