# Admin 'decoupling'

Code that should not be coupled to admin stuff:

- queryset annotations for changelists (also need those annotations for non-admin ListViews)

- dbentry.ac.views.ACAusgabe relies on admin annotations (see above)

- some dbentry.utils.admin functions are not specific to admin (link functions, LogEntry functions)

- dbentry.search.form
  - SearchForm relies on admin static files such as form.css
  - SearchFormFactory mentions ModelAdmin.lookup_allowed
  
- admin actions generally
  - action views rely on model_admin for:
    - setting `self.opts` from `model_admin.opts`
    - adding admin media to the context
    - urls for `get_objects_list` (using `model_admin.admin_site.name`)
    - sending user messages from checks (via `view.model_admin.message_user`)
    - MergeView: to get the changelist instance `self.model_admin.get_changelist_instance`
    - ChangeBestand:
      - `create_log_entries`
      - the formsets of the view are taken from `self.model_admin.get_inline_formsets`
    - `delete_selected` action is all django admin

- static files
  - js
    - merge.js
    - remove_empty_fields.js
    - select2_tabular (outside of admin: maybe TomSelect?)
    - googlebtn.js
    - collapse.js (outside of admin: should be done by bootstrap anyway)
  - css
    - base_custom requires admin/css/base.css
  - many forms (and other Media using stuff) use admin static files 
  
- admin site stuff:
  - need something similar for non-admin anyway, so maybe use mixins
  - this includes tools.decorators.register_tool
  - login, log out and password change are handled by admin.AdminSite


## Important stuff that would need to replicated from Django admin

- login, log out and password change (<-- contrib.auth views!)
- index page
- permission checks (including redirect to login screen?)
- changelists
- never_cache and csrf_protect (like `site.admin_view`)
- delete view
- related widget wrapper
- template tags (f.ex. `admin_urls` providing the tag `admin_urlname`)

# Other TODOs:

- use bootstrap modal for login (and password reset)
- add dark mode
- implement a theme switcher
- IMPORTANT: richtexteditor content spills out below?!