"""Launch school_floor (optional) + slam_toolbox online async."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    gui = LaunchConfiguration('gui')
    start_sim = LaunchConfiguration('start_sim')
    start_explorer = LaunchConfiguration('start_explorer')

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
        }.items(),
        condition=IfCondition(start_sim),
    )

    slam_params = os.path.join(
        get_package_share_directory('astropath_config'),
        'params',
        'mapper_params_online_async.yaml',
    )
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('slam_toolbox'),
                'launch',
                'online_async_launch.py',
            )
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'slam_params_file': slam_params,
        }.items(),
    )

    # Delay explorer so gz + bridges + slam are up
    explorer = TimerAction(
        period=12.0,
        actions=[
            Node(
                package='astropath_config',
                executable='school_explorer',
                name='school_explorer',
                output='screen',
                parameters=[{'use_sim_time': use_sim_time}],
                condition=IfCondition(start_explorer),
            )
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument('use_sim_time', default_value='true'),
            DeclareLaunchArgument(
                'gui',
                default_value='false',
                description='Gazebo GUI client (false = headless server)',
            ),
            DeclareLaunchArgument(
                'start_sim',
                default_value='true',
                description='Also launch school_floor.launch.py',
            ),
            DeclareLaunchArgument(
                'start_explorer',
                default_value='false',
                description='Auto-start school_explorer after delay',
            ),
            school_launch,
            slam_launch,
            explorer,
        ]
    )
