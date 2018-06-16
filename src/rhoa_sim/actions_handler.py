#!/usr/bin/env python

# IMPORT
import rospy, sys, actionlib, rospkg, socket

from commons.utils                  import MessageIDGenerator 
from commons.network                import Sender
from commons.EHoAProcess            import EHoAProcess 
from commons.messages               import MoveActionMessage, ScanActionMessage
from commons.utils                  import LoggerConfigurator

from collections                    import deque
from actionlib.simple_action_client import *

from rhoa_sim.msg                   import *
from rhoa_sim.srv                   import AddMoveAction, AddScanAction
from actionlib_msgs.msg             import *

class Action:
    """
    Handy Class to store the type of the action received ("Move", "Scan") and the associated request
    """
    def __init__(self, _type, message, request):
        self.type       = _type
        self.message    = message 
        self.request    = request

class ActionsHandler(EHoAProcess):
    """
    Node, whose goal is to handle multiple actions, by storing them, and sending them one by one to the action handler.
    It acts as an interface between the lower level and the others level
    """
    def _custom_init(self):
        self._logger = LoggerConfigurator.get_logger("Knowledge Handler", self.conf["logger"])
        super(ActionsHandler, self)._custom_init()

    def start_node(self):
        rospy.loginfo("Initialization")

        # Get parameters from command line or launch file
        self._robot_name    = rospy.get_param('~robot_name', "toto")
        self._rate          = float(rospy.get_param('~rate', 1.0))

        self._actions_deque = deque()
        self._current_action = None

        # Linking to action server
        self.move_action_client = actionlib.SimpleActionClient('action_handler_move', rhoa_sim.msg.DoMoveAction)
        self.scan_action_client = actionlib.SimpleActionClient('action_handler_scan', rhoa_sim.msg.DoScanAction)

        rospy.logwarn("Waiting for server")
        self.move_action_client.wait_for_server()
        self.scan_action_client.wait_for_server()

        # Main loop
        while not rospy.is_shutdown():

            # If current action is finished, let's launch the next one in queue
            if not self._current_action:
                if self._actions_deque:
                    rospy.loginfo("Sending next action")
                    self._current_action = self._actions_deque.popleft()
                    self.send_action()

            rospy.sleep(1/self._rate)
        return

    def _set_handlers(self):
        ScanActionMessage.set_handler(self.receive_scan_action)
        MoveActionMessage.set_handler(self.receive_move_action)
        return

    def send_action(self):
        """
        Send action to the action handler
        """
        res = None
        if self._current_action.type == "move":
            self.send_move(self._current_action)
        elif self._current_action.type == "scan":
            self.send_scan(self._current_action)
        
        rospy.loginfo("Action done")
        self._current_action = None
        return

    def send_move(self, action):
        """
        Send the corresponding action to the action handler
        """
        # Creates a goal to send to the action server.
        goal = rhoa_sim.msg.DoMoveGoal(location=action.message.target)

        # Sends the goal to the action server.
        self.move_action_client.send_goal(goal)

        # Waits for the server to finish performing the action.
        self.move_action_client.wait_for_result()

        res = self.move_action_client.get_result()

        """
        if self._current_action.message.reply_method == "immediate":
            Sender(self._current_action.request, logger=self._logger).send({
                "receiver": self._current_action.message.sender,
                "id": MessageIDGenerator.get_new_message_id(),
                "data": res,
                "linked_to": self._current_action.message.id
            })
        else:
            with socket.create_connection(tuple(self._current_action.message.reply_to)) as sock:
                Sender(self._current_action.request, logger=self._logger).send({
                    "receiver": self._current_action.message.sender,
                    "id": MessageIDGenerator.get_new_message_id(),
                    "data": res,
                    "linked_to": self._current_action.message.id
            })
        """

    def send_scan(self, action):
        """
        Send the corresponding action to the action handler
        """

        # Creates a goal to send to the action server.
        goal = rhoa_sim.msg.DoScanGoal(location=str(action.message.target), marker_id=int(action.message.target_code))

        # Sends the goal to the action server.
        self.scan_action_client.send_goal(goal)

        # Waits for the server to finish performing the action.
        self.scan_action_client.wait_for_result()

        res = self.scan_action_client.get_result()

        """
        if self._current_action.message.reply_method == "immediate":
            Sender(self._current_action.request).send({
                "receiver": self._current_action.message.sender,
                "id": MessageIDGenerator.get_new_message_id(),
                "data": (res.terminalState, res.marker_id),
                "linked_to": self._current_action.message.id
                }, logger=self._logger)
        else:
            with socket.create_connection(tuple(self._current_action.message.reply_to)) as sock:
                Sender(self._current_action.request).send({
                    "receiver": self._current_action.message.sender,
                    "id": MessageIDGenerator.get_new_message_id(),
                    "data": (res.terminalState, res.marker_id),
                    "linked_to": self._current_action.message.id
                }, logger=self._logger)
        """

    def receive_move_action(self, message, request):
        """
        Function called when a AddMoveAction services is requested.
        Add the action to the stack
        """
        self._logger.info("Received MoveActionMessage")
        action = Action("move", message, request)
        self._actions_deque.append(action)
        return

    def receive_scan_action(self, message, request):
        """
        Function called when a AddScanAction services is requested.
        Add the action to the stack
        """
        self._logger.info("Received ScanActionMessage")
        action = Action("scan", message, request)
        self._actions_deque.append(action)
        return

# Main function.
if __name__ == '__main__':
    # Initialize the node and name it.
    rospy.init_node('actions_handler')
    actionsHandler = None
    try:
        rospack = rospkg.RosPack()
        s = rospack.get_path('rhoa_sim')
        actionsHandler = ActionsHandler(s + "/src/rhoa_sim/actions_handler_config.json")
        actionsHandler.run()
        actionsHandler.start_node()

    except rospy.ROSInterruptException:
        actionsHandler.stop()
        pass
