/* Set a new theme. */
function set_theme(theme_url) {
    const link = document.getElementById("user_theme") ;
    link.setAttribute("href", theme_url);
    localStorage.theme_url = theme_url;
}

/* Load the user's current theme. */
// TODO: move into template as a self-executing function
function load_initial_theme() {
    const theme_url = localStorage.theme_url
    if (theme_url) {
        set_theme(theme_url);
    }
}

/* Set the currently selected theme's dropdown item to active. */
function set_active_theme(elem) {
    if (elem === undefined) {
        const theme_url = document.getElementById("user_theme").getAttribute("href");
        elem = document.querySelector(`#theme-container a[rel="${theme_url}"`);
    }
    if (elem) {
        document.querySelectorAll("#theme-container a").forEach((elem) => elem.classList.remove("active"));
        elem.classList.add("active");
    }
}

addEventListener("DOMContentLoaded", (event) => {
    /* Load available themes from the bootswatch API and create dropdown items for
     each theme. */
    fetch("https://bootswatch.com/api/5.json")
        .then((response) => response.json())
        .then((data) => {
            const container = document.getElementById("theme-container");
            for (var theme of data.themes) {
                const listItem = document.createElement("li");
                const switchBtn = document.createElement("a");
                switchBtn.setAttribute("rel", theme.cssCdn);
                switchBtn.setAttribute("href", "#");
                switchBtn.setAttribute("class", "change-style-menu-item dropdown-item");
                switchBtn.innerText = theme.name;
                listItem.appendChild(switchBtn);
                container.appendChild(listItem);
            }
        });

    set_active_theme();  // for the initial theme

    // Add click event listeners for all theme buttons in the dropdown
    document.getElementById("theme-container").addEventListener("click", (event) => {
        event.preventDefault();
        const elem = event.target;
        set_theme(elem.getAttribute('rel'));
        set_active_theme(elem);
    });
});