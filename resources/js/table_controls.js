(() => {
  const PAGE_SIZES = [10, 25, 50];

  function addElement(tag, className, text) {
    const element = document.createElement(tag);
    element.className = className;
    if (text) element.textContent = text;
    return element;
  }

  function setupTable(table) {
    const body = table.tBodies[0];
    if (!body) return;

    const allRows = Array.from(body.rows);
    const dataRows = allRows.filter(row => !row.querySelector('td[colspan]'));
    const emptyRow = allRows.find(row => row.querySelector('td[colspan]'));
    const card = table.closest('.bg-white.rounded-2xl, .bg-white.rounded-lg, .bg-surface') || table.parentElement;
    const scrollArea = table.closest('.overflow-x-auto') || table;
    let search = card.querySelector('input[type="search"]');

    if (!search) {
      const searchBar = addElement('div', 'px-4 py-3 border-b border-gray-100');
      search = addElement('input', 'w-full sm:max-w-sm border border-gray-200 rounded-xl px-4 py-2 text-sm');
      search.type = 'search';
      search.placeholder = 'Cari data tabel...';
      searchBar.append(search);
      card.insertBefore(searchBar, scrollArea);
    }
    search.setAttribute('aria-label', 'Cari isi tabel');

    const controls = addElement('div', 'table-controls flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-4 py-3 text-sm text-gray-600');
    const summary = addElement('span', 'table-page-summary');
    const pageSizeLabel = addElement('label', 'flex items-center gap-2');
    pageSizeLabel.append(document.createTextNode('Baris per halaman'));
    const pageSize = addElement('select', 'border border-gray-200 rounded-lg px-2 py-1 bg-white');
    pageSize.setAttribute('aria-label', 'Jumlah baris per halaman');
    PAGE_SIZES.forEach(size => {
      const option = document.createElement('option');
      option.value = String(size);
      option.textContent = String(size);
      pageSize.append(option);
    });
    pageSize.value = '10';
    pageSizeLabel.append(pageSize);

    const pager = addElement('div', 'flex items-center gap-2');
    const previous = addElement('button', 'border border-gray-200 rounded-lg px-3 py-1 hover:bg-gray-50 disabled:opacity-40', 'Sebelumnya');
    previous.type = 'button';
    const pageLabel = addElement('span', 'min-w-16 text-center');
    const next = addElement('button', 'border border-gray-200 rounded-lg px-3 py-1 hover:bg-gray-50 disabled:opacity-40', 'Berikutnya');
    next.type = 'button';
    pager.append(previous, pageLabel, next);
    controls.append(summary, pageSizeLabel, pager);
    scrollArea.insertAdjacentElement('afterend', controls);

    let currentPage = 1;
    let filteredRows = dataRows;
    let filterEmpty = null;

    function render() {
      const query = search.value.trim().toLocaleLowerCase();
      filteredRows = dataRows.filter(row => row.textContent.toLocaleLowerCase().includes(query));
      const pageCount = Math.max(1, Math.ceil(filteredRows.length / Number(pageSize.value)));
      currentPage = Math.min(currentPage, pageCount);
      const start = (currentPage - 1) * Number(pageSize.value);
      const visibleRows = new Set(filteredRows.slice(start, start + Number(pageSize.value)));

      dataRows.forEach(row => { row.hidden = !visibleRows.has(row); });
      if (emptyRow) emptyRow.hidden = dataRows.length > 0;

      if (!filterEmpty) {
        filterEmpty = document.createElement('tr');
        filterEmpty.dataset.filterEmpty = 'true';
        const cell = document.createElement('td');
        cell.className = 'px-4 py-6 text-center text-gray-500';
        cell.colSpan = Math.max(table.tHead?.rows[0]?.cells.length || 1, 1);
        cell.textContent = 'Tidak ada data yang cocok dengan pencarian.';
        filterEmpty.append(cell);
        body.append(filterEmpty);
      }
      filterEmpty.hidden = filteredRows.length > 0 || dataRows.length === 0;

      const first = filteredRows.length ? start + 1 : 0;
      const last = Math.min(start + Number(pageSize.value), filteredRows.length);
      summary.textContent = `Menampilkan ${first}–${last} dari ${filteredRows.length} baris`;
      pageLabel.textContent = `${currentPage} / ${pageCount}`;
      previous.disabled = currentPage <= 1;
      next.disabled = currentPage >= pageCount;
    }

    search.addEventListener('input', () => { currentPage = 1; render(); });
    pageSize.addEventListener('change', () => { currentPage = 1; render(); });
    previous.addEventListener('click', () => { currentPage -= 1; render(); });
    next.addEventListener('click', () => { currentPage += 1; render(); });
    render();
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('table[data-table-controls]').forEach(setupTable);
  });
})();
