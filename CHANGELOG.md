# Changelog

## [0.25.0] - 2025-06-27

### Added

- added possibility to select which fields to export  

### Changed

- made Audio.plattennummer queries case-insensitive
- reworked docker setup:
    - install process now downloads docker-compose files instead of the entire repository
    - docker-compose now uses a MIZDB image from the GitHub container registry instead of building an image locally
    - settings are now read from the environment file instead of many different files like `.secrets` or `settings.py`.
      This allows using just a single `docker-compose.env` file to manage settings.
    - added GitHub workflow that builds and publishes an image when a new release tag is pushed
- added background to favicon
- updated django-import-export to version 4.3.8

## [0.24.0] - 2025-06-12

### Added

- show warning message in MIZSelect dropdown when trying to create duplicates of objects with unique constraints

### Fixed

- fixed Erscheinungsdatum getting reset to default when updating an Ausgabe instance due to the DateInput not accepting
  the initial value

## [0.23.0] 2025-06-11

### Added

- added simple favicon and logo

### Changed

- updated project dependencies
- now includes Python 3.13 in tests and CI
- tweaked help docs

### Fixed

- searchbar search: search term is now properly escaped before being attached to the result link
- full text search now includes items that merely contain the search term
- fixed change history messages including problematic `None` values in the list of changed fields if a form field has no
  explicit label set

## [0.22.1] - 2025-05-28

### Fixed

- fixed wsgi.py settings `DJANGO_SETTINGS_MODULE` incorrectly

## [0.22.0] - 2025-05-27

### Added

- Audio changelist: add search form field for 'Plattennummer'
- include 'Genres' in Band and Musiker autocomplete dropdown table
- send email to admins upon server errors
- add feedback page: let users mail feedback to the admins

### Changed

- only add data from changelist filters to form initial data if the view is an 'add' view. This stops data from the
  search form sneaking into form data on edit views.

## [0.21.0] - 2025-05-21

### Added

- non-admin autocomplete create function for Person, Band and Musiker now automatically add a numeric suffix when the
  newly created object is an exact duplicate of an already existing object. For example: assuming that a Band "The
  Beatles" already exists, when the user creates a new Band with the same name via the create autocomplete function, the
  new Band will have the name "The Beatles (2)".
- added docker compose file for running a (development) test server
- mkdocs config using the Materials theme for the online help

### Changed

- changed how the help button works:
    - the primary 'help button' now sends the user to the online help pages
    - a dropdown menu includes a button for the offline help pages
    - help button URLs should now always send the user to the help page that corresponds with the current list or edit
      view
- hide add buttons on the changelists if the user does not have 'add' permission

### Fixed

- re-added changelist links on view-only pages
- fix Brochure-type list views using the wrong ordering field for the 'jahr_list' list display field
- fix string_list annotations not including values that do not satisfy set filters

## [0.20.0] - 2024-09-20

### Changed

- changed export permission requirements:
    - exporting a limited set of records only requires 'view' permission
    - exporting all records of a model requires superuser permission
- watchlist: include magazin name in Ausgabe watchlist items
- moved docs and test requirements into their own requirement files
- move dev configs (pytest, ruff, etc.) into pyproject.toml

### Fixed

- fixed text search with search terms that contain forward slashes (#14)
- watchlist: include Magazin name in the text representation of Ausgabe watchlist items
- fixed URLs for the duplicates search

## [0.19.1] - 2024-09-03

### Fixed

- quick fix for Broschüre pages being inaccessible due to an UnicodeEncodeError when served under Apache. The
  anticipated template file for the Broschüre help page contains an Umlaut, which creates problems when checking for the
  existence of that template. To fix, the help link now always links to the help index instead of model-specific help
  pages depending on what view the user is on.

## [0.19.0] - 2024-08-19

### Added

- added date picker for Ausgabe Erscheinungsdatum field
- added button to inlines that sends the user to the changelist of the items selected in the inline forms
- added 'Band' search field to Musiker changelist
- added 'Ergebnisse exportieren' button to changelist that exports the current search results

### Changed

- made some columns in the Ausgabe changelist unsortable. Columns like the one for the "Ausgabenummer" contain mostly
  numerical values, but they actually are text and thus order lexicographically if sorted against, which ends up looking
  wrong and confusing to the user.
- store secrets in a single yaml file instead of multiple files in a `.secret` directory
- reworked docker setup:
    - volume source directories are read from environment (`DATA_DIR`, `LOG_DIR`, `BACKUP_DIR`)
    - volume source directories default to `/var/lib/mizdb/` and `/var/log/mizdb`
    - $UID and $GID are no longer used to define the container user: containers are run as root and the webserver is
      run as apache
- add scripts: uninstall script, backup script and get-mizdb script
- moved database scripts into `scripts` directory
- changed update process:
    - update now checks against GitHub API
    - rebuilds containers after pulling the update
    - applies migrations if necessary

### Fixed

- delete view: non-admin users were required to have "delete" permissions for auto created M2M tables.
- Genre edit page now includes links to the changelists of related Brochure models (Broschüre, Programmheft,
  Warenkatalog)

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
