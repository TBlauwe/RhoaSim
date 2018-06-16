"""
The process API allows you to create your own process by simply overriding base classes.
"""
from __future__ import print_function
import future
import queue
import socket
import threading
import traceback

from commons.utils import ConfigurationLoader, LoggerConfigurator, MessageIDGenerator, HandlerStore
from commons.network import ThreadPoolTCPServer, MessageWorker, Sender, Receiver


class ServerProcess(object):
    """
    A ServerProcess is an object designed to act like a server, listening an address and a port
    for incoming messages. A basic ServerProcess has a handlers_store attribute (which is in fact
    :class:`HandlerStore` object) that you can manipulate to add custom handlers. This handlers
    will be executed if the incoming message is an InformationMessage and if the `linked_to`
    field matches with the provided id at handler registration. Please see :class:`HandlerStore`
    for more information about it.

    You can start the server with the :meth:`run` method. This will internally start a
    :class:`ThreadPoolTCPServer` server on a fresh new thread. To stop the server, call the
    :meth:`stop` method.

    If you want to extend the behaviour of this class, you might be interested in overriding some
    methods:

        * :meth:`_custom_init`: this is where you should define extra attributes. This method is
            executed in the constructor, just before creating MessageWorkers.
        * :meth:`_set_handlers` : also executed in the constructor, this is where you should
            register class-level handlers for messages. This is the last method called in the
            constructor
        * :meth:`_after_exit` : this method is executed once the :meth:`stop` method has been
            executed
        * :meth:`_before_run` : this method is the first one executed in the :meth:`run`.



    """

    DEFAULT_WORKER_NUMBER = 3

    def __init__(self, conf="conf.json", *args, **kwargs):
        """
        Create a new ServerProcess with the provided configuration. If you are subclassing,
        you should *not* override this method. Use :meth:`_custom_init` and :meth:`_set_handlers`
        instead.

        :param conf: path to a configuration file
        :param args:
        :param kwargs: extra parameters passed to the thread creation. Do *not* use the target
        keyword
        """

        # Setup configuration
        self.conf = ConfigurationLoader.get_instance()
        self.conf.file = conf

        # Create the queue that will hold waiting requests
        self._queue = queue.Queue()

        # Create the server
        self._server = ThreadPoolTCPServer(
            (self.conf["server"]["address"], self.conf["server"]["port"]),
            _queue=self._queue
        )

        # Create its thread
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            *args,
            **kwargs
        )

        # Create default stuff
        # self._service_store = None
        # self._subscription_store = None
        # self._connection = None
        self.handlers_store = HandlerStore()

        # Configure logger
        self._logger = LoggerConfigurator.get_logger("ServerProcess", self.conf["logger"])

        # Customize stuff, according to what type of process it is
        self._custom_init()

        # Create workers
        self._workers = [
            MessageWorker(
                self._queue,
                self.handlers_store,
                self._logger
            ) for _ in range(self.DEFAULT_WORKER_NUMBER)
        ]

        # Configure handlers
        self._set_handlers()

    def run(self):
        """
        Start the server on its own thread. If you are subclassing, please use the
        :meth:`_before_run` instead of overriding.
        """
        # Execute custom lines
        self._before_run()

        # Start workers
        for worker in self._workers:
            worker.start()

        self._logger.info("Server: starting now ...")
        self._server_thread.start()

    def stop(self):
        """
        Stop the server. If you need to perform clean up, consider using the :meth:`_after_exit`.
        :return:
        """
        self._server.shutdown()
        self._server_thread.join()
        self._logger.info("Server: shutting down now ...")
        # Shutdown workers
        for thread in self._workers:
            thread.stop_soon()
            thread.join()

        # Execute process-specific stuff
        self._after_exit()

    def _set_handlers(self):
        """
        This method is used to register your class-level handlers. It is executed in the
        constructor (last instruction).::

            def _set_handlers(self):
                SubscriptionMessage.set_handler(self.my_handler_method)

        """
        pass

    def _custom_init(self):
        """
        Use this method if you want to use custom attributes or redefine some like _connection,
        _subscription_store or _service_store. It is executed in the constructor,
        before MessageWorkers being created.
        """
        pass

    def _after_exit(self):
        """
        This method is the last instruction executed in the stop method. you can perform some
        clean up actions here.
        """
        pass

    def _before_run(self):
        """
        This method is the first instruction called in the :meth:`run` method. You can perform
        some actions here before starting the server.
        """
        pass


class ClientProcess(object):
    """
    The ClientProcess is designed to send messages
    """

    def __init__(self, handler_store=None, logger=None):
        """
        Create a new Client. Client are able to send messages (orders or subscription) in sync
        mode. If you want to use async mode (for subscription for example), you have to use a
        server process (it's ok to use the ServerProcess one). If you do so, create the server
        and pass to the client its reference to the HandlerStore.::

            # Create a client with async support
            server = ServerProcess("path/to/conf")
            client = ClientProcess(server.handlers_store)

            # Start the server
            server.run()

            # Send messages
            rtrn = client.send_order(msg, handlers=...)

        """
        # Create a store if necessary
        self._store = HandlerStore() if handler_store is None else handler_store
        self._logger = logger

    def send_order(self, message, handlers=None):
        """
        Send a message. The destination must be provided (use the sender, receiver and the
        reply_to if necessary).

        :param message: a Message object (or one of its subclasses)
        :param handlers: a callback or or list of them
        """
        # Register callback
        if handlers is not None:
            if isinstance(handlers, (tuple, list)):
                self._store.set_handlers_for(message.id, handlers)
            else:
                self._store.set_handlers_for(message.id, [handlers])

        # Send messages
        sock = None
        result = None

        try:
            sock = socket.create_connection(tuple(message.receiver))

            # Send the message
            sender = Sender(sock, self._logger)
            sender.send(message)

            if message.to_dict().get("reply_method", "") == "immediate":
                # Create a receiver and receive the reply
                receiver = Receiver(sock, self._logger)
                result = receiver.receive()

        except Exception:
            if self._logger is not None:
                self._logger.error(traceback.format_exc())

        finally:
            if sock is not None:
                sock.close()

        return result

    def send_subscription(self, message, handlers=None):
        """
        Send a message. The destination must be provided (use the sender, receiver and the
        reply_to if necessary).

        :param message: a Message object (or one of its subclasses)
        :param handlers: a callback or or list of them
        """
        # Register callback
        if handlers is not None:
            if isinstance(handlers, (tuple, list)):
                self._store.set_handlers_for(message.id, handlers)
            else:
                self._store.set_handlers_for(message.id, [handlers])

        # Send messages
        sock = None
        result = None

        try:
            sock = socket.create_connection(tuple(message.receiver))

            # Send the message
            sender = Sender(sock, self._logger)
            sender.send(message)

            # Create a receiver and receive the reply
            receiver = Receiver(sock, self._logger)
            result = receiver.receive()

        except Exception:
            print(traceback.format_exc())

        finally:
            if sock is not None:
                sock.close()

        return result


if __name__ == '__main__':
    from commons.messages import Message

    server = ServerProcess("conf/client.json")
    client = ClientProcess(server.handlers_store)
    server.run()
    #print(client.send_subscription(Message.parse_from_dict({
    print(client.send_order(Message.parse_from_dict({
        "id": MessageIDGenerator.get_new_message_id(),
        "receiver": ("localhost", 25565),
        "sender": (),
        "reply_to": ("localhost", 25566),
        "reply_method": "delayed",
        "service": "SetFuelLevelService",
        "args": [],
        "kwargs": {"name": "rHoA", "fuel_level": 13},
        #"is_subscribing": True
    }), handlers=lambda x: print(x)))

    import time

    time.sleep(5)
    server.stop()
