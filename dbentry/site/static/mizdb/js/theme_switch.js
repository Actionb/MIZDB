/**
 * Enable selecting a different theme from a selection of bootstrap themes.
 */
(() => {
  /* Set a new theme. */
  function setTheme (themeUrl) {
    const link = document.getElementById('user_theme')
    if (link) {
      link.setAttribute('href', themeUrl)
      window.localStorage.setItem('mizdb_theme_url', themeUrl)
    }
  }

  /* Set the currently selected theme's dropdown item to active. */
  function setActiveTheme (elem) {
    if (elem) {
      document.querySelectorAll('#theme-dropdown a').forEach((elem) => elem.classList.remove('active'))
      elem.classList.add('active')
    }
  }

  document.addEventListener('DOMContentLoaded', (event) => {
    const dropdown = document.getElementById('theme-dropdown')
    const link = document.getElementById('user_theme')
    // Load additional themes from the bootswatch API and add them to the theme dropdown.
    if (dropdown && link) {
      fetch('https://bootswatch.com/api/5.json')
        .then((response) => response.json())
        .then((data) => {
          for (const theme of data.themes) {
            const listItem = document.createElement('li')
            const switchBtn = document.createElement('a')
            switchBtn.setAttribute('rel', theme.cssCdn)
            switchBtn.setAttribute('href', '#')
            switchBtn.setAttribute('class', 'change-theme-menu-item dropdown-item')
            switchBtn.setAttribute('crossorigin', 'anonymous')
            switchBtn.innerText = theme.name
            listItem.appendChild(switchBtn)
            dropdown.appendChild(listItem)
          }
        })

      // Add click event listener for the theme dropdown items.
      dropdown.addEventListener('click', (event) => {
        event.preventDefault()
        const elem = event.target
        setTheme(elem.getAttribute('rel'))
        setActiveTheme(elem)
      })

      // Set the menu item of the initial theme to active.
      const themeUrl = link.getAttribute('href')
      const elem = document.querySelector(`#theme-dropdown a[rel="${themeUrl}"`)
      setActiveTheme(elem)
    }
  })

  /* Load the user's current theme. */
  setTheme(window.localStorage.getItem('mizdb_theme_url'))
})()
