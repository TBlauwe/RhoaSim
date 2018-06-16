#!/usr/bin/env python

# IMPORT
import rospy, sys, actionlib, rospkg, socket, Queue

from commons.utils                  import MessageIDGenerator 
from commons.network                import Sender
from commons.messages               import GetPathMessage
from commons.EHoAProcess            import EHoAProcessWithClient
from commons.utils          import LoggerConfigurator

from actionlib.simple_action_client import *
from math                           import radians, degrees
from tf.transformations             import quaternion_from_euler, euler_from_quaternion

from aruco_msgs.msg                 import MarkerArray, Marker
from nav_msgs.msg                   import Odometry
from rhoa_sim.msg                   import *
from move_base_msgs.msg             import MoveBaseAction, MoveBaseGoal
from geometry_msgs.msg              import Point, Quaternion

class Pose:
    """
    Handy Class to store a position with orientation (x, y, yaw)
    """
    def __init__(self, x, y, yaw):
        self.x = x
        self.y = y
        self.yaw = yaw # Degrees

class ActionHandler(EHoAProcessWithClient):

    def _custom_init(self):
        self._logger = LoggerConfigurator.get_logger("Knowledge Handler", self.conf["logger"])
        super(ActionHandler, self)._custom_init()

    def start_node(self):
        self._robot_name                = rospy.get_param('~robot_name', "toto")
        self._rate                      = float(rospy.get_param('~rate', 1.0))
        self._tolerance                 = float(rospy.get_param('~tolerance', 0.75))

        self._action_name               = rospy.get_name()
        self._position                  = None
        self._orientation               = None
        self._aruco_markers_in_sight    = []

        # create messages that are used to publish feedback/result
        self._move_feedback   = rhoa_sim.msg.DoMoveFeedback()
        self._move_result     = rhoa_sim.msg.DoMoveResult()

        self._scan_feedback   = rhoa_sim.msg.DoScanFeedback()
        self._scan_result     = rhoa_sim.msg.DoScanResult()
        # Define an action server per order
        self._as_move       = actionlib.SimpleActionServer(self._action_name+"_move", rhoa_sim.msg.DoMoveAction, execute_cb=self.execute_move_cb, auto_start = False)
        self._as_scan       = actionlib.SimpleActionServer(self._action_name+"_scan", rhoa_sim.msg.DoScanAction, execute_cb=self.execute_scan_cb, auto_start = False)

        self._as_move.start()
        self._as_scan.start()

        # Subscription
        odom_topic  = "/" + self._robot_name + "/odom"
        rospy.Subscriber(odom_topic, Odometry, self.odom_callback)

        aruco_topic = "/" + self._robot_name + "/aruco_marker_publisher/markers"
        rospy.Subscriber(aruco_topic, MarkerArray, self.aruco_callback)

        # Define a client for to send goal requests to the move_base server through a SimpleActionClient
        self._move_base_client = actionlib.SimpleActionClient("/" + self._robot_name + "/move_base", MoveBaseAction)

        # Wait for the action server to come up
        while not self._move_base_client.wait_for_server(rospy.Duration.from_sec(6.0)) and not rospy.is_shutdown():
            rospy.logwarn("Waiting for the "+ self._robot_name + "/move_base " +"move_base action server to come up")

        while not rospy.is_shutdown():
            rospy.sleep(1/self._rate)

    def execute_scan_cb(self, request):
        """
        Executed when a scan action is received. Circle around the pillar until a marker is found or has made one circle
        """
        rospy.loginfo('%s: executing scan order around %s for %s' % (self._action_name, request.location, str(request.marker_id)))

        location = self.getPath(request.location).data
        self._logger.debug(location)

        scanningPoses = self.getLocationScanningPoses(location[0])

        while scanningPoses and not request.marker_id in self._aruco_markers_in_sight:
            self._aruco_markers_in_sight = []
            pose = scanningPoses.pop()
            self._move_base_client.send_goal(self.create_nav_goal(pose), self.move_done_cb, self.move_active_cb, self.move_feedback_cb)
            self._move_base_client.wait_for_result()

        if self._aruco_markers_in_sight:
            if request.marker_id in self._aruco_markers_in_sight:
                self._scan_result.terminalState = 1 # Success
                self._scan_result.marker_id     = request.marker_id
            else:
                self._scan_result.terminalState = 0 # Fail
                self._scan_result.marker_id     = self._aruco_markers_in_sight.pop()
        else:
           self._scan_result.terminalState = 0 # Fail
           self._scan_result.marker_id     = -1

        rospy.logwarn(self._move_result)
        self._as_scan.set_succeeded(self._scan_result)

    def execute_move_cb(self, request):
        """
        Executed when a move action is received. Go to the nearest scanning pose around the location.
        """
        rospy.loginfo('%s: executing move order to %s' % (self._action_name, request.location))
        
        waypoints = self.getPath(request.location).data
        self._logger.debug(waypoints)

        for waypoint in waypoints:
            x = waypoint[0]
            y = waypoint[1]

            self._move_base_client.send_goal(self.create_nav_goal(self.getNearestScanningPose(x, y)), self.move_done_cb, self.move_active_cb, self.move_feedback_cb)

            # Waiting for the result - If feedback is needed, put the publishing loop here
            self._move_base_client.wait_for_result()
            res = self._move_base_client.get_result()

        # Handle different outcome here
        self._move_result.terminalState = 1 # Success

        rospy.logwarn(self._move_result)
        self._as_move.set_succeeded(self._move_result)
        self._aruco_markers_in_sight = []

    def getNearestScanningPose(self, _x, _y):
        """
        Return a position not far from the location and the nearest to the robot
        """
        pos_x = _x
        pos_y = _y

        yaw = 0

        delta_y = self._position.y - pos_y
        delta_x = self._position.x - pos_x

        tolerance = self._tolerance

        if abs(delta_x) > abs(delta_y):
            if delta_x < 0 :
                x = pos_x - tolerance
                y = pos_y
                yaw = 0
            else:
                x = pos_x + tolerance
                y = pos_y
                yaw = 180
        else:
            if delta_y < 0 :
                x = pos_x
                y = pos_y - tolerance
                yaw = 90
            else:
                x = pos_x
                y = pos_y + tolerance
                yaw = 270
        return Pose(x, y, yaw)

    def getLocationScanningPoses(self, location):
        """
        Return scanning positions around a location. Typically 4 for a pillar.
        """         
        x = location[0]
        y = location[1]

        tolerance = self._tolerance
        scanningPoses = []

        scanningPoses.append(Pose(x - tolerance, y, 0))
        scanningPoses.append(Pose(x, y - tolerance, 90))
        scanningPoses.append(Pose(x + tolerance, y, 180))
        scanningPoses.append(Pose(x, y + tolerance, 270))

        return scanningPoses

    def getPath(self, location):
        """
        Translate a location name with a location position by communicating with the learning process
        """
        message = GetPathMessage({
            "id": MessageIDGenerator.get_new_message_id(),
            "sender": (), 
            "receiver": (str(self.conf['learning_process']['address']), self.conf['learning_process']['port']),
            "source": "",
            "destination": location,
            "reply_method": "immediate",
            "reply_to": None})
        return self.client.send_order(message)


    def create_nav_goal(self, pose):
        """
        Return a goal for the move base action server. The goal location is x, y , 0 and orientation is 0, 0, yaw
        """
        goal = MoveBaseGoal()

        #set up the frame parameters
        goal.target_pose.header.frame_id = self._robot_name+"_tf/map"
        goal.target_pose.header.stamp = rospy.Time.now()

        # moving towards the goal*/
        goal.target_pose.pose.position = Point(pose.x, pose.y, 0)

        angle = radians(pose.yaw) # angles are expressed in radians
        quat = quaternion_from_euler(0.0, 0.0, angle) # roll, pitch, yaw
        goal.target_pose.pose.orientation = Quaternion(*quat.tolist())

        return goal

    def move_done_cb(self, terminalState, result):
        rospy.loginfo("move action done")

    def move_active_cb(self):
        rospy.loginfo("move action active")

    def move_feedback_cb(self, fb):
        return

    def odom_callback(self, data):
        """
        Function called when a Odom message is published on the topic listened
        :param data: Data contained inside the message - http://docs.ros.org/api/nav_msgs/html/msg/Odometry.html
            std_msgs/Header header
            string child_frame_id
            geometry_msgs/PoseWithCovariance pose
            geometry_msgs/TwistWithCovariance twist
        """
        position    = data.pose.pose.position
        quaternion  = (data.pose.pose.orientation.x, data.pose.pose.orientation.y, data.pose.pose.orientation.z, data.pose.pose.orientation.w)
        orientation = euler_from_quaternion(quaternion)

        self._position      = position
        self._orientation   = orientation

    def aruco_callback(self, data):
        """
        Function called when a Aruco message is published on the topic listened
        :param data:
            Header header
            uint32 id
            geometry_msgs/PoseWithCovariance pose
            float64 confidence
        """
        markers = data.markers
        for marker in markers:
            if not marker.id in self._aruco_markers_in_sight:
                self._aruco_markers_in_sight.append(marker.id)

# Main function.
if __name__ == '__main__':
    # Initialize the node and name it.
    rospy.init_node('action_handler')
    actionHandler = None
    try:
        rospack = rospkg.RosPack()
        s = rospack.get_path('rhoa_sim')
        actionHandler = ActionHandler(s + "/src/rhoa_sim/action_handler_config.json")
        actionHandler.run()
        actionHandler.start_node()

    except rospy.ROSInterruptException: 
        actionHandler.stop()
        pass
