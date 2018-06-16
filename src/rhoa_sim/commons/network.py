#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Asynchronous multi-threaded server over TCP. Uses a pool of threads to handle requests.
"""
import future
import sys
import threading
import queue
import socketserver
import struct
import json

from commons.utils import LoggerConfigurator, MessageIDGenerator, CustomJSONEncoder
from commons.messages import Message, InformationMessage


class TCPRequestHandler(socketserver.BaseRequestHandler):
    """
    A simple Handler for the ThreadPoolTCPServer. It just adds the request to the queue provided by
    the server.
    """

    def handle(self):
        """
        This method is called when a new request has arrived and the server wants to treat it. In
        this case, it adds the request to the queue.
        """
        self.server.queue.put(self.request)


class ThreadPoolTCPServer(socketserver.TCPServer):
    """
    This subclass of :class:`socketserver.TCPServer` is relying on a queue. The server is acting
    like a producer, providing the requests. On the other side of the queue, consumers should
    consume the requests. Because of this behaviour, the user is responsible to properly handle
    the request (which is a :class:`socket.socket` object). Remember that you need to close the
    request manually. You can access to the currently used Queue through the `queue` attribute
    """

    def __init__(self, server_address, handler=TCPRequestHandler,
                 bind_and_activate=True, _queue=None):
        """
        Creates a new ThreadPoolTCPServer.

        :param server_address: a tuple (hostname, port), see AF_INET and :class:`socket`
        :param handler: a handler of your own, default is :class:`TCPRequestHandler`
        :param bind_and_activate: see :class:`TCPServer`
        :param _queue: the queue that will be used by the server (and the handler). Default is
                       None, which means a new infinite queue will be created.
        """
        socketserver.TCPServer.__init__(
            self,
            server_address,
            handler,
            bind_and_activate
        )
        self.queue = queue.Queue() if _queue is None else _queue

    def process_request(self, request, client_address):
        """
        Overridden method, do not close the socket anymore (except if and error occurs in the
        RequestHandler `handle`, `handle_error` is also called)
        """
        try:
            self.finish_request(request, client_address)
        except:
            self.handle_error(request, client_address)
            self.shutdown_request(request)


class Worker(threading.Thread):
    """
    A `Worker` is designed to act like a consumer. Each `Worker` is running on its own thread.
    Subclasses should override the `work` method.
    As a thread, you have to call the `run` method to start the **Worker**.
    """

    def __init__(self, _queue, logger=None):
        """
        Creates a new Worker with the provided :class:`Queue`

        :param _queue: the `Queue`
        """
        super(Worker, self).__init__()
        self._queue = _queue
        self._stop_flag = False
        self._logger = logger

    def work(self, item):
        """
        The work that will be done.

        :param item: the element retrieved from the **Queue**
        """
        pass

    def run(self, blocking=True, timeout=1):
        """
        Overrides the `run` method from the :class:`Thread` class. The **Worker** is running
        until the stop flag is set (done through the `stop_soon` method).
        If an unexpected error occurs while executing the

        :param blocking: see :meth:`Queue.get`
        :param timeout:  see :meth:`Queue.get`
        """
        while not self._stop_flag:
            try:
                item = self._queue.get(block=blocking, timeout=timeout)
            except queue.Empty:
                continue  # Loop until the stop flag is set

            try:
                self.work(item)
            except Exception as e:
                self.handle_error(e, item)
            finally:
                self._queue.task_done()

        if self._logger is not None:
            self._logger.info("{} : {} is shutting down".format(
                self.__class__.__name__,
                threading.current_thread()
            ))

    def stop_soon(self):
        """
        Stop the thread as soon as possible. It depends on the timeout from the run method and
        the time it takes to do the job.
        Calling stop_soon is not enough to ensure the thread is dead, you should also call join
        after.
        """
        self._stop_flag = True

    def handle_error(self, error, item):
        """
        This method is called when an error occurs in the thread. Override it to provide your own
        error support. By default, this method re-raise the error (and the thread is killed).

        :param error: the error that have been raised.
        :param item: the item that was supposed to be handled
        """
        raise error


class Receiver(object):
    """
    A small object designed to receive a message to a provided socket and then parse it. To use
    it, first call the constructor with the socket you want to listen. Then, call the
    :meth:`receive` method. Later, you can access to the last parsed message through the
    property `last_msg`.::

        # First, create the object with your socket
        recv = Receiver(my_socket)

        # Then get the message
        msg = recv.receive()

        # Do some work here
        ...

        # You can access to the last parsed message
        msg = recv.last_msg

    """

    BUFFER_SIZE = 1024

    def __init__(self, sock, logger=None):
        """
        Create a new receiver, which will listen on the provided socket.

        :param sock: the socket where the message will be received
        """
        self._sock = sock
        self._last_msg = None
        self._logger = logger

    @property
    def last_msg(self):
        return self._last_msg

    def receive(self):
        """
        Start receiving a message on the socket provided in the constructor. Might raise several
        errors, like the ones raised by a wrong format in :meth:`struct.unpack`

        :return: a message, which has a Message subclass type
        """
        msg = self._sock.recv(Receiver.BUFFER_SIZE)

        # Find the size of the message and the remaining bytes
        msg_len = len(msg)

        if self._logger is not None:
            self._logger.debug("Receiver : buffer size is {}".format(msg_len))
            self._logger.debug("Receiver : message is {}".format(msg))

        msg_len, msg = struct.unpack(
            "!I" + str(msg_len - 4) + "s",
            msg
        )

        # Keep receiving until we reach the desired size
        while len(msg) != msg_len:
            msg += self._sock.recv(Receiver.BUFFER_SIZE)

        msg = msg.decode("ascii")

        # Parse the message
        msg = json.loads(msg)
        self._last_msg = Message.parse_from_dict(msg)

        return self._last_msg


class Sender(object):
    """
    This small object is designed to send a message through a provided socket. To use it,
    first create a new object with the socket you want to write. Then, call :meth:`send`.
    The sender field will be properly positioned to the socket address. The Sender object store
    the last sent message, you can access to it be using the read-only property
    `last_msg`.::

        with socket.create_connection(my_message.receiver) as sock:
            # Create the sender
            sender = Sender(sock)

            # Send the message
            sender.send(my_message)

            # Do extra work
            ....

            # You can access to the last sent message
            msg = sender.last_msg

    """

    def __init__(self, sock, logger=None):
        """
        Create a new Sender object with the provided socket.

        :param sock: the socket you want to write on
        """
        self._sock = sock
        self._last_msg = None
        self._logger = None

    @property
    def last_msg(self):
        return self.last_msg

    def send(self, msg):
        """
        Send a message through the socket provided to the constructor. This method is setting the
        sender field to the socket address.

        :param msg: the message you want to send (either a dict or a Message instance)
        """
        # Keep in memory the last message
        self._last_msg = msg

        addr, port = self._sock.getsockname()

        # Pack data into a buffer
        if isinstance(msg, dict):
            # Set the sender address to the current socket address and dump the message
            msg["sender"] = (addr, port)
            data = json.dumps(msg, cls=CustomJSONEncoder)
        else:
            # Set the sender address to the current socket address and dump the message
            msg.sender = (addr, port)
            data = json.dumps(msg.to_dict(), cls=CustomJSONEncoder)

        if self._logger is not None:
            self._logger.debug("Sender : message is {}".format(data))

        # Pack the data into a buffer
        l_data = len(data)

        if sys.version_info >= (3,):  # In python3 must be a bytearray
            msg = struct.pack("!I" + str(l_data) + "s", l_data, bytearray(data, "ascii"))
        else:
            msg = struct.pack("!I" + str(l_data) + "s", l_data, data)

        if self._logger is not None:
            self._logger.debug("Sender : buffer is {}".format(msg))

        # Send data
        self._sock.sendall(msg)


class MessageWorker(Worker):
    """
    This :class:`Worker` is consuming TCP requests. The expected message format is :
        | datalen |    data    |

    *datalen* occupying 4 octets and *data* datalen octets.
    """

    BUFFER_SIZE = 1024

    def __init__(self, _queue, handler_store, logger=None):
        """
        Create a new MessageWorker. In addition of the required parameter `_queue`, you need to
        provide a service store (where are stored your services), a subscription store (where are
        stored subscriptions) and a database connection (will be used by services).

        :param _queue: the queue where request are stored
        :param handler_store: a store that holds some InformationMessage id specific handlers
        """
        super(MessageWorker, self).__init__(_queue, logger)

        # Internal attributes
        self._handler_store = handler_store
        self._msg = None

    def work(self, request):
        """
        Do the work. First, it parses the message. Then, according to the message type, it calls
        the class-level handler. Then, the request is closed.

        :param request: the request the Worker has to handle
        """

        if self._logger is not None:
            self._logger.info("MessageWorker : Handle request from {}".format(
                request.getpeername()
            ))

        # Receive the message
        receiver = Receiver(request, self._logger)
        parsed_message = receiver.receive()

        if self._logger is not None:
            self._logger.debug("MessageWorker : {}".format(parsed_message))

        # Store it for error recovery
        self._msg = parsed_message

        # Handle the message (class-level handler)
        parsed_message.handle(
            message=parsed_message,
            request=request
        )

        # Handle the message (id specific)
        if isinstance(parsed_message, InformationMessage):
            # Check the store and execute handlers
            for handler in self._handler_store.get_handlers_for(parsed_message.linked_to):
                handler(parsed_message)

        # Close the connection and reset current message
        self._msg = None
        request.close()

    def handle_error(self, error, request):
        """
        Handle any error that occurs. If possible, the other process is contacted and informed
        that its request failed.

        :param error: the error occurring
        :param request: the original request
        """
        if self._msg is None:
            request.close()
            raise error

        msg = {
            "id": MessageIDGenerator.get_new_message_id(),
            "receiver": request.getpeername(),
            "linked_to": self._msg.id,
            "data": str(error)
        }

        if self._logger is not None:
            self._logger.warn("MessageWorker : {}".format(error))

        sender = Sender(request, self._logger)
        sender.send(msg)
        request.close()
