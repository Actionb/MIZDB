document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('table').forEach(function(table) {
      table.classList.add('table', 'table-striped', 'table-hover');
    })
})