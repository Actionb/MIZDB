// Remove empty form data from search forms
document.addEventListener("DOMContentLoaded", () => {
	const form = document.querySelector(".search-form")
	if (form) {
        form.addEventListener("formdata", (e) => {
            const formData = e.formData
            for (const [name, value] of [...formData.entries()]){
                if (value === "") formData.delete(name)
            }
        })
    }
})