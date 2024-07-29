/**
 * Add a button to each inline that links to the changelist of the items 
 * selected in the inline.
 */
document.addEventListener('DOMContentLoaded', () => {
  function addChangelistButton(formset) {
    const addRow = formset.querySelector('.add-row')
    const clBtn = document.createElement('button')
    clBtn.classList.add('btn', 'btn-info', 'ms-3')
    clBtn.innerText = 'Änderungsliste'
    clBtn.title = 'Änderungsliste der ausgewählten Objekte anzeigen'

    clBtn.addEventListener('click', (e) => {
      e.preventDefault()
      if (!formset.dataset.clUrl) return;
      if (formset.dataset.clField) {
        const ids = new Set()
        formset.querySelectorAll(`select[id$=${formset.dataset.clField}] ~ .ts-wrapper .item`).forEach((item) => ids.add(item.dataset.value))
        const params = new URLSearchParams({ id__in: Array.from(ids).join(',') })
        window.open(`${formset.dataset.clUrl}?${params.toString()}`)
      } else {
        window.open(formset.dataset.clUrl)
      }
    })

    addRow.appendChild(clBtn);
  }

  document.querySelectorAll('[data-cl-url]').forEach((formset) => {
    try {
      addChangelistButton(formset);
    } catch (TypeError) {
      return
    }
  })
})
