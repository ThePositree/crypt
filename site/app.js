const canvas = document.querySelector("#equityChart");
const ctx = canvas.getContext("2d");

const points = [54, 62, 58, 74, 68, 92, 84, 101, 97, 118, 112, 136, 128, 149];

function drawChart() {
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.round(rect.width * scale);
  canvas.height = Math.round(rect.height * scale);
  ctx.setTransform(scale, 0, 0, scale, 0, 0);

  const width = rect.width;
  const height = rect.height;
  const padding = Math.max(24, width * 0.055);
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;
  const min = Math.min(...points) - 10;
  const max = Math.max(...points) + 10;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfcff";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#e4e9f1";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = padding + (chartHeight / 4) * i;
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
  }

  const coords = points.map((point, index) => {
    const x = padding + (chartWidth / (points.length - 1)) * index;
    const y = padding + chartHeight - ((point - min) / (max - min)) * chartHeight;
    return { x, y };
  });

  const fill = ctx.createLinearGradient(0, padding, 0, height - padding);
  fill.addColorStop(0, "rgba(18, 105, 211, 0.2)");
  fill.addColorStop(1, "rgba(24, 162, 184, 0.02)");

  ctx.beginPath();
  coords.forEach((coord, index) => {
    if (index === 0) {
      ctx.moveTo(coord.x, coord.y);
    } else {
      ctx.lineTo(coord.x, coord.y);
    }
  });
  ctx.lineTo(width - padding, height - padding);
  ctx.lineTo(padding, height - padding);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();

  ctx.beginPath();
  coords.forEach((coord, index) => {
    if (index === 0) {
      ctx.moveTo(coord.x, coord.y);
    } else {
      ctx.lineTo(coord.x, coord.y);
    }
  });
  ctx.strokeStyle = "#1269d3";
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.stroke();

  coords.forEach((coord, index) => {
    if (index % 3 !== 0 && index !== coords.length - 1) {
      return;
    }
    ctx.beginPath();
    ctx.arc(coord.x, coord.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = index === coords.length - 1 ? "#168a5b" : "#ffffff";
    ctx.fill();
    ctx.strokeStyle = "#1269d3";
    ctx.lineWidth = 2;
    ctx.stroke();
  });

  ctx.fillStyle = "#656b78";
  ctx.font = "600 12px Inter, system-ui, sans-serif";
  ctx.fillText("illustrative research equity", padding, padding - 8);
}

drawChart();
window.addEventListener("resize", drawChart);
