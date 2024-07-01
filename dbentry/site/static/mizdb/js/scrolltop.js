// Script for the scroll back to top button:
let btn = document.getElementById("btn-back-to-top");

// When the user scrolls down 20px from the top of the document, show the button
window.onscroll = function() {scrollFunction()};

function scrollFunction() {
  if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
    btn.classList.remove("d-none");
  } else {
    btn.classList.add("d-none");
  }
}