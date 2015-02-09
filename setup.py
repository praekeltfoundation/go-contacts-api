from setuptools import setup, find_packages

setup(
    name="go-contacts",
    version="0.1.8",
    url='http://github.com/praekelt/go-contacts-api',
    license='BSD',
    description="A contacts and groups API for Vumi Go",
    long_description=open('README.rst', 'r').read(),
    author='Praekelt Foundation',
    author_email='dev@praekeltfoundation.org',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'cyclone',
        'go_api>=0.3.0',
        'vumi>=0.5.4',
        'vumi-go',
        'confmodel==0.2.0',
    ],
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
