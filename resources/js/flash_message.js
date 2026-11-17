        // Tunggu sampai halaman selesai dimuat
document.addEventListener('DOMContentLoaded', function () {
    const flashContainer = document.getElementById('flash-messages');
    if (!flashContainer) return;

    // Keep long analysis summaries visible until the user dismisses them.
    // Short, single-line notices can still clear themselves after a few seconds.
    const messages = flashContainer.querySelectorAll('[data-flash-item]');
    const hasLongMessage = Array.from(messages).some((message) => {
        const text = message.innerText?.trim() || '';
        return text.length > 180 || text.includes('Batch ');
    });
    const requestedDuration = Number(document.body.dataset.flashDuration);

    if (!hasLongMessage || requestedDuration > 0) {
        window.setTimeout(function () {
            flashContainer.style.transition = 'opacity 0.4s ease';
            flashContainer.style.opacity = '0';
            window.setTimeout(function () {
                flashContainer.remove();
            }, 400);
        }, requestedDuration > 0 ? requestedDuration : 5000);
    }
});
