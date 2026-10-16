import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_leap_gazebo = FindPackageShare('leap_hand_gazebo').find('leap_hand_gazebo')
    world_path = os.path.join(pkg_leap_gazebo, 'worlds', 'leap_hand_grasp.world')
    xacro_path = os.path.join(pkg_leap_gazebo, 'urdf', 'leap_hand_gazebo.xacro')

    # 1. Launch Gazebo Harmonic
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ]),
        launch_arguments=[
            ('gz_args', f'-r -v 4 {world_path}'),
        ]
    )

    # 2. Robot State Publisher
    robot_description_content = Command([
        FindExecutable(name='xacro'), ' ', xacro_path
    ])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description_content, 'use_sim_time': True}],
        output='screen'
    )

    # 3. Bridge the clock from Gazebo to ROS 2
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
        ],
        output='screen'
    )

    # 4. Delayed Spawn (Waits for Gazebo to initialize)
    delayed_spawn_hand = TimerAction(
        period=5.0,
        actions=[
            Node(
                package='ros_gz_sim',
                executable='create',
                arguments=[
                    '-name', 'leap_hand',
                    '-topic', '/robot_description',
                    '-x', '0.0', '-y', '0.0', '-z', '0.25',
                ],
                output='screen'
            )
        ]
    )

    # 5a. Spawn joint_state_broadcaster first
    delayed_spawn_jsp = TimerAction(
        period=7.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
                parameters=[{'use_sim_time': True}],
                output='screen'
            )
        ]
    )

    # 5b. Spawn index_finger_controller slightly later
    delayed_spawn_finger = TimerAction(
        period=9.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['index_finger_controller', '--controller-manager', '/controller_manager'],
                parameters=[{'use_sim_time': True}],
                output='screen'
            )
        ]
    )

    return LaunchDescription([
        ros_gz_bridge,
        gazebo,
        robot_state_publisher,
        delayed_spawn_hand,
        delayed_spawn_jsp,
        delayed_spawn_finger,
    ])
