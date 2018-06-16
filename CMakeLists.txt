cmake_minimum_required(VERSION 2.8.3)
project(rhoa_sim)

find_package(catkin REQUIRED COMPONENTS
  genmsg
  actionlib
  actionlib_msgs
  roscpp
  rospy
  std_msgs
  message_generation
  move_base
  move_base_msgs
)


## Generate messages in the 'msg' folder
add_message_files(
  FILES
)

## Generate services in the 'srv' folder
# add_service_files(
#   FILES
# )

## Generate actions in the 'action' folder
add_action_files(
  FILES
  DoScan.action
  DoMove.action
  )

## Generate added messages and services with any dependencies listed here
generate_messages(
  DEPENDENCIES
  std_msgs
  actionlib_msgs
)

catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES rhoa_sim
 CATKIN_DEPENDS roscpp rospy std_msgs message_runtime
#  DEPENDS system_lib
)

include_directories(
# include
  ${catkin_INCLUDE_DIRS}
)
