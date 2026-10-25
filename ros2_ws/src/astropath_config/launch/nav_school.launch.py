"""Launch school_floor (optional) + Nav2 localization + navigation (no docking)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    gui = LaunchConfiguration('gui')
    start_sim = LaunchConfiguration('start_sim')
    autostart = LaunchConfiguration('autostart')

    pkg = get_package_share_directory('astropath_config')
    map_yaml = os.path.join(pkg, 'maps', 'school_floor.yaml')
    params_file = os.path.join(pkg, 'params', 'nav2_params.yaml')
    nav2_bringup = get_package_share_directory('nav2_bringup')

    school_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('astropath_sim'),
                'launch',
                'school_floor.launch.py',
            )
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'gui': gui,
            'x_pose': '-3.5',
            'y_pose': '1.70',
        }.items(),
        condition=IfCondition(start_sim),
    )

    # Split bringup: stock localization + our navigation without docking_server
    localization = TimerAction(
        period=8.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(nav2_bringup, 'launch', 'localization_launch.py')
                ),
                launch_arguments={
                    'map': map_yaml,
                    'use_sim_time': use_sim_time,
                    'params_file': params_file,
                    'autostart': autostart,
                    'use_composition': 'False',
                }.items(),
            )
        ],
    )

    navigation = TimerAction(
        period=10.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg, 'launch', 'navigation_school.launch.py')
                ),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'params_file': params_file,
                    'autostart': autostart,
                    'use_composition': 'False',
                }.items(),
            )
        ],
    )

    initial_pose = TimerAction(
        period=16.0,
        actions=[
            Node(
                package='astropath_config',
                executable='set_initial_pose',
                name='set_initial_pose',
                output='screen',
                parameters=[
                    {
                        'use_sim_time': use_sim_time,
                        'x': -3.5,
                        'y': 1.70,
                        'yaw': 0.0,
                        'frame_id': 'map',
                        'publish_count': 8,
                        'publish_period': 0.5,
                    }
                ],
            )
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument('use_sim_time', default_value='true'),
            DeclareLaunchArgument(
                'gui',
                default_value='false',
                description='Gazebo GUI client (false = headless)',
            ),
            DeclareLaunchArgument(
                'start_sim',
                default_value='true',
                description='Also launch school_floor.launch.py',
            ),
            DeclareLaunchArgument('autostart', default_value='true'),
            school_launch,
            localization,
            navigation,
            initial_pose,
        ]
    )
