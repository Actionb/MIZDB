/**
 * Scroll the inline tab pane into view when clicking the inline tab button if
 * the bottom of the pane is not visible. Leaves an offset at the top when
 * scrolling to leave space for the row of submit buttons.
 * https://stackoverflow.com/a/49860927/9313033
 */
window.addEventListener('shown.bs.tab', event => {
  const tabButton = event.target
  const tabPane = document.querySelector(tabButton.dataset.bsTarget)

  if (tabPane.getBoundingClientRect().bottom > window.innerHeight) {
    const headerOffset = 60
    const elementPosition = tabButton.getBoundingClientRect().top
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    })
  }
})
