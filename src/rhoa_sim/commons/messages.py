from commons.utils import get_final_classes


class Message(object):
    """
    This class is the root of all messages
    It comes with common attributes : (id, receiver, sender) and common methods
    """

    _handler = None

    def __init__(self, params):
        self.id = params["id"]
        self.receiver = params["receiver"]
        self.sender = params["sender"]

    def to_dict(self):
        """
        This method returns dictionary containing the attribute values of the current object
        :return:
        """
        return vars(self)

    def handle(self, *args, **kwargs):
        if self._handler is None:
            return
        return self._handler(*args, **kwargs)

    @staticmethod
    def parse_from_dict(params):
        """
        This method parses a dictionary and returns the appropriate object derived from Message
        :param params:
        :return:
        An object of a class derived from Message if the parsing was successful, None otherwise
        """
        final_classes = get_final_classes(Message)
        possible_classes = list()
        for final_class in final_classes:
            if final_class.get_required_params().issubset(params):
                possible_classes.append((
                    final_class,
                    len(final_class.get_required_params())
                ))
        possible_classes.sort(key=lambda x: x[1])
        return possible_classes[-1][0](params) if len(possible_classes) > 0 else None

    @staticmethod
    def check_parsing_determinism():
        """
        This method serves to check if the parsing is determinist
        ie : if there are branches of inheritance from the Message class which have the same
        required params
        :return: An array of sets containing conflicting branches
        """
        result = []
        final_classes = list(get_final_classes(Message))
        for i in range(len(final_classes)):
            class1 = final_classes[i]
            params1 = class1.get_required_params()
            for j in range(i+1, len(final_classes)):
                class2 = final_classes[j]
                params2 = class2.get_required_params()
                if params1.issubset(params2) and params2.issubset(params1):
                    added = False
                    for conflict in result:
                        if class1 in conflict:
                            conflict.append(class2)
                            added = True
                            break
                        if class2 in conflict:
                            added = True
                            conflict.append(class1)
                            break
                    if not added:
                        result.append([class1, class2])
        return result

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class (Message)
        :return:
        A set of required params
        """
        return {"id", "receiver", "sender"}

    @classmethod
    def get_required_params(cls):
        """
        This method retrieves the required params up from the Message class to the current class
        :return:
        A set of required params
        """
        result = cls.get_my_required_params()
        if cls != Message:
            for base_class in cls.__bases__:
                if issubclass(base_class, Message):
                    result = result.union(base_class.get_required_params())
        return result

    @classmethod
    def set_handler(cls, handler):
        cls._handler = handler

    def __repr__(self):
        return vars(self).__repr__()


class OrderMessage(Message):
    """
    This class describes a order message
    It is built on the Message class and adds a reply method attribute
    """
    def __init__(self, params):
        super(OrderMessage, self).__init__(params)
        self.reply_method = params["reply_method"]
        self.reply_to = params["reply_to"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"reply_method", "reply_to"}


class ServiceOrderMessage(OrderMessage):
    """
    This order is a service asked to a process (mainly the ContextProcess).
    It adds service, args and kwargs attributes.
    """

    def __init__(self, params):
        super(ServiceOrderMessage, self).__init__(params)
        self.service = params["service"]
        self.args = params["args"]
        self.kwargs = params["kwargs"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"service", "args", "kwargs"}


class RobotActionOrderMessage(OrderMessage):
    """
    This class describes an order message for the robot (action process)
    It is built on the OrderMessageClass and adds an action identifier attribute
    """
    def __init__(self, params):
        super(RobotActionOrderMessage, self).__init__(params)
        self.action_id = params["action_id"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"action_id"}


class MoveActionMessage(RobotActionOrderMessage):
    """
    This class describes a move order message for the robot (action process)
    It is built on the RobotActionOrderMessage and adds a target location attribute
    """
    def __init__(self, params):
        super(MoveActionMessage, self).__init__(params)
        self.target = params["target"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"target"}


class ScanActionMessage(RobotActionOrderMessage):
    """
    This class describes a scan order message for the robot (action process)
    It is built on the RobotActionOrderMessage and adds a target code attribute
    """
    def __init__(self, params):
        super(ScanActionMessage, self).__init__(params)
        self.target = params["target"]
        self.target_code = params["target_code"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"target", "target_code"}


class LearningOrderMessage(OrderMessage):
    """
    This class describes a learning order message for the learning process
    It is built ont the OrderMessage Class
    """
    def __init__(self, params):
        super(LearningOrderMessage, self).__init__(params)


class GetPathMessage(LearningOrderMessage):
    """
    This class describes get path order for the learning
    It is built on the LearningOrderMessage class and adds source and destination attributes
    """
    def __init__(self, params):
        super(GetPathMessage, self).__init__(params)
        self.source = params["source"]
        self.destination = params["destination"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"source", "destination"}


class ObservationOrderMessage(OrderMessage):
    """
    This class describes an observation order message for the observation process
    It is built ont the OrderMessage Class
    """
    def __init__(self, params):
        super(ObservationOrderMessage, self).__init__(params)


class SubscriptionMessage(Message):
    """
    This class describes a subscription message
    It is built on the Message class
    it adds an attribute for precising if it is a message for subscribing or unsubscribing
    """
    def __init__(self, params):
        super(SubscriptionMessage, self).__init__(params)
        self.is_subscribing = params["is_subscribing"]
        self.reply_to = params["reply_to"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"is_subscribing", "reply_to"}


class ContextSubscriptionMessage(SubscriptionMessage):
    """
    This class describes a service subscription to the context process
    It is built on the ContextSubscriptionMessage and adds the service, args and kwargs attributes
    """
    def __init__(self, params):
        super(ContextSubscriptionMessage, self).__init__(params)
        self.service = params["service"]
        self.args = params["args"]
        self.kwargs = params["kwargs"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"service", "args", "kwargs"}


class ObservationSubscriptionMessage(SubscriptionMessage):
    """
    This class describes a subscription to the observation process
    It is built on the SubscriptionMessage class
    """
    def __init__(self, params):
        super(ObservationSubscriptionMessage, self).__init__(params)


class CollisionSubscriptionMessage(ObservationSubscriptionMessage):
    """
    This class describes a subscription to collision events to the observation process
    It is built on the ObservationSubscriptionMessage class
    """
    def __init__(self, params):
        super(CollisionSubscriptionMessage, self).__init__(params)


class ArucoEncounterSubscriptionMessage(ObservationSubscriptionMessage):
    """
    This class describes a subscription to aruco encounter events to the observation process
    It is built on the ObservationSubscriptionMessage class and adds a target_codes attribute
    The target_codes attribute is a list of integers
    specifying the aruco codes whose encounter should be signaled to the subscriber
    if the list is empty, every code will be signaled to the subscriber
    """
    def __init__(self, params):
        super(ArucoEncounterSubscriptionMessage, self).__init__(params)
        self.target_codes = params["target_codes"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"target_codes"}


class PositionChangeSubscriptionMessage(ObservationSubscriptionMessage):
    """
    This class describes a subscription to position change events to the observation process
    It is built on the ObservationSubscriptionMessage class
    """
    def __init__(self, params):
        super(PositionChangeSubscriptionMessage, self).__init__(params)
        self.step = params["step"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"step"}


class InformationMessage(Message):
    """
    This class describes an information message
    It is built on the Message class
    """
    def __init__(self, params):
        super(InformationMessage, self).__init__(params)
        self.linked_to = params["linked_to"]
        self.data = params["data"]

    @staticmethod
    def get_my_required_params():
        """
        This static method retrieves the required params of only the current class
        :return:
        A set of required params
        """
        return {"linked_to", "data"}