import os
from glob import glob

from setuptools import setup

package_name = 'astropath_config'


def package_files(base: str, patterns: list[str]) -> list[tuple[str, list[str]]]:
    entries: list[tuple[str, list[str]]] = []
    for pattern in patterns:
        for path in glob(os.path.join(base, pattern), recursive=True):
            if not os.path.isfile(path):
                continue
            install_dir = os.path.join('share', package_name, os.path.dirname(path))
            entries.append((install_dir, [path]))
    return entries


setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name] if os.path.isdir(package_name) else [],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.py')),
        *package_files('maps', ['**/*']),
        *package_files('params', ['**/*']),
        *package_files('rviz', ['**/*']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Astropath',
    maintainer_email='sidg@astropath.local',
    description='Astropath maps, Nav2 params, and mapping/navigation helpers',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'school_explorer = astropath_config.school_explorer:main',
            'set_initial_pose = astropath_config.set_initial_pose:main',
            'nav_goals = astropath_config.nav_goals:main',
            'simple_route = astropath_config.simple_route:main',
        ],
    },
)
