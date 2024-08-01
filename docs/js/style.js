document.addEventListener('DOMContentLoaded', () => {
    const help_content = document.querySelector('#help_content')
    if (!help_content) return
    
    // Style the tables
    help_content.querySelectorAll('table').forEach(table => table.classList.add('table', 'table-striped', 'table-hover'))

    // Style the headings
    help_content.querySelectorAll('h1,h2,h3,h4,h5').forEach(heading => heading.classList.add('text-info-emphasis'))
    help_content.querySelectorAll('h2').forEach(heading => heading.classList.add('fs-3', 'mb-3'))
    help_content.querySelectorAll('h3 ~ h2').forEach(h => h.classList.add('pt-3'))
    help_content.querySelectorAll('h3').forEach(heading => heading.classList.add('fs-5'))
    help_content.querySelectorAll('h3:not(h2+h3)').forEach(heading => heading.classList.add('fs-5', 'pt-3', 'border-top'))

    // Indent the paragraphs
    help_content.querySelectorAll('[role=main] p').forEach(p => p.classList.add('ps-3'))

    // Hide the toc if it only contains one item
    const toc = help_content.querySelector('.bs-sidebar')
    if (toc && toc.querySelectorAll('.nav-item').length == 1) {
        toc.classList.add('d-none')
    }

    help_content.querySelector('[role=main]').classList.add('card', 'py-2')
})