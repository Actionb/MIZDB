# Changelog

## [unreleased]

### Changed

- refactored MergeView to use django-formtool's SessionWizardView directly

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
