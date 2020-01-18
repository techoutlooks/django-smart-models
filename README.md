# Smart Django models able to support complex use-cases with little effort.
[django-smartmodels](https://github.com/techoutlooks/django-smartmodels)

API for building multi-tenant Django applications, with the unique features :
1) Tracking, recording and reverting CRUD changes made on models
2) Shared objects management, where resources (SmartModel subclasses) belong to namespaces (org, domain, etc.),
   yet can be temporarily "owned" by users (survive user deletion). 
   Resources inherit their creator's namespace; are only visible to users belonging to the namespace.
3) Stats building using pandas, built in the smart models manager.

### Features

`django-smart-models` aims to provide the following features at the model level:
- Don't truly delete any model instance but just mark it so. Ownership of pseudo-deleted instances is transferred
  to the `sentinel` user. Overrides the default manager to filter out deleted instances.
- Track CRUD operations on model instances: owner, timestamps, statistics, etc.
- Has builtin most of the  defaults to auto-configure the Django settings.
- Swappable `Namespace` model as the visibility domain of resources (eg. org).

In addition:
- Customizable Model, CBV and RESTful (DRF) APIs implementing common patterns (mixins).
- LoopbackJS-style search supported by the REST API based on `django-rest-framework-loopback-js-filters`.
- Bulk DRF API compatible with the smart models
- Writable nested model serialization feature as a DRF-based mixin, 
  that performs out of the same data, CRUD operations on nested fields at once.
- Support for pandas right in the smart objects manager
  
### Rationale

Make smart functionality builtin in models to provide features like:
 1) Administrative boundaries eg. users create resources visible by more than one departments in an
    organization , or make contributions to several research domains, at once.
 2) Enable the soft deletion (and instant recovery) of model instances,
    continue to show the contributions made by a deleted user to some org.
 3) Tracking the usage of resources by users, etc.
 4) Rolling back user changes on models.
    
### Explanation

Two modes exist: the shared, and the private.

In the shared, users may belong to and commit resources to multiple orgs, and the resources they create don't have
any `owner` (meant for proprietorship mode below) ; but a user can create and manage resources (aka. SharedResource's)
across soft administrative boundaries (org, department, admin, etc.).In such shared mode, the created resources however
have a viewing scope (hidden or not to users), that is the meaning assumed by default for the `namespaces` field 
available in every SharedResource instance. Hence, the resource's visibility can be modified dynamically.

In private operation, a single user owns all resources (proprietorship).
Although it is originally meant for the smartmodels app to function in shared mode, where the
`namespaces` field on resources scopes their visibility, proprietorship of resources is emulated by setting
at least the following in Django settings: `SMARTMODELS_OWNER_MODEL = AUTH_USER_MODEL`.

### Requirements

    Python 3+, Django 2.2+
    djangorestframework, django-cors-headers, django-rest-framework-loopback-js-filters
    django-pandas, rest-pandas

### Setup

Install django-smartmodels inside a virtual env.

    pip3 install -U virtualenv
    virtualenv -p /usr/bin/python3 venv
    source venv/bin/activate
    pip install -e git+https://github.com/techoutlooks/django-smartmodels.git#egg=smartmodels
    
Setup rest_framework authentication scheme. 
Eg. with DOT aka [django-oauth-toolkit](https://github.com/jazzband/django-oauth-toolkit.git)',

- add DOT to DRF authentication classes in settings.py like so,

        REST_FRAMEWORK = { 
            'DEFAULT_AUTHENTICATION_CLASSES': (
                'oauth2_provider.ext.rest_framework.OAuth2Authentication', 
            ), 
        } 

- Add DOT to your urls.py

        urlpatterns = patterns('',
            url(r'^admin/', include(admin.site.urls)),
            
            # your rest_framework generic endpoints
            url(r'^', include(router.urls)),

            # DOT standard views
            url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
        )

Bootstrap the demo project

    cd demo
    python manage.py migrate
    python manage.py runserver

### TODO

- Model usage stats
- Namespace API key
- Rollback models changes
- Namespace creation allowed for staff/admin alone.


### Thanks & credits

[DOT & DRF integration](https://yeti.co/blog/oauth2-with-django-rest-framework/)
[DRF LB filter backend](https://github.com/gerasev-kirill/django-rest-framework-loopback-js-filters)
[Django Pandas](https://github.com/chrisdev/django-pandas)
[DRF Pandas](https://github.com/wq/django-rest-pandas)
