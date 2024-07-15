document.addEventListener('DOMContentLoaded', () => {
    // Style the tables
    document.querySelectorAll('table').forEach(table => table.classList.add('table', 'table-striped', 'table-hover'))

    // Style the headings
    document.querySelectorAll('h1,h2,h3,h4,h5').forEach(heading => heading.classList.add('text-info-emphasis'))
    document.querySelectorAll('h2').forEach(heading => heading.classList.add('fs-3', 'mb-3'))
    document.querySelectorAll("h3 ~ h2").forEach(h => h.classList.add('pt-3'))
    document.querySelectorAll('h3').forEach(heading => heading.classList.add('fs-5'))
    document.querySelectorAll('h3:not(h2+h3)').forEach(heading => heading.classList.add('fs-5', 'pt-3', 'border-top'))

    // Indent the paragraphs
    document.querySelectorAll('[role=main] p').forEach(p => p.classList.add('ps-3'))
})