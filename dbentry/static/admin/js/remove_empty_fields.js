// Remove empty fields from GET forms (without jQuery)
// Author: Bill Erickson
// URL: http://www.billerickson.net/code/hide-empty-fields-get-form/
document.addEventListener("DOMContentLoaded", () => {
	const form = document.querySelector("#changelist-search")
	const inputs = form.querySelectorAll("input,select,button,textarea")
	form.addEventListener("submit", (e) => {
		inputs.forEach((elem) => {
			if (!elem.value) {
				elem.disabled = true
			}
		})
		return true; // ensure form still submits
	})
	// Un-disable form fields when page loads, in case they click back after submission:
	inputs.forEach((elem) => elem.disabled = false)
})