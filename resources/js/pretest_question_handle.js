const { userId, csrfToken, questions, pretestApiUrl } = window.APP_CONFIG;

const totalQ = questions.length;
let currentQ = 0;
let answers = {}; // { [questionId]: "jawaban isian siswa" }
const draftKey = `edudaya:evaluation:${userId}`;

function setSaveStatus(message, state = '') {
  const status = document.getElementById('answerSaveStatus');
  if (!status) return;
  status.textContent = message;
  status.dataset.state = state;
}

function saveDraft() {
  try {
    localStorage.setItem(draftKey, JSON.stringify(answers));
    setSaveStatus('Draft tersimpan di perangkat ini · belum dikirim ke server', 'local');
  } catch (error) {
    setSaveStatus('Draft lokal tidak dapat disimpan', 'error');
    console.warn('Draft evaluasi lokal tidak dapat disimpan.', error);
  }
}

try {
  const saved = JSON.parse(localStorage.getItem(draftKey) || '{}');
  if (saved && typeof saved === 'object' && !Array.isArray(saved)) answers = saved;
} catch (error) {
  console.warn('Draft evaluasi lokal tidak dapat dibaca.', error);
}

// ── INIT ──
document.getElementById('qOf').textContent = totalQ;
buildNavGrid();

// Hook dipanggil dari handleIsianInput() di HTML setiap kali siswa mengetik
window.onIsianAnswerChange = function (value) {
  const q = questions[currentQ];
  if (!q) return;
  answers[q.id] = value;
  saveDraft();

  updateNavGrid();
  updateSidebarProgress();
  checkAllAnswered();
};

goTo(0);

// ── RENDER SOAL ──
function renderOptions(q) {
  const list = document.getElementById('optionsList');
  if (!list) return false;

  const options = Array.isArray(q.options) ? q.options : [];
  if (options.length === 0) {
    list.style.display = 'none';
    list.innerHTML = '';
    return false;
  }

  list.style.display = 'flex';
  list.innerHTML = '';
  options.forEach(opt => {
    const label = document.createElement('label');
    label.className = 'opt-label' + (answers[q.id] === opt.id ? ' selected' : '');
    label.dataset.optionId = opt.id;

    const radio = document.createElement('span');
    radio.className = 'opt-radio';
    const text = document.createElement('span');
    text.textContent = `${String(opt.id).toUpperCase()}. ${opt.text}`;
    label.append(radio, text);

    label.addEventListener('click', () => {
      answers[q.id] = opt.id;
      saveDraft();
      list.querySelectorAll('.opt-label').forEach(el => {
        el.classList.toggle('selected', el.dataset.optionId === opt.id);
      });
      updateNavGrid();
      updateSidebarProgress();
      checkAllAnswered();
    });

    list.appendChild(label);
  });
  return true;
}

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

  // Pilihan ganda (evaluation) atau isian (pretest)
  const isChoice = renderOptions(q);
  const isianWrap = document.getElementById('answerIsianWrap');
  if (isianWrap) isianWrap.style.display = isChoice ? 'none' : 'flex';

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
  if (box) {
    box.value = isChoice ? '' : savedValue;
    box.classList.toggle('filled', !isChoice && savedValue.trim().length > 0);
  }

  const counter = document.getElementById('isianCharCount');
  if (counter) {
    counter.textContent = (isChoice ? 0 : savedValue.length) + ' karakter';
    counter.classList.toggle('ok', !isChoice && savedValue.trim().length > 0);
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
  if (box && !isChoice) box.focus();
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
  setSaveStatus(`${answered} dari ${totalQ} jawaban · tersimpan lokal, belum dikirim`, 'local');
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
let submitting = false;
function handleSubmit() {
  if (submitting) return;
  const allDone = questions.every(isAnswered);
  if (!allDone) {
    const belum = questions.filter(q => !isAnswered(q)).length;
    document.getElementById('warnStrip').style.display = 'flex';
    document.getElementById('warnText').textContent =
      `Masih ada ${belum} soal yang belum dijawab!`;
    return;
  }

  submitting = true;
  setSaveStatus('Mengirim jawaban ke server…', 'sending');
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
  .then(async res => ({ ok: res.ok, data: await res.json() }))
  .then(({ ok, data }) => {
      if (data.redirect_url) {
          try { localStorage.removeItem(draftKey); } catch (error) { console.warn(error); }
          setSaveStatus('Jawaban berhasil disimpan ke server', 'saved');
          window.location.assign(data.redirect_url);
      } else {
          submitting = false;
          setSaveStatus(ok ? 'Jawaban belum dikonfirmasi tersimpan' : 'Server menolak pengiriman · draft tetap tersimpan lokal', 'error');
          alert(data.error || 'Jawaban belum dikonfirmasi tersimpan. Draft masih tersimpan di perangkat ini, periksa koneksi lalu kirim lagi.');
      }
  })
  .catch(err => {
      submitting = false;
      console.error('Error:', err);
      setSaveStatus('Koneksi gagal · draft masih tersimpan di perangkat ini', 'error');
      alert('Koneksi gagal. Jawabanmu masih tersimpan sebagai draft di perangkat ini. Periksa koneksi lalu kirim lagi.');
  });
}
