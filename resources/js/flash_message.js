        // Tunggu sampai halaman selesai dimuat
        document.addEventListener('DOMContentLoaded', function () {
            const flashContainer = document.getElementById('flash-messages');

            if (flashContainer) {
                // Setel waktu tunggu (misal: 3000ms = 3 detik)
                setTimeout(function () {
                    // Tambahkan efek transisi halus (opacity 0)
                    flashContainer.style.transition = "opacity 0.6s ease";
                    flashContainer.style.opacity = "0";

                    // Hapus elemen sepenuhnya dari layout setelah transisi selesai
                    setTimeout(function () {
                        flashContainer.remove();
                    }, 600);
                }, 3000);
            }
        });