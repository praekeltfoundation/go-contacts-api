from setuptools import setup

setup(
    name="fake-go-contacts",
    version="0.1.8",
    url='http://github.com/praekelt/go-contacts-api',
    license='BSD',
    description="A verified fake implementation of go-contacts for testing.",
    long_description=open('README.rst', 'r').read(),
    author='Praekelt Foundation',
    author_email='dev@praekeltfoundation.org',
    py_modules=['fake_go_contacts'],
    install_requires=[],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
