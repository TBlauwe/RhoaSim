from commons.messages import OrderMessage
from commons.process import ServerProcess, ClientProcess
from commons.network import Sender

from commons.utils import MessageIDGenerator


class EHoAProcess(ServerProcess):
    """
    This class defines a generic process for our project
    It Consists of a server that receives messages and handle them
    We may add a subscription store ...etc
    """
    def _custom_init(self):
        pass


class EHoAProcessWithClient(EHoAProcess):
    """
    This class describes a process with a client
    """
    def _custom_init(self):
        """
        We setup our client here
        """
        self.client = ClientProcess(self.handlers_store, logger=self._logger)


if __name__ == "__main__":
    # An example of how a RHoAProcess can be implemented
    class EHoAProcessExample(EHoAProcess):
        """
        A simple example implementing a process that receives order messages and stops after a certain number
        Each time he receives an order message, he replies telling the message number he received
        """
        def _custom_init(self):
            """
            Here we can set some attributes and do stuff before starting the process
            """
            self.message_counter = 0
            self.limit = 5

        def _set_handlers(self):
            """
            Here we set the handlers for the desired Message Types
            In this example, the handler is the :method: count
            """
            OrderMessage.set_handler(self.count)

        def count(self, message, request):
            """
            A Message handler should take two parameters :
            A message which is an instance of a subclass of :class: Message
            A request which is the socket from which the message has been received
            """
            self.message_counter += 1
            message_params = dict()
            message_params["id"] = MessageIDGenerator.get_new_message_id()
            message_params["sender"] = ()
            message_params["receiver"] = request.getpeername()
            message_params["linked_to"] = message.id
            message_params["data"] = "You sent me the message number" + str(self.message_counter)
            sender = Sender(request)
            sender.send(message_params)
            if self.message_counter >= self.limit:
                self.stop()

        def _after_exit(self):
            """
            In this method we can do the stuff that we want to de right before the process stops
            """
            print("exiting after having received " + str(self.message_counter) + " messages")
            print("process ending")

    exampleProcess = EHoAProcessExample("conf/example_process_conf.json")
    exampleProcess.run()
