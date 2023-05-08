function set_theme(theme_name) {
    const link = document.getElementById("theme") ;
    link.setAttribute("href", `https://cdn.jsdelivr.net/npm/bootswatch@5.2.3/dist/${theme_name}/bootstrap.min.css`);
}

addEventListener("DOMContentLoaded", (event) => {
    document.querySelectorAll(".change-style-menu-item").forEach((elem) => {
        elem.addEventListener("click", (event) => {
            event.preventDefault();
            var theme_name = event.target.getAttribute('rel');
            set_theme(theme_name)
        });
    });
});