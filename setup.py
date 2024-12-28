from setuptools import setup, find_namespace_packages

setup(
    name="jtbd",
    version="0.1.0",
    packages=find_namespace_packages(include=['jtbd*', 'todo*', 'buildit*']),
    include_package_data=True,
    install_requires=[
        "textual>=0.40.0",
        "setuptools>=60.0.0",
    ],
    entry_points={
        'console_scripts': [
            'todo=todo.__main__:main',
            'buildit=buildit.__main__:main',
        ],
    },
    author="olayeku",
    description="Just Track By Doing - A collection of task tracking tools",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    keywords="todo, project management, task tracking",
    url="",  # Add your repository URL here
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
) 