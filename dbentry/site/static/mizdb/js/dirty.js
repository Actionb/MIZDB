/*
 * Issue a warning if the user tries to leave a form with unsaved changes.
 * Relies on `django-formset` setting django-field-groups to a dirty state ('dj-dirty' class),
 * and a custom event fired by the submit buttons.
*/

window.addEventListener("load", (event) => {

    /* The element class django-formset assigns to dirty inputs */
    const dirty_flag = "dj-dirty"

    const form = {
        submitted: false
    }

    /* This event is emitted by the django-formset submit buttons. */
    window.addEventListener("FormSubmitted", (event) => {
        form.submitted = true;
    });

    window.addEventListener("beforeunload", function (e) {
        if (!form.submitted && document.querySelector(`.${dirty_flag}`) !== null) {
            e.preventDefault();
            return "Es gibt nicht gespeicherte Änderungen auf dieser Seite, die verworfen werden, wenn Sie fortfahren.";
        }
    });
});