/**
 *  Remove the deleted items from the changelist selection.
 */
window.addEventListener('submit', (e) => {
  const formData = new FormData(e.target)
  const storage = new window.SelectionStorage()
  if (storage) {
    for (const [key, value] of formData) {
      if (key === '_selected-item') storage.removeItem(value)
    }
    storage.store()
  }
})

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
