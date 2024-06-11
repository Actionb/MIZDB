document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('imageModal')
  const modalImg = document.getElementById('imageModalImage')
  const captionText = document.getElementById('imageModalCaption')

  const close = document.getElementById('imageModalClose')
  if (close) close.addEventListener('click', (e) => { modal.classList.toggle('d-none') })

  document.querySelectorAll('img.modal-image').forEach((img) => {
    img.addEventListener('click', (e) => {
      modal.classList.toggle('d-none')
      modalImg.src = img.src
      captionText.innerHTML = img.alt
    })
  })
})
