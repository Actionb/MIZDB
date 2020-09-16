/*global gettext*/
(function() {
    'use strict';
    var closestElem = function(elem, tagName) {
        if (elem.nodeName === tagName.toUpperCase()) {
            return elem;
        }
        if (elem.parentNode.nodeName === 'BODY') {
            return null;
        }
        return elem.parentNode && closestElem(elem.parentNode, tagName);
    };

    window.addEventListener('load', function() {
        // Add anchor tag for Show/Hide
        var fieldsets = document.querySelectorAll('fieldset.collapse');
        for (var i = 0; i < fieldsets.length; i++) {
            var elem = fieldsets[i];
            if (elem.querySelectorAll('div.errors').length !== 0) {
                // Don't hide if fields in this fieldset have errors
                elem.classList.remove('collapsed');
            }
            var hint = document.createElement('span');
            hint.setAttribute('class', 'collapse-hint collapsible');
            if (elem.classList.contains('collapsed')) {
                hint.textContent = ' (' + gettext('Show') + ')';
            } else {
                hint.textContent = ' (' + gettext('Hide') + ')';
            }
            elem.querySelector('.collapsible').appendChild(hint);
        }
        // Create the event listener callback
        var toggleFunc = function(ev) {
            // When an element with the class collapsible is clicked,
            // hide/show the nearest parent fieldset.
            if (ev.target.matches('.collapsible')) {
                ev.preventDefault();
                ev.stopPropagation();
                var fieldset = closestElem(ev.target, 'fieldset');
                var hint = fieldset.querySelector('.collapse-hint')
                if (fieldset.classList.contains('collapsed')) {
                    hint.textContent = ' (' + gettext('Hide') + ')';
                    fieldset.classList.remove('collapsed');
                } else {
                    hint.textContent = ' (' + gettext('Show') + ')';
                    fieldset.classList.add('collapsed');
                }
            }
        };
        var inlineDivs = document.querySelectorAll('fieldset.module');
        for (i = 0; i < inlineDivs.length; i++) {
            inlineDivs[i].addEventListener('click', toggleFunc);
        }
    });
})();
