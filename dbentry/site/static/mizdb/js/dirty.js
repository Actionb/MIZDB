/*
 * Issue a warning if the user tries to leave a form with unsaved changes.
*/
window.addEventListener('load', (event) => {
  const form = document.querySelector('form.change-form')
  const DIRTY_FLAG = '_dirty'
  let submitting = false

  form.addEventListener('submit', () => { submitting = true })

  form.querySelectorAll('input,select,textarea').forEach(
    (elem) => elem.addEventListener('change', (event) => {
      elem.classList.add(DIRTY_FLAG)
    })
  )

  function isDirty () {
    return form.querySelector(`.${DIRTY_FLAG}`) !== null
  }

  window.addEventListener('beforeunload', (e) => {
    if (!submitting && isDirty()) e.preventDefault()
  })

  form.addEventListener('reset', (e) => {
    form.querySelectorAll(`.${DIRTY_FLAG}`).forEach((elem) => elem.classList.remove(DIRTY_FLAG))
  })
})
