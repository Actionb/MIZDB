/* Set a new theme. */
function set_theme(theme_url) {
    const link = document.getElementById("user_theme");
    if (link) {
        link.setAttribute("href", theme_url);
        localStorage.setItem("mizdb_theme_url", theme_url);
   }
}

/* Set the currently selected theme's dropdown item to active. */
function set_active_theme(elem) {
    if (elem) {
        document.querySelectorAll("#theme-dropdown a").forEach((elem) => elem.classList.remove("active"));
        elem.classList.add("active");
    }
}

addEventListener("DOMContentLoaded", (event) => {
    const dropdown = document.getElementById("theme-dropdown");
    const link = document.getElementById("user_theme");
    // Load additional themes from the bootswatch API and add them to the theme dropdown.
    /* FIXME: some of the themes import fonts hosted by google, resulting
        in issues with cross-origin request restrictions, see:
        https://github.com/jrief/django-formset/pull/44
        https://github.com/thomaspark/bootswatch/issues/573
        https://stackoverflow.com/questions/34772357/bootstrap-css-without-google-fonts-2-bootswatch
    */
    // TODO: self-host the fonts and recompile the themes
    if (dropdown && link) {
        fetch("https://bootswatch.com/api/5.json")
            .then((response) => response.json())
            .then((data) => {
                for (var theme of data.themes) {
                    const listItem = document.createElement("li");
                    const switchBtn = document.createElement("a");
                    switchBtn.setAttribute("rel", theme.cssCdn);
                    switchBtn.setAttribute("href", "#");
                    switchBtn.setAttribute("class", "change-theme-menu-item dropdown-item");
                    switchBtn.setAttribute("crossorigin", "anonymous");
                    switchBtn.innerText = theme.name;
                    listItem.appendChild(switchBtn);
                    dropdown.appendChild(listItem);
                }
            });

        // Add click event listener for the theme dropdown items.
        dropdown.addEventListener("click", (event) => {
            event.preventDefault();
            const elem = event.target;
            set_theme(elem.getAttribute('rel'));
            set_active_theme(elem);
        });
    
        // Set the menu item of the initial theme to active.
        const theme_url = link.getAttribute("href");
        const elem = document.querySelector(`#theme-dropdown a[rel="${theme_url}"`);
        set_active_theme(elem);
    }
});

/* Load the user's current theme. */
(() => set_theme(localStorage.getItem("mizdb_theme_url")))();