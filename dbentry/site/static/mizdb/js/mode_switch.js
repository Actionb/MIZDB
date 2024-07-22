/**
 * Switch between light mode and dark mode.
 */
(() => {
  const LIGHT = 'light'
  const DARK = 'dark'
  const STORAGE_KEY = 'mizdb_color_mode'

  /**
   * Return the current color mode as set by the user or by the browser.
   */
  function getMode () {
    const storedMode = window.localStorage.getItem(STORAGE_KEY)
    if (storedMode) return storedMode
    return window.matchMedia(`(prefers-color-scheme: ${LIGHT})`).matches ? LIGHT : DARK
  }

  /**
   * Set the bootstrap theme data attribute to the given mode.
   */
  function setMode (mode) {
    document.documentElement.setAttribute('data-bs-theme', mode)
  }

  /**
   * Store the given color mode.
   */
  function storeMode (mode) {
    window.localStorage.setItem(STORAGE_KEY, mode)
  }

  /**
   * Set the toggle button icon depending on the given mode.
   */
  function setIcon (mode) {
    const lightIcon = document.getElementById('light-icon')
    const darkIcon = document.getElementById('dark-icon')
    if (!(lightIcon && darkIcon)) return
    if (mode === LIGHT) {
      lightIcon.classList.remove('d-none')
      darkIcon.classList.add('d-none')
    } else {
      lightIcon.classList.add('d-none')
      darkIcon.classList.remove('d-none')
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    setIcon(getMode())
    const toggler = document.getElementById('color-mode-toggle')
    if (toggler) {
      toggler.addEventListener('click', (e) => {
        e.preventDefault()
        const mode = getMode() === LIGHT ? DARK : LIGHT // toggle the current mode
        setMode(mode)
        setIcon(mode)
        storeMode(mode)
      })
    }
  })

  setMode(getMode())
})()
