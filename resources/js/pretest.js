// ── SIDEBAR STATE ──
let sidebarOpen = true;

function toggleSidebar() {
  sidebarOpen = !sidebarOpen;

  const burgerBtn = document.getElementById('burgerBtn');
  const sidebar   = document.getElementById('sidebar');
  const overlay   = document.getElementById('sidebarOverlay');
  const main      = document.getElementById('main');

  burgerBtn.classList.toggle('open',    !sidebarOpen);
  sidebar.classList.toggle('collapsed', !sidebarOpen);
  overlay.classList.toggle('show',      !sidebarOpen);
  main.classList.toggle('expanded',     !sidebarOpen);
}

document.getElementById('sidebarOverlay').addEventListener('click', toggleSidebar);


// ── TIMER COUNTDOWN ──
const DURATION = 15 * 60;
let timeLeft   = DURATION;

function formatTime(s) {
  const m = Math.floor(s / 60).toString().padStart(2, '0');
  const d = (s % 60).toString().padStart(2, '0');
  return `${m}:${d}`;
}

function updateTimer() {
  document.getElementById('timerText').textContent = formatTime(timeLeft);
  document.getElementById('timerBox').classList.toggle('urgent', timeLeft <= 120);

  if (timeLeft === 0) {
    clearInterval(timerInterval);
    handleSubmit();
    return;
  }
  timeLeft--;
}

updateTimer();
const timerInterval = setInterval(updateTimer, 1000);
