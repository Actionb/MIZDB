document.addEventListener("DOMContentLoaded", () => {
  const toggleButton = document.querySelector(".watchlist-toggle-btn");
  if (toggleButton) {
    const callback = (btn, data) => {
      if (!data) return;
      if (data.on_watchlist) {
        btn.classList.remove("btn-primary");
        btn.classList.add("btn-success");
      } else {
        btn.classList.add("btn-primary");
        btn.classList.remove("btn-success");
      }
    };
    WatchlistButton.initToggleButton(toggleButton, callback);
  }
});
