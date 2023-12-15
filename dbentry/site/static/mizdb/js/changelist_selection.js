/**
 * Manage selection of items from changelists.
 */
(function () {
  const defaults = {
    selectItemCheckbox: 'input.selection-cb',
    selectAllCheckbox: '#select-all-cb',
    selectionPanel: '#changelist-selection-container',
    itemsContainer: '#selected-items-container',
    selectionTemplate: '#selected-item-template',
    counterElement: '#selection-count',
    clearButton: '#clear-selection',
    storageKey: 'mizdb_selection'
  }

  /**
   * Interface for storing and loading changelist selections for a model.
   *
   * Use load() to load a selection for the current model from localStorage.
   *
   * Add or remove items with addItem(id) and removeItem(id), respectively.
   * Use clearAll() to remove all items for the current model.
   *
   * Use store() to update the selection for this model in localStorage with
   * the current selection (or delete it if no selection).
   */
  class SelectionStorage {
    constructor (model, storageKey) {
      this.model = model || document.body.dataset.model
      this.storageKey = storageKey || defaults.storageKey

      // Restore selections from local storage:
      this.load()
    }

    /**
     * Retrieve a selection from local storage.
     */
    load () {
      this.selected = []
      this.linkMapping = {}
      if (window.localStorage.getItem(this.storageKey)) {
        const fromStorage = JSON.parse(window.localStorage.getItem(this.storageKey))
        if (fromStorage[this.model]) {
          this.selected = fromStorage[this.model].selected || []
          this.linkMapping = fromStorage[this.model].linkMapping || {}
        }
      }
    }

    /**
     * Add the current selection to local storage.
     */
    store () {
      const stored = window.localStorage.getItem(this.storageKey)
      const data = stored ? JSON.parse(stored) : {}
      if (this.selected.length) {
        data[this.model] = { selected: this.selected, linkMapping: this.linkMapping }
      } else {
        delete data[this.model]
      }
      window.localStorage.setItem(this.storageKey, JSON.stringify(data))
    }

    /**
     * Add an item to the selection.
     *
     * @param {number} id The object id of the item to add.
     * @param {object} link The href, title and text for the link to the item
     */
    addItem (id, link) {
      this.selected.push(id)
      this.linkMapping[id] = link
    }

    /**
     * Remove the item with the given id from the selection.
     *
     * @param {number} id The object id of the item to remove
     */
    removeItem (id) {
      this.selected.splice(this.selected.indexOf(id), 1)
      delete this.linkMapping.id
    }

    /**
     * Remove all items from the selection.
     */
    clearAll () {
      this.selected = []
      this.linkMapping = {}
    }
  }

  /**
   * Manager for selections of items in changelists.
   *
   * Sets up click handlers and renders the items of the selection container.
   */
  class ChangelistSelection {
    constructor (storage, userOptions) {
      this.options = Object.assign({}, defaults, userOptions)
      this.selectionPanel = document.querySelector(this.options.selectionPanel)
      this.itemsContainer = document.querySelector(this.options.itemsContainer)
      this.itemTemplate = document.querySelector(this.options.selectionTemplate)
      this.counterElement = document.querySelector(this.options.counterElement)
      this.allSelectionCheckbox = document.querySelector(this.options.selectAllCheckbox)

      this.storage = storage || new SelectionStorage()
      this.load()

      this.setupClickHandlers(this)
      // Reload storage and refresh the container if the page was loaded from cache.
      window.addEventListener('pageshow', (e) => {
        if (e.persisted) {
          this.load()
          this.render()
        }
      })
    }

    /**
     * Setup click event handlers for the checkboxes and buttons.
     *
     * @param {ChangelistSelection} selection the current ChangelistSelection instance
     */
    setupClickHandlers (selection) {
      // A selection checkbox has been clicked.
      function selectionClickHandler (e) {
        const cb = e.target
        const row = cb.closest('tr')
        if (cb.checked) {
          selection.addRow(row)
        } else {
          selection.removeRow(row)
        }
        selection.update()
      }

      // The "select all" checkbox has been clicked.
      function allSelectionClickHandler (e) {
        const all = e.target
        document.querySelectorAll(selection.options.selectItemCheckbox).forEach((cb) => {
          const row = cb.closest('tr')
          if (all.checked) {
            // Select all rows.
            if (!(cb.checked)) selection.addRow(row)
            cb.checked = true
          } else {
            // Un-select all rows.
            if (cb.checked) selection.removeRow(row)
            cb.checked = false
          }
        })
        selection.update()
      }

      // The "clear all" button has been clicked.
      function clearButtonClickHandler (e) {
        e.preventDefault()
        selection.clearAll()
        selection.update()
      }

      if (this.allSelectionCheckbox) this.allSelectionCheckbox.addEventListener('click', allSelectionClickHandler)
      document.querySelectorAll(this.options.selectItemCheckbox).forEach((cb) => cb.addEventListener('click', selectionClickHandler))
      document.querySelector(this.options.clearButton).addEventListener('click', clearButtonClickHandler)
    }

    /**
     * Load the selection from storage and check any selected checkboxes.
     */
    load () {
      this.storage.load()
      document.querySelectorAll(this.options.selectItemCheckbox).forEach((cb) => { cb.checked = false })
      this.storage.selected.forEach((id) => {
        const cb = this.getSelectionCheckbox(id)
        if (cb) cb.checked = true
      })
    }

    /**
     * Update the state; save the selected items to storage, render the
     * selection and update the "select all" checkbox.
     */
    update () {
      this.storage.store()
      this.render()
    }

    /**
     * Render the container with the selected items.
     */
    render () {
      const selected = this.storage.selected
      const linkMapping = this.storage.linkMapping
      const count = selected.length
      if (count > 0) {
        this.selectionPanel.classList.remove('d-none')
      } else {
        this.selectionPanel.classList.add('d-none')
      }
      this.itemsContainer.innerHTML = ''
      selected.forEach((id) => {
        const clone = this.itemTemplate.content.cloneNode(true)
        clone.querySelector('input').setAttribute('value', id)

        const link = clone.querySelector('.item-container a')
        link.href = linkMapping[id].href
        link.innerText = linkMapping[id].text
        link.title = linkMapping[id].title

        clone.querySelector('a.remove-selection').addEventListener('click', (e) => {
          e.preventDefault()
          this.storage.removeItem(id)
          const cb = this.getSelectionCheckbox(id)
          if (cb) cb.checked = false
          this.update()
        })
        this.itemsContainer.appendChild(clone)
      })
      this.counterElement.innerText = count
      if (this.allSelectionCheckbox) this.allSelectionCheckbox.checked = this.allChecked()
    }

    /**
     * Return the selection checkbox for the given object id.
     *
     * @param {number} id the object id
     */
    getSelectionCheckbox (id) {
      return document.querySelector(`${this.options.selectItemCheckbox}[value="${id}"]`)
    }

    /**
     * Return the id of the object in the given row.
     *
     * @param {HTMLTableRowElement} row a changelist table row
     */
    getRowId (row) {
      return row.querySelector(this.options.selectItemCheckbox).value
    }

    /**
     * Add the given table row to the selection.
     *
     * @param {HTMLTableRowElement} row the changelist table row that was selected
     */
    addRow (row) {
      // Create a text representation of the row by concatenating the texts of
      // the change links in the row. If the row does not contain any links,
      // use the text of the first non-empty table data element.
      let textElements = row.querySelectorAll('a.change-link')
      if (!textElements.length) {
        for (const elem of row.querySelectorAll('td:not(:first-child)')) {
          if (elem.innerText !== '' && elem.innerText !== '-') {
            textElements = [elem]
            break
          }
        }
      }
      const id = this.getRowId(row)
      const href = textElements[0].href || '#'
      let text = [...textElements].map((elem) => elem.innerText).join(' ')
      const title = text
      if (text.length > 66) {
        text = text.substring(0, 60) + ' [...]'
      }
      this.storage.addItem(id, { href, text, title })
    }

    /**
     * Remove the given table row from the selection.
     *
     * @param {HTMLTableRowElement} row the changelist table row that was un-selected
     */
    removeRow (row) {
      const id = this.getRowId(row)
      this.storage.removeItem(id)
      const cb = this.getSelectionCheckbox(id)
      if (cb) cb.checked = false
    }

    /**
     * Remove all items from the selection.
     */
    clearAll () {
      this.storage.clearAll()
      document.querySelectorAll(this.options.selectItemCheckbox).forEach((cb) => { cb.checked = false })
    }

    /**
     * Return whether all selection checkboxes are checked. Return false if
     * there are no checkboxes.
     */
    allChecked () {
      return document.querySelectorAll(this.options.selectItemCheckbox) && !document.querySelectorAll(this.options.selectItemCheckbox + ':not(:checked)').length
    }
  }

  window.SelectionStorage = SelectionStorage
  window.ChangelistSelection = ChangelistSelection
})()
