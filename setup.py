from setuptools import setup, find_packages

DESCRIPTION = "Django admin app support for MongoDB fields"

LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Framework :: Django',
    'Topic :: Database :: Front-Ends',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'License :: OSI Approved :: BSD License',
    ]

setup(name='django_mongodb_extras',
    packages=find_packages(exclude=('tests', 'tests.*')),
    author='Vasily Alexeev',
    author_email='mail@v-alexeev.ru',
    url='http://v-alexeev.ru/',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    platforms=['any'],
    classifiers=CLASSIFIERS,
    install_requires=[],
    version='0.1',
)