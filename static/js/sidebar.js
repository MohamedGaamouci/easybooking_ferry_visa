console.log("sidebar script loaded secessfelly")
document.addEventListener("DOMContentLoaded", () => {
    const currentUrlName = request.resolver_match.url_name;
    const links = document.querySelectorAll('#sidebar-nav a.nav-item');

    links.forEach(link => {
        if (link.dataset.url === currentUrlName) {
            link.classList.add(
                "bg-brand-600",
                "text-white",
                "shadow-lg",
                "shadow-brand-900/20"
            );

            const badge = link.querySelector('span.rounded-full');
            if (badge && !badge.classList.contains('bg-red-500')) {
                badge.classList.remove('bg-slate-700', 'text-slate-300');
                badge.classList.add('bg-white', 'text-brand-700');
            }
        }
    });
});