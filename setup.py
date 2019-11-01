import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="smart_models",
    version="0.1.0",
    author="Edouard Carvalho",
    author_email="ceduth@techoutlooks.com",
    description="Models with multiple namespaces (eg. users, orgs, etc), with CRUD operations tracking",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/techoutlooks/django-smart-models",
    packages=setuptools.find_packages(),
    python_requires='>=2.7',
    install_requires=[
        "Django>=1.11",
        "djangorestframework>=3.9.4",
        "django-oauth-toolkit>=1.1.2",
    ]
)
