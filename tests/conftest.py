"""The conftest.py file serves as a means of providing fixtures for an entire directory.

Fixtures defined in a conftest.py can be used by any test in that package without needing to import them.
"""

pytest_plugins = [  # Magic list of fixtures to load
    "tests.fixtures.archivepodcast_app",
    "tests.fixtures.archivepodcast_obj",
    "tests.fixtures.aws",
    "tests.fixtures.configs",
    # "tests.fixtures.requests",
    "tests.fixtures.threads",
    "tests.fixtures.aiohttp",
]
