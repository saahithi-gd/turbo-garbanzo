#!/usr/bin/env python3
"""Launch Gazebo Harmonic school_floor world with TurtleBot3 Waffle (TB3 jazzy style)."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    tb3_launch_dir = os.path.join(
        get_package_share_directory('turtlebot3_gazebo'), 'launch'
    )
    astropath_share = get_package_share_directory('astropath_sim')
    ros_gz_sim = get_package_share_directory('ros_gz_sim')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    # North hallway center (island wall y≈0.97; room wall y≈2.5). y=1.2 was too
    # close for Nav2 inflation (0.25 m) and blocked all planners.
    x_pose = LaunchConfiguration('x_pose', default='-3.5')
    y_pose = LaunchConfiguration('y_pose', default='1.70')
    gui = LaunchConfiguration('gui', default='true')

    world = os.path.join(astropath_share, 'worlds', 'school_floor.world')

    gzserver_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': ['-r -s -v2 ', world],
            'on_exit_shutdown': 'true',
        }.items(),
    )

    # Do NOT set on_exit_shutdown for the GUI client: a gz client segfault
    # (seen on this hybrid GPU host) must not tear down the sim server.
    gzclient_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-g -v2 ', 'on_exit_shutdown': 'false'}.items(),
        condition=IfCondition(gui),
    )

    robot_state_publisher_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_launch_dir, 'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    spawn_turtlebot_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_launch_dir, 'spawn_turtlebot3.launch.py')
        ),
        launch_arguments={'x_pose': x_pose, 'y_pose': y_pose}.items(),
    )

    # Gazebo must find TB3 meshes and astropath_sim models (school_floor, aruco_*)
    set_tb3_resource = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        os.path.join(get_package_share_directory('turtlebot3_gazebo'), 'models'),
    )
    set_astropath_resource = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        os.path.join(astropath_share, 'models'),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'x_pose', default_value='-3.5',
            description='Spawn X in open hallway near door 0',
        ),
        DeclareLaunchArgument(
            'y_pose', default_value='1.70',
            description='Spawn Y in open hallway near door 0 (north of island)',
        ),
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='Start gz client (-g); set false for headless',
        ),
        set_tb3_resource,
        set_astropath_resource,
        gzserver_cmd,
        gzclient_cmd,
        robot_state_publisher_cmd,
        spawn_turtlebot_cmd,
    ])
