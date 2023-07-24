window.addEventListener("load", (event) => {
    const searchInput = document.querySelector('#searchInput');
    const searchURL = searchInput.dataset.searchUrl;
    const popup = searchInput.dataset.popup;
    const searchResults = document.querySelector('#searchResults');

    searchInput.addEventListener("input", (event) => {
        function addResults() {
            const decoder = new TextDecoder();
            const params = new URLSearchParams({q: event.target.value})
            if (popup) params.append('popup', true)

            fetch(`${searchURL}?${params.toString()}`)
                .then((response) => response.json())
                .then((data) => {
                    searchResults.innerHTML = "";
                    if (data.total_count == 0) {
                        searchResults.innerHTML = '<p class="ps-3">Keine Ergebnisse</p>';
                    }
                    else {
                        const results = document.createElement("ul");
                        const total_count = data.total_count;
                        for (result of data.results) {
                            const category = document.createElement("li");
                            category.innerHTML = result.category;
                            if (total_count <= 15){
                                const sublist = document.createElement("ul");
                                for (item of result.items) {
                                    const result_item = document.createElement("li");
                                    result_item.innerHTML = item;
                                    sublist.appendChild(result_item)
                                }
                                category.appendChild(sublist)
                            }
                            results.appendChild(category);
                        }
                        searchResults.appendChild(results);
                    }
                })
        }

        window.clearTimeout(this.delay);
        this.delay = window.setTimeout(addResults, 250);
    });
});