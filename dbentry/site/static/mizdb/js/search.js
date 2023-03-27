window.addEventListener("load", (event) => {
    const searchInput = document.querySelector('#searchInput');
    const searchURL = searchInput.dataset.searchUrl;
    const searchResults = document.querySelector('#searchResults');

    searchInput.addEventListener("input", (event) => {
        function addResults() {
            fetch(`${searchURL}?q=${event.target.value}`)
                .then((response) => response.json())
                .then((data) => {
                    searchResults.innerHTML = "";
                    const result_list = document.createElement("ul");
                    for (link_html of data.results) {
                        const result_item = document.createElement("li");
                        result_item.innerHTML = link_html;
                        result_list.appendChild(result_item);
                    }
                    searchResults.appendChild(result_list)
                })
        }

        window.clearTimeout(this.delay);
        this.delay = window.setTimeout(addResults, 250);
    });
});