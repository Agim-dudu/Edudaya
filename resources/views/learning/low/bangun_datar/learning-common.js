window.JAWABAN_SOAL = window.JAWABAN_SOAL || {};
function periksaSoal(id){
    const input=document.getElementById('ans-'+id), fb=document.getElementById('fb-'+id), sol=document.getElementById('sol-'+id);
    if(!input||!fb)return;
    let val=input.value.trim().replace(/\s+/g,'');
    if(val===''){fb.innerHTML='<div class="bg-yellow-100 border-2 border-yellow-400 rounded-xl p-3 text-sm font-bold text-yellow-700">✏️ Tulis jawabanmu dulu ya!</div>';return;}
    const num=parseFloat(val.replace(',','.'));
    const map=window.JAWABAN_SOAL||{};
    const ben=map[id];
    if(ben!==undefined && !isNaN(num)&&Math.abs(num-ben)<0.01){fb.innerHTML='<div class="bg-green-100 border-2 border-green-400 rounded-xl p-3 text-sm font-bold text-green-700">🎉 BENAR! Hebat!</div>'; if(sol)sol.classList.remove('hidden');}
    else{fb.innerHTML='<div class="bg-red-100 border-2 border-red-400 rounded-xl p-3 text-sm font-bold text-red-600">😊 BELUM TEPAT! Coba perhatikan lagi ya!</div>'; if(sol)sol.classList.remove('hidden');}
}
let sidebarOpen=true;
function toggleSidebar(){const s=document.getElementById('sidebar'),m=document.getElementById('mainArea'),o=document.getElementById('sidebarOverlay'),mob=window.innerWidth<=768;if(mob){const h=s.classList.contains('-translate-x-full');if(h){s.classList.remove('-translate-x-full');o.classList.remove('hidden');o.classList.add('flex');}else{s.classList.add('-translate-x-full');o.classList.add('hidden');o.classList.remove('flex');}}else{sidebarOpen=!sidebarOpen;if(sidebarOpen){s.classList.remove('-translate-x-full');m.classList.remove('ml-0');m.classList.add('ml-[280px]');}else{s.classList.add('-translate-x-full');m.classList.remove('ml-[280px]');m.classList.add('ml-0');}}}
function closeSidebar(){const s=document.getElementById('sidebar'),o=document.getElementById('sidebarOverlay');s.classList.add('-translate-x-full');o.classList.add('hidden');o.classList.remove('flex');}
function toggleSidebarMenu(h){const i=h.querySelector('ion-icon'),l=h.nextElementSibling;const op=!l.classList.contains('hidden');l.classList.toggle('hidden',op);l.classList.toggle('flex',!op);i.style.transform=op?'':'rotate(180deg)';}
function initSidebar(){var p=window.location.pathname;document.querySelectorAll('#sidebar a').forEach(function(a){if(a.getAttribute('href')&&p.indexOf(a.getAttribute('href'))!==-1){var u=a.closest('ul');if(u&&u.classList.contains('hidden')){u.classList.remove('hidden');u.classList.add('flex');var hh=u.previousElementSibling;if(hh){var ic=hh.querySelector('ion-icon');if(ic)ic.style.transform='rotate(180deg)';}}}});}
document.addEventListener('DOMContentLoaded',()=>{
    if(window.innerWidth<=768){document.getElementById('sidebar').classList.add('-translate-x-full');document.getElementById('mainArea').classList.remove('ml-[280px]');document.getElementById('mainArea').classList.add('ml-0');}
    initSidebar();
    const gifs=document.querySelectorAll('img.gif-lazy');
    if('IntersectionObserver' in window){const obs=new IntersectionObserver((entries)=>{entries.forEach(e=>{if(e.isIntersecting){const img=e.target;if(img.dataset.src){img.src=img.dataset.src;img.removeAttribute('data-src');}obs.unobserve(img);}});},{rootMargin:'50px'});gifs.forEach(g=>obs.observe(g));}else{gifs.forEach(img=>{if(img.dataset.src){img.src=img.dataset.src;img.removeAttribute('data-src');}});}
    document.querySelectorAll('img').forEach(img => {
        if(img.closest('#sidebar')||img.closest('nav')||img.id==='imgLightboxImg')return;
        if(img.src && !img.classList.contains('no-lightbox')){
            img.style.cursor='zoom-in';
            img.addEventListener('click',function(e){e.preventDefault();const lb=document.getElementById('imgLightbox'),lbi=document.getElementById('imgLightboxImg');if(lb&&lbi){lbi.src=img.currentSrc||img.src;lbi.alt=img.alt;lb.classList.remove('hidden');lb.classList.add('flex');document.body.style.overflow='hidden';}});
        }
    });
});
