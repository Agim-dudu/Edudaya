const { userId, csrfToken, questions, pretestApiUrl } = window.APP_CONFIG;

const waktuPengerjaan = 120;
const totalQ = questions.length;
let currentQ = 0;
let answers = {};

// ── INIT ──
document.getElementById('qOf').textContent = totalQ;
buildNavGrid();
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

  // Pilihan jawaban
  const list = document.getElementById('optionsList');
  list.innerHTML = '';
  q.options.forEach(opt => {
    const selected = answers[q.id] === opt.id ? 'selected' : '';
    list.innerHTML += `
      <label class="opt-label ${selected}" onclick="selectAnswer(${q.id}, '${opt.id}', this)">
        <input type="radio" name="q${q.id}" value="${opt.id}" ${selected ? 'checked' : ''}>
        <div class="opt-radio"><div class="opt-radio-dot"></div></div>
        <div class="opt-letter">${opt.id.toUpperCase()}</div>
        <div class="opt-text">${opt.text}</div>
      </label>`;
  });

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
}

// ── PILIH JAWABAN ──
function selectAnswer(questionId, optionId, clickedLabel) {
  answers[questionId] = optionId;

  // Update visual semua label di soal ini
  document.querySelectorAll('#optionsList .opt-label').forEach(lbl => {
    lbl.classList.remove('selected');
  });
  clickedLabel.classList.add('selected');

  updateNavGrid();
  updateSidebarProgress();
  checkAllAnswered();
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

function updateNavGrid() {
  questions.forEach((q, i) => {
    const btn = document.getElementById(`navNum${i}`);
    if (!btn) return;
    btn.className = 'nav-num';
    if (i === currentQ) btn.classList.add('active');
    else if (answers[q.id]) btn.classList.add('answered');
  });
}

// ── PROGRESS SIDEBAR ──
function updateSidebarProgress() {
  const answered = Object.keys(answers).length;
  document.getElementById('sbProgressText').textContent = `${answered} / ${totalQ}`;
  document.getElementById('sbProgressFill').style.width = (answered / totalQ * 100) + '%';
}

// ── CEK SEMUA TERJAWAB ──
function checkAllAnswered() {
  const allDone = Object.keys(answers).length === totalQ;
  document.getElementById('sbSubmitBtn').disabled = !allDone;
  document.getElementById('sbSubmitHint').textContent = allDone ?
    'Semua soal terjawab!' :
    'Jawab semua soal dulu!';
}

// ── SUBMIT ──
function handleSubmit() {
  const allDone = Object.keys(answers).length === totalQ;
  if (!allDone) {
    document.getElementById('warnStrip').style.display = 'flex';
    document.getElementById('warnText').textContent =
      `Masih ada ${totalQ - Object.keys(answers).length} soal yang belum dijawab!`;
    return;
  }

  fetch(pretestApiUrl, {          // ← pakai variabel, bukan template literal
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({
      user_id: userId,
      answers: answers,
      time_taken: waktuPengerjaan
    })
  })
  .then(res => res.json())
  .then(data => {
      if (data.redirect_url) {
          window.location.href = data.redirect_url;  // ← navigasi manual
      }
  })
  .catch(err => console.error('Error:', err));
  }