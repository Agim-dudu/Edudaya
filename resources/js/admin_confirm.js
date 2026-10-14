document.addEventListener('submit', function (event) {
    const form = event.target;
    if (form.matches('form[data-confirm]') && !window.confirm(form.dataset.confirm)) {
        event.preventDefault();
    }
});
