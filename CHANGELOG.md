# Changelog

## [Unreleased]

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