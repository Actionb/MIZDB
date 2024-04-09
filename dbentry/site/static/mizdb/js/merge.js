document.addEventListener('DOMContentLoaded', () => {
  const checkboxSelector = 'table input[type="checkbox"]'
  const primary = document.querySelector('#id_0-primary')

  /**
   * A checkbox input on the select primary form was checked. Store the
   * checkbox's value in a hidden form field, then uncheck all other checkbox
   * inputs.
   */
  function handleCheckboxChecked (e) {
    const cb = e.target
    // Store the last selected value in the hidden form field:
    primary.value = cb.value
    // Uncheck the other checkboxes and 'un-highlight' their parent row:
    document.querySelectorAll(checkboxSelector).forEach(other => {
      if (other !== cb) {
        other.checked = false
      }
    })
  }

  document.querySelectorAll(checkboxSelector).forEach(elem => {
    elem.addEventListener('change', handleCheckboxChecked)
  })
})
