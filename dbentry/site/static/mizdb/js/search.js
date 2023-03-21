window.addEventListener("load", (event) => {
    const searchInput = document.querySelector('#searchInput');
    const searchResults = document.querySelector('#searchResults');

    // TODO: "keydown" might be the wrong trigger for this? (triggers one keypress too late?)
    searchInput.addEventListener("keydown", (event) => {
        fetch(`http://127.0.0.1:8000/searchbar/?q=${event.target.value}`)
            .then((response) => response.json())
            .then((data) => {
                // FIXME: search is too slow - caching?
                searchResults.innerHTML = "";
                const result_list = document.createElement("ul");
                for (link_html of data.results) {
                    const result_item = document.createElement("li");
                    result_item.innerHTML = link_html;
                    result_list.appendChild(result_item);
                }
                searchResults.appendChild(result_list)
            })
    });
});