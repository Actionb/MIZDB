window.addEventListener("load", (event) => {
    const searchInput = document.querySelector('#searchInput');
    const searchURL = searchInput.dataset.searchUrl;
    const searchResults = document.querySelector('#searchResults');

    searchInput.addEventListener("input", (event) => {
        function addResults() {
            const decoder = new TextDecoder();

            fetch(`${searchURL}?q=${event.target.value}`)
                .then((response) => response.body.getReader().read())
                .then((r) => {searchResults.innerHTML = decoder.decode(r.value); })
        }

        window.clearTimeout(this.delay);
        this.delay = window.setTimeout(addResults, 250);
    });
});