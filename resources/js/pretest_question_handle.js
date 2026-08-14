const { userId, csrfToken, questions, pretestApiUrl } = window.APP_CONFIG;

const totalQ = questions.length;
let currentQ = 0;
let answers = {}; // { [questionId]: "jawaban isian siswa" }

// ── INIT ──
document.getElementById('qOf').textContent = totalQ;
buildNavGrid();

// Hook dipanggil dari handleIsianInput() di HTML setiap kali siswa mengetik
window.onIsianAnswerChange = function (value) {
  const q = questions[currentQ];
  if (!q) return;
  answers[q.id] = value;

  updateNavGrid();
  updateSidebarProgress();
  checkAllAnswered();
};

goTo(0);

// ── RENDER SOAL ──
function goTo(index) {
  if (index < 0 || index >= totalQ) return;
  currentQ = index;

  const q = questions[index];

  // Badge & progress
  document.getElementById('qNum').textContent = index + 1;
  document.getElementById('qTopic').textContent = q.topic;
  document.getElementById('qProgressFill').style.width = ((index + 1) / totalQ * 100) + '%';

  // Teks soal
  document.getElementById('qText').textContent = q.question;

  // Gambar (jika ada)
  const existingImg = document.getElementById('qImage');
  if (existingImg) existingImg.remove();
  if (q.image && q.image !== 'none') {
    const img = document.createElement('img');
    img.id = 'qImage';
    img.src = '/resources/images/pretest/' + q.image;
    img.alt = 'Gambar soal';
    img.style.cssText = 'max-width:100%;border-radius:12px;margin-bottom:16px;border:2px solid #ede9fe;';
    document.getElementById('qText').before(img);
  }

  // ── Sinkronkan kotak jawaban isian dengan jawaban tersimpan untuk soal ini ──
  const box = document.getElementById('answerIsianBox');
  const savedValue = answers[q.id] || '';
  box.value = savedValue;
  box.classList.toggle('filled', savedValue.trim().length > 0);

  const counter = document.getElementById('isianCharCount');
  if (counter) {
    counter.textContent = savedValue.length + ' karakter';
    counter.classList.toggle('ok', savedValue.trim().length > 0);
  }

  // Tombol prev / next / submit
  document.getElementById('btnPrev').disabled = index === 0;
  const isLast = index === totalQ - 1;
  document.getElementById('btnNext').style.display = isLast ? 'none' : 'inline-flex';
  document.getElementById('btnSubmit').style.display = isLast ? 'inline-flex' : 'none';

  // Warn strip
  document.getElementById('warnStrip').style.display = 'none';

  // Update nav grid & progress sidebar
  updateNavGrid();
  updateSidebarProgress();

  // Fokus otomatis ke kotak jawaban biar langsung bisa mengetik
  box.focus();
}

// ── NAV GRID (sidebar) ──
function buildNavGrid() {
  const grid = document.getElementById('navGrid');
  grid.innerHTML = '';
  questions.forEach((q, i) => {
    const btn = document.createElement('button');
    btn.className = 'nav-num';
    btn.textContent = i + 1;
    btn.id = `navNum${i}`;
    btn.onclick = () => goTo(i);
    grid.appendChild(btn);
  });
}

function isAnswered(q) {
  const val = answers[q.id];
  return typeof val === 'string' && val.trim().length > 0;
}

function updateNavGrid() {
  questions.forEach((q, i) => {
    const btn = document.getElementById(`navNum${i}`);
    if (!btn) return;
    btn.className = 'nav-num';
    if (i === currentQ) btn.classList.add('active');
    else if (isAnswered(q)) btn.classList.add('answered');
  });
}

// ── PROGRESS SIDEBAR ──
function updateSidebarProgress() {
  const answered = questions.filter(isAnswered).length;
  document.getElementById('sbProgressText').textContent = `${answered} / ${totalQ}`;
  document.getElementById('sbProgressFill').style.width = (answered / totalQ * 100) + '%';
}

// ── CEK SEMUA TERJAWAB ──
function checkAllAnswered() {
  const allDone = questions.every(isAnswered);
  document.getElementById('sbSubmitBtn').disabled = !allDone;
  document.getElementById('sbSubmitHint').textContent = allDone ?
    'Semua soal terjawab!' :
    'Jawab semua soal dulu!';
}

// ── SUBMIT ──
function handleSubmit() {
  const allDone = questions.every(isAnswered);
  if (!allDone) {
    const belum = questions.filter(q => !isAnswered(q)).length;
    document.getElementById('warnStrip').style.display = 'flex';
    document.getElementById('warnText').textContent =
      `Masih ada ${belum} soal yang belum dijawab!`;
    return;
  }

  fetch(pretestApiUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({
      user_id: userId,
      answers: answers,
      time_taken: DURATION - timeLeft
    })
  })
  .then(res => res.json())
  .then(data => {
      if (data.redirect_url) {
          window.location.href = data.redirect_url;
      }
  })
  .catch(err => console.error('Error:', err));
}