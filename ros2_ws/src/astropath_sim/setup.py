import os
from glob import glob

from setuptools import setup

package_name = 'astropath_sim'


def package_files(base: str, patterns: list[str]) -> list[tuple[str, list[str]]]:
    """Install matched files under share/<package>/<relpath>."""
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
        (f'share/{package_name}/worlds', glob('worlds/*')),
        (f'share/{package_name}/textures', glob('textures/*')),
        *package_files(
            'models',
            [
                '**/*.sdf',
                '**/*.config',
                '**/*.png',
                '**/*.jpg',
                '**/*.material',
                '**/*.obj',
                '**/*.mtl',
                '**/*.dae',
            ],
        ),
        (f'share/{package_name}/scripts', glob('scripts/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Astropath',
    maintainer_email='sidg@astropath.local',
    description='Astropath school_floor Gazebo world for TurtleBot3 Waffle',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'verify_aruco_camera = astropath_sim.verify_aruco_camera:main',
        ],
    },
)
