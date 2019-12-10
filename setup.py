import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="smartmodels",
    version="0.1.0",
    author="Edouard Carvalho",
    author_email="ceduth@techoutlooks.com",
    description="Factory for smart features built in Django models (models, managers, admin, pandas, REST APIs, etc.) "
                "Eg. object ownership: user-creator and namespaces (orgs, domains, ...), CRUD actions tracking, stats.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/techoutlooks/django-smartmodels",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    install_requires=[
        "Django>=2.2",
        "django-cors-headers>=3.2",
        "djangorestframework>=3.10",
        "django-rest-framework-loopback-js-filters>=1.1.4",
        "numpy>=1.17.4",
        "django-pandas>=0.6.1",
        "rest-pandas>1.1.0"
    ]
)
