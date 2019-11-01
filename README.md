# Smart Django Models


[django-smart-models](https://github.com/techoutlooks/django-smart-models)

API for building multi-tenant Django applications, with the unique features :
1) Tracking, recording and reverting CRUD changes made on models
2) Shared objects management, where resources (Django models) belong to namespaces  (org, domain, etc.),
   instead of users. The resources are only visible to the users added to a namespace

### Features

django-smart-models aims to provide the following features readily available :
- Customizable Model, CBV and RESTful APIs as a single codebase,
- Don't truly delete any model instance but just mark it so. Ownership of pseudo-deleted instances is transferred
  to the `sentinel` user. Overrides the default manager to filter out deleted instances.
- Track CRUD operations on model instances: owner, timestamps, statistics, etc.
- Has builtin most of the  defaults to auto-configure the Django settings.
- Swappable `Namespace` model.

### Rationale

Make smart functionality builtin in models to provide features like:
 1) Administrative boundaries eg. users create resources visible by more than one departments in an
    organization , or make contributions to several research domains, at once.
 2) Enable the soft deletion (and instant recovery) of model instances,
    continue to show the contributions made by a deleted user to some org.
 3) Tracking the usage of resources by users, etc.
    
### Explanation

Two modes exist: the shared, and the private.

In the shared, users may belong to and commit resources to multiple orgs, and the resources they create don't have
any `owner` (meant for proprietorship mode below) ; but a user can create and manage resources (aka. SharedResource's)
across soft administrative boundaries (org, department, admin, etc.).In such shared mode, the created resources however
have a viewing scope (hidden or not to users), that is the meaning assumed by default for the `namespaces` field 
available in every SharedResource instance. Hence, the resource's visibility can be modified dynamically.

In private operation, a single user owns all resources (proprietorship).
Although it is originally meant for the smart_models app to function in shared mode, where the
`namespaces` field on resources scopes their visibility, proprietorship of resources is emulated by setting
at least the following in Django settings: `SMART_MODELS_OWNER_MODEL = AUTH_USER_MODEL`.

### Install

```bash
pip install -e git+https://github.com/techoutlooks/django-smart-models#egg=smart_models
```

### TODO
- Model usage stats
- Namespace API key
- Rollback value changes in models
