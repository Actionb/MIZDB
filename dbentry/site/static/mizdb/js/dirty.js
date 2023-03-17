/*
 * Issue a warning if the user tries to leave a form with unsaved changes.
 * Relies on django-formset setting django-field-groups to a dirty state ('dj-dirty' class).
*/

var isDirty = function() {
    return document.querySelector(".dj-dirty") !== null
 }

window.onload = function() {

    const Dirty = {
    /* FIXME: this doesn't work on django-formset submit buttons because they are outside the form element? */
        is_submitting: false
    }

    window.addEventListener("submit", (event) => {
        Dirty.is_submitting = true;
    });
    window.addEventListener("beforeunload", function (e) {
        if (isDirty() && !Dirty.is_submitting) {
            e.preventDefault();
            return "HEYYYYYYYY"; /* TODO: add message -- also why is only a default message and not this custom message displayed? */
        }
    });
};