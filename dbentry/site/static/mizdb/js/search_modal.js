/**
 * Search function for the searchbar search modal.
 */
window.addEventListener('load', () => {
  const searchModal = document.querySelector('#searchModal')
  const searchInput = document.querySelector('#searchInput')
  searchModal.addEventListener('shown.bs.modal', () => searchInput.focus())
  searchInput.addEventListener('input', debounce((e) => search(e.target.value)))
  let controller = new AbortController()

  function search (q) {
    if (q.length < 3) return
    const searchURL = searchInput.dataset.searchUrl
    const searchResults = document.querySelector('#searchResults')
    const searchSpinner = document.querySelector('#searchSpinner')
    const chevronUp = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-chevrons-up"><polyline points="17 11 12 6 7 11"></polyline><polyline points="17 18 12 13 7 18"></polyline></svg>'
    const chevronDown = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-chevrons-down"><polyline points="7 13 12 18 17 13"></polyline><polyline points="7 6 12 11 17 6"></polyline></svg>'

    const params = new URLSearchParams({ q })
    if (searchInput.dataset.popup) params.append('popup', true)

    searchResults.innerHTML = ''
    searchSpinner.classList.remove('d-none')

    fetch(`${searchURL}?${params.toString()}`, { signal: controller.signal })
      .then((response) => response.json())
      .then((data) => {
        searchSpinner.classList.add('d-none')
        searchResults.innerHTML = ''
        if (data.total_count === 0) {
          searchResults.innerHTML = '<p class="ps-3">Keine Ergebnisse</p>'
        } else {
          const results = makeDomElement('<ul class="list-group list-group-flush"></ul>')
          const count = data.total_count
          for (const result of data.results) {
            const modelResult = makeDomElement('<li class="list-group-item list-group-item-action"></li>')

            // Add a title div that contains the changelist link and a toggler
            // button for the collapsible result list.
            const title = makeDomElement('<div class="d-flex justify-content-between"></div>')
            title.innerHTML = result.changelist_link
            modelResult.appendChild(title)

            if (result.details) {
              // Append more detailed results in a nested list.
              const objectResults = makeDomElement(`<ul id="id_${result.model_name}_results" class="collapse"></ul>`)
              for (const detail of result.details) {
                objectResults.appendChild(makeDomElement(`<li>${detail}</li>`))
              }
              modelResult.appendChild(objectResults)

              // Add a toggler for the list:
              const toggler = makeDomElement(`<a href="" class="results-toggler" data-bs-toggle="collapse" data-bs-target="#${objectResults.id}" title="Ergebnisse zeigen/verstecken"></a>`)
              if (count < 20) {
                objectResults.classList.add('show')
                toggler.innerHTML = chevronUp
                toggler.title = 'Ergebnisse verstecken'
              } else {
                toggler.innerHTML = chevronDown
                toggler.title = 'Ergebnisse anzeigen'
              }
              toggler.addEventListener('click', (e) => {
                e.preventDefault()
                if (toggler.classList.contains('collapsed')) {
                  toggler.innerHTML = chevronDown
                  toggler.title = 'Ergebnisse anzeigen'
                } else {
                  toggler.innerHTML = chevronUp
                  toggler.title = 'Ergebnisse verstecken'
                }
              })
              title.appendChild(toggler)
            }

            results.appendChild(modelResult)
          }
          searchResults.appendChild(results)
        }
      })
      .catch((error) => console.log(error))
  }

  function makeDomElement (html) {
    const tpl = document.createElement('template')
    // Utilize automatic parsing of the value when setting innerHTML
    // https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML#replacing_the_contents_of_an_element
    tpl.innerHTML = html.trim()
    return tpl.content.firstChild
  }

  // https://www.freecodecamp.org/news/javascript-debounce-example/
  function debounce (func, timeout = 500) {
    let timeoutID
    return (...args) => {
      // Abort previous timeout and fetch request:
      clearTimeout(timeoutID)
      controller.abort()
      // Create a new abort controller so it can be consumed again to abort a
      // request.
      controller = new AbortController()
      timeoutID = setTimeout(() => {
        func.apply(this, args)
      }, timeout)
    }
  }
})
