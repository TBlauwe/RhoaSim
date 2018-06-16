#!/usr/bin/env python

import rospy, rospkg, logging

from commons.EHoAProcess    import EHoAProcessWithClient
from commons.messages       import Message
from commons.utils          import MessageIDGenerator 
from commons.utils          import LoggerConfigurator

from math                   import radians, degrees
from tf.transformations     import quaternion_from_euler, euler_from_quaternion

from std_msgs.msg           import Header
from nav_msgs.msg           import Odometry, OccupancyGrid
from aruco_msgs.msg         import MarkerArray, Marker
from geometry_msgs.msg      import PoseWithCovarianceStamped, PoseWithCovariance , Pose, Point, Quaternion, TwistWithCovariance, Twist, Vector3

class KnowledgeHandler(EHoAProcessWithClient):
    """
    Retrieve information send on different topics, and send them to the Contex Process
    """

    def _custom_init(self):
        self._logger = LoggerConfigurator.get_logger("Knowledge Handler", self.conf["logger"])
        super(KnowledgeHandler, self)._custom_init()

    def start_node(self):

        self._logger.info("Starting node")

        self._robot_name    = rospy.get_param('~robot_name', "rHoa")
        self._rate          = float(rospy.get_param('~rate', 5.0))
        self._action_name   = rospy.get_name()
        self._send_message  = rospy.get_name() 

        # Subscription
        aruco_topic = "/" + self._robot_name + "/aruco_marker_publisher/markers"
        self.aruco  = None

        odom_topic  = "/" + self._robot_name + "/odom"
        self.odom   = None

        rospy.Subscriber(aruco_topic, MarkerArray, self.aruco_callback)
        rospy.Subscriber(odom_topic, Odometry, self.odom_callback)

        # Spin to avoid exiting
        while not rospy.is_shutdown():
            self.send_data()
            rospy.sleep(self._rate)

    def send_data(self):
        """
        Send data to the context process
        For now:
            Aruco :     (x, y, aruco) - if an aruco code is in sight
            Position :  (x, y, z)

        """
        # Send aruco marker if one
        if self.odom:
            position = self.odom.pose.pose.position

            if self.aruco:
                self._logger.info("Sending aruco")
                # Create a messages
                msg = Message.parse_from_dict({
                    "id": MessageIDGenerator.get_new_message_id(),
                    "sender": (),
                    "receiver": (str(self.conf['context_process']['address']), self.conf['context_process']['port']), 
                    "service": "SetArucoService",
                    "args": [],
                    "kwargs": {"x": position.x, "y": position.y, "aruco": self.aruco},
                    "reply_method": "immediate",
                    "reply_to": None
                })
                self.client.send_order(msg)
                self.aruco = None

            self._logger.info("Sending position")
            msg = Message.parse_from_dict({
                "id": MessageIDGenerator.get_new_message_id(),
                "sender": (),
                "receiver": (str(self.conf['context_process']['address']), self.conf['context_process']['port']), 
                "service": "SetRobotPosition",
                "args": [],
                "kwargs": {"name": "rHoA", "x": position.x, "y": position.y, "z": position.z},
                "reply_method": "immediate",
                "reply_to": None
            })
            self._logger.debug(msg)
            self.client.send_order(msg)
            self.odom = None


    def aruco_callback(self, data):
        """
        Function called when a Aruco message is published on the topic listened
       
        :param data:

            * Header header
            * aruco_msgs/Marker[] markers

            Marker :

            * Header header
            * uint32 id
            * geometry_msgs/PoseWithCovariance pose
            * float64 confidence

        """
        markers = data.markers
        for marker in markers:
            self.aruco = marker.id


    def odom_callback(self, data):
        """
        Function called when a Odom message is published on the topic listened
        
        :param data:

            * std_msgs/Header header
            * string child_frame_id
            * geometry_msgs/PoseWithCovariance pose
            * geometry_msgs/TwistWithCovariance twist

        """
        self.odom = data

        pose  = data.pose
        twist = data.twist

        position    = data.pose.pose.position
        quaternion  = (data.pose.pose.orientation.x, data.pose.pose.orientation.y, data.pose.pose.orientation.z, data.pose.pose.orientation.w)
        orientation = euler_from_quaternion(quaternion)

        linear  = twist.twist.linear
        angular = twist.twist.angular

        rospy.loginfo("... position         : " + str(position))
        rospy.loginfo("... orientation      : " + str(orientation))

        rospy.loginfo("... linear velocity  : " + str(linear))
        rospy.loginfo("... angular velocity : " + str(angular))

# Main function.
if __name__ == '__main__':
    # Initialize the node and name it.
    rospy.init_node('knowledge_handler')
    knowledgeHandler = None
    try:
        rospack = rospkg.RosPack()
        s = rospack.get_path('rhoa_sim')
        knowledgeHandler = KnowledgeHandler(s + "/src/rhoa_sim/knowledge_handler_config.json")
        knowledgeHandler.run()
        knowledgeHandler.start_node()
    except rospy.ROSInterruptException:
        knowledgeHandler.stop()
        pass
