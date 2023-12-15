/**
 * Send the user to the previous page in the session history when they click on
 * the cancel button.
 */
document.addEventListener('DOMContentLoaded', () => {
  function cancel (e) {
    e.preventDefault()
    window.history.back()
  }

  document.querySelectorAll('.cancel-link').forEach(function (elem) {
    elem.addEventListener('click', cancel)
  })
})
