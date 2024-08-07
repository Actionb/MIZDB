# Changelog

## [0.18] - 2024-07-22

### Added

- internal documentation and help pages

### Changed

- clean up templates
  - remove unused files 
  - move templates from project root into app directory
- clean up and rework action views
- remove logging for change confirmations, logins, logouts and CSRF failures
- reworked docker image: now uses alpine as base images instead of debian
- many tweaks to the `mizdb.sh` utility script and the installation script  

### Fixed

- BulkEditJahrgang now handles invalid Jahrgang values
- Ausgabe changelist is now ordered chronologically

## [0.17] - 2024-05-27

### Added

- MIZQuerySet now has an `order_by_most_used` method that orders items by how
  often they are used in a given relation. Schlagwort and Genre autocompletes
  are now ordered by how often they are used in Artikel relations if no search
  term is given.

## [0.16] - 2024-05-12

### Added

- watchlist feature for keeping user lists of model objects
- enable exporting records
- add "Monat" column to Ausgabe autocomplete

### Changed

- disallow empty URLs
- allow anonymous users to use changelist selection

## [0.15] - 2024-04-09

### Changed

- updated dependencies:
	- updated to Django 4.2.9. Notable
	  change: [set formfield_callback](https://docs.djangoproject.com/en/5.0/releases/4.2/#forms) in `MIZEditForm.Meta`
	- removed unused dependencies PyYAML, pipreqs and pylint
- admin refactor:
	- moved modules specific to admin to `dbentry/admin`
	- added `DbentryAdminConfig` app config. With the above change, Django's autodiscovery for the admin _module_
	  containing the model admin classes will no longer work (it will try to import `dbentry.admin`, which is now a
	  package). `DbentryAdminConfig` is a config that disables the autodiscovery and imports the admin module.
	- moved dal package `ac` to `dbentry/admin/autocomplete`
	- moved some static files that were not exclusively for admin to `dbentry/static/mizdb`
- changelist action refactor: make action base views compatible with non-admin views
- re-enable "View on site" link in admin user links

## [0.14] - 2024-01-29

### Changed

- changed handling of requests with invalid CSRF tokens:
	- invalid login requests by authenticated users will cause a redirect to the login page so that the user can confirm
	  the login with a refreshed token
	- invalid logout requests by authenticated users will cause a redirect to the index page with a warning message, but
	  will not log out the user
	- invalid logout requests by _unauthenticated_ users will cause a redirect to the login page like a normal logout
	- invalid add/change page requests will redirect back to the page, preserving the previous form data, for the user
	  to try again with a refreshed token

### Fixed

- fixed error occurring when logging out in two separate tabs one after another
- fixed sticky bottom container not always being placed at the very bottom of the view port

## [0.13] - 2023-12-15

### Added

- integrated site app that does not rely on django admin
- use Sass/SCSS to generate CSS and theme

## [0.12.2] - 2023-10-06

### Reverted

- reverted commit `3fc06493` from release 0.11.1:
  > initialize changelist search form with `initial` instead of `data`

  Using `data` instead of `initial` was the proper way to go for search forms after all.

## Fixed

- invalid name_field for Provenienz model. Was `geber`, should have been `geber__name`.

## [0.12.1] - 2023-09-19

### Added

- added Orte column to Band and Musiker dal autocomplete

## [0.12] - 2023-09-19

### Added

- Docker support
	- added new installation methods
	- added management utility script `mizdb.sh`
	- reworked handling of secret files and database connection parameters

### Changed

- Buch: removed Genre overview annotation to speed up changelist requests

## [0.11.1] - 2023-08-01

### Changed

- refactored MergeView to use django-formtool's SessionWizardView directly
- initialize changelist search form with `initial` instead of `data`

## [0.11] - 2023-07-27

### Added

- add overview (changelist view) queryset annotations and optimizations to models
- add mizdb-tomselect widgets and views

### Changed

- dbentry admin changelists now use overview annotations
- dal autocomplete tabular views now use the overview annotations
- refactored search form factory and view mixins to allow using different widget factories

## [0.10.1] - 2023-06-07

### Fixed

- fix incorrect tabular_autocomplete parameter for KalenderAdmin.SpielortInline

## [0.10] - 2023-05-01

### Changed

- text search: accept string of comma-separated values as search term for ids
- admin: require confirmation for drastic model object changes

### Added

- summarize utility function and action that provide summaries of model objects

### Other

- updated package versions:
	- Django updated to version 4.1
	- `django-autocomplete-light` updated to verson 3.9.4
	- use own fork of `django-tsvector-field` to make it compatible with Django 4
	- other minor package updates

- updated tox tests
- force using jQuery version 3.5.1 (due to a bug with select2 and jQuery 3.6)

## [0.9] - 2022-12-05

### Finished test rework

- rewrote and revised the MIZDB tests

### Changed

- unified 'maint' and 'bulk' package into a 'tools' package. That change includes:
	- URLs for 'maint' and 'bulk' views are now configured in tools.urls (from dbentry.urls)
	- moved templates for 'maint' and 'bulk' views into dbentry.templates.tools (from
	  MIZDB.templates.admin)

### Changed

- renamed 'crosslinks' to 'changelist_links'

### Added

- added a 'replace' action that replaces any occurrence of a (single) model object with a set of
  objects of the same model
