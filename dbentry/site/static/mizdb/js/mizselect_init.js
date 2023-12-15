/**
 * Initialize MIZSelect elements with German texts.
 */
window.addEventListener('initMIZSelect', (e) => {
  const elem = e.target
  const germanSettings = {
    plugins: {
      add_button: { label: 'Hinzufügen' },
      changelist_button: { label: 'Änderungsliste' },
      edit_button: { title: 'Bearbeiten' }
    },
    render: {
      no_results: function (data, escape) {
        return '<div class="no-results">Keine Ergebnisse</div>'
      },
      loading_more: function (data, escape) {
        return '<div class="loading-more-results py-2 d-flex align-items-center"><div class="spinner"></div> Lade mehr Ergebnisse </div>'
      },
      no_more_results: function (data, escape) {
        return '<div class="no-more-results">Keine weiteren Ergebnisse</div>'
      }
    }
  }
  if (elem.hasAttribute('can-remove')) {
    germanSettings.plugins.remove_button = { title: 'Entfernen' }
  }
  if (elem.hasAttribute('is-multiple')) {
    germanSettings.plugins.clear_button = { title: 'Auswahl aufheben' }
  }
  e.target.initMIZSelect(germanSettings)
})
