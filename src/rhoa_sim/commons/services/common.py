# -*- coding: utf-8 -*-
"""
This module describes what interface should follow user-defined services and is shipped with some
services.
If you want to provide your own services, put them on a module and define a **load_services**
function. See the one define in this module.
"""
import future
import sys

import os
import queue
import socket

from commons.network import Worker, Sender
from commons.utils import get_final_classes, LoggerConfigurator, MessageIDGenerator

if sys.version_info >= (3,):
    import importlib.util
else:
    import importlib


class ServiceLoader(object):
    """
    The ServiceLoader is used to load modules in the given directories and then, search for leafs in
     the Service heritage tree. If the loaded modules contain some, then this leafs will be
     stored in a provided service store.
    """

    # Some names are excluded when the loader is looking fo modules
    EXCLUDED = ["__init__.py", "__pycache__"]

    def __init__(self, path, logger=None):
        """
        Create a new ServiceLoader with the given path(s).

        :param path: str or list of directories you want to check
        """
        self.path = path
        self._loaded_modules = []
        self._logger = logger

    @property
    def path(self):
        """
        Get all registered directories for search.

        :return: a list of directories (str)
        """
        return self._path

    @path.setter
    def path(self, value):
        """
        Set the search directories.

        :param value: str or list of directories (str)
        """
        if isinstance(value, str):
            self._path = [value]
        elif isinstance(value, (list, tuple)):
            self._path = value[:]
        else:
            raise TypeError()

    def load(self, service_store):
        """
        Load each module and then search for leafs in the Service heritage tree. The leafs will
        be stored in the provided service store.

        :param service_store: the service store where services will be registered.
        """
        for path in self.path:
            self._loaded_modules = self._load_modules(path)

        for service in get_final_classes(Service):
            service_store.register_service(service)

    def _load_modules(self, path):
        """
        Utility function for loading modules.

        :param path: a directory
        :return: all loaded modules
        """
        lst = os.listdir(os.path.abspath(path))
        result = set()
        for d in lst:
            if d in ServiceLoader.EXCLUDED:
                continue

            s = os.path.join(os.path.abspath(path), d)
            if os.path.isdir(s):
                result.update(self._load_modules(s))
            elif os.path.isfile(s):
                name = d.split('.')[0]
                if sys.version_info >= (3,):
                    spec = importlib.util.spec_from_file_location(
                        name,
                        s
                    )
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                else:
                    rel_path = os.path.relpath(s)
                    print(rel_path)
                    mod = importlib.import_module(
                        ".".join(rel_path.split(os.path.sep)[1:]).split(".")[0]
                    )
                result.add(mod)
        return result


class ServiceStore(object):
    """
    ServiceStore objects are designed to store services. You can retrieve stored services with
    their name.
    """

    def __init__(self, logger=None):
        """
        Create a new ServiceStore. At the beginning, there are no registered services;
        """
        self._store = {}
        self._logger = logger

    def register_service(self, service_class):
        """
        Register a new Service in the service store. Do nothing if the service was already
        registered.

        :param service_class: the service class.
        """
        name = service_class.__name__
        if name not in self._store.keys():
            self._store[name] = service_class
        elif self._logger is not None:
            self._logger.warn(
                "ServiceStore: Adding an already registered service ({})".format(name)
            )

    def unregister_service(self, service_class):
        """
        Forget a service. Do nothing if service wasn't registered previously.

        :param service_class: the service class
        """
        name = service_class.__name__
        if name in self._store.keys():
            del self._store[name]
        elif self._logger is not None:
            self._logger.warn(
                "ServiceStore: Removing an unregistered service({})".format(name)
            )

    def get_service_class(self, service_name):
        """
        Get a stored service according to its class name.

        :param service_name: the name of the service
        :return: the service class if registered, else None.
        """
        service = self._store.get(service_name, None)
        if service is None and self._logger is not None:
            self._logger.warn("ServiceStore: service {} doesn't exist".format(service_name))
        return service


class SubscriptionStore(object):
    """
    This object is storing Services that need to be notified when changes are occurring. Services
    are stored in an internal dictionary, grouped by class name. Each subscriptions is a tuple
    containing the following information:

        - the instantiate service
        - the original request message (it should be an instance of :class:`old.messages.SubscriptionMessage`)
        - the last value
        - some additional parameters that need to be passed to the execute method.

    The SubscriptionStore is lazy, which means it won't send messages if the value hasn't
    changed. Notice that it will still execute concerned services at each time.
    Because the ServiceStore is using a bunch of threads internally, remember calling the
    :meth:`stop_workers` method before deleting the object.
    """

    class ReplySender(Worker):
        """
        This Worker is design to send results to process. It is processing a tuple (computed
        value, original subscription message) and will send the result to the address provided by
        the key 'reply_to' of the SubscriptionMessage.
        """

        def work(self, item):
            """
            Processes item (which is value, request).

            :param item: a tuple value, SubscriptionMessage
            """
            value, request = item

            # Create a socket (TCP socket)
            with socket.create_connection(request.reply_to) as sock:

                # Create the message and send it
                sender = Sender(sock, self._logger)
                sender.send({
                    "id": MessageIDGenerator.get_new_message_id(),
                    "linked_to": request.id,
                    "receiver": sock.getpeername(),
                    "data": value
                })
                if self._logger is not None:
                    self._logger.debug("Sending back data")

    class ServiceExecutor(Worker):
        """
        The ServiceExecutor is a thread that runs services. It uses a queue to get them and put
        the results in an other one.
        """

        def __init__(self, in_queue, out_queue, logger=None):
            """
            Create a new ServiceExecutor.

            :param in_queue: services that will be executed
            :param out_queue: where results will be put
            """
            super(SubscriptionStore.ServiceExecutor, self).__init__(in_queue)
            self._out_queue = out_queue
            self._logger = logger

        def work(self, services):
            """
            Run each service and, if the computed value is different from the last one,
            put the data into the out_queue.

            :param services: a list of tuple (service, request, last_value, args, kwargs)
            """
            for service, request, last, args, kwargs in services:
                result = service.execute(*args, **kwargs)
                if result != last:
                    self._out_queue.put((result, request))

    def __init__(self, executors_nb=3, reply_senders_nb=1, logger=None):
        """
        Create a new SubscriptionStore.

        :param executors_nb: how many threads will be created to handle services execution
        :param reply_senders_nb: how many threads will be created to handle replies sending
        """
        self._store = dict()  # Store the subscriptions
        self._waiting_replies = queue.Queue()  # Notifications that need to be sent
        self._waiting_services = queue.Queue()  # Affected services that need to be recomputed
        self._logger = logger
        self._executors = [
            SubscriptionStore.ServiceExecutor(
                self._waiting_services,
                self._waiting_replies,
                logger=self._logger
            ) for
            _ in range(executors_nb)
        ]
        self._reply_senders = [
            SubscriptionStore.ReplySender(
                self._waiting_replies,
                logger=self._logger
            ) for _ in range(reply_senders_nb)
        ]
        self._start_workers()

    def _start_workers(self):
        """
        Utility method designed to start every workers (executors and senders)
        """
        for executor in self._executors:
            executor.start()
        for sender in self._reply_senders:
            sender.start()

    def add_subscription(self, service, request, last_value, *args, **kwargs):
        """
        Register a new subscription with the given service and reply_to information.

        :param last_value: the last result obtained by running the service
        :param service: an object that have an execute method
        :param request: the received message
        :param args: additional parameters that will be passed to the execute method
        :param kwargs: additional parameters that will be passed to the execute method
        """
        # Subscriptions are stored according to the service class name
        class_name = service.__class__.__name__

        if not self._store.get(class_name, False):
            self._store[class_name] = []

        # Only one subscription per service and process
        if len([item for item in self._store[class_name] if item.sender == request.sender]) != 0:
            if self._logger is not None:
                self._logger.warn(
                    "SubscriptionStore: {} tried to register itself for {} twice.".format(
                        request.sender,
                        class_name
                    )
                )
            return  # TODO : raise an error

        # Register the subscription
        self._store[class_name].append((
            service,
            request,
            last_value,
            args,
            kwargs
        ))

    def remove_subscription(self, request):
        """
        Remove a subscription from the store. Fail silently if the service has not been registered.

        :param request: the unsubscribe message
        """
        class_name = request.service
        if class_name in self._store.keys():
            i = 0
            while (i < len(self._store[class_name])
                   and self._store[class_name][i][1].sender != request.sender):
                i += 1
            if i < len(self._store[class_name]):
                self._store[class_name].pop(i)
            elif self._logger is not None:
                self._logger.warn(
                    "SubscriptionStore: sender {}  has no subscription to ".format(
                        request.sender,
                        class_name
                    )
                )
        elif self._logger is not None:
            self._logger.warn(
                "SubscriptionStore: the service {} has no active subscription".format(class_name)
            )

    def notify_subscribers(self, services):
        """
        Called by an observed service, it will notify services with the given service classes.

        :param services: a class or a list of class
        """
        if isinstance(services, type):
            services = [services]
        for service_type in services:
            if self._store.get(service_type.__name__, False):
                self._waiting_services.put(self._store[service_type.__name__])

    def _stop_executors(self):
        """
        Stop the executors. Will perform a join on them.
        """
        for executor in self._executors:
            executor.stop_soon()
            executor.join()

    def _stop_reply_senders(self):
        """
        Stop the senders. Will perform a join on them.
        :return:
        """
        for sender in self._reply_senders:
            sender.stop_soon()
            sender.join()

    def stop_workers(self):
        """
        Stop workers. Block until it's done.
        """
        self._stop_executors()
        self._stop_reply_senders()


class Service(object):
    """
    A Service is designed to ask something to the context process. This is just a skeleton class
    and it is not designed to be used directly. If you want to add new services, consider
    subclassing.
    """

    DEPENDENCIES = []
    REQUIRED_PARAMS = set()

    def __init__(self, sub_store, service_store):
        """
        Create a new Service that will use the given subscription store to notify observers.

        :param sub_store: a SubscriptionStore
        :param service_store: a ServiceStore
        """
        self.sub_store = sub_store
        self.service_store = service_store

    def execute(self, *args, **kwargs):
        """
        Execute the service and get results. When a Service is executed, it should notify all
        dependencies that the value might have changed.::

            def execute(self, *args, **kwargs):
                ...  # do what the service is supposed to do
                self.sub_store.notify_subscribers(self.__class__.DEPENDENCIES)
                return ...  # Return the a value if needed


        :param args: additional parameters
        :param kwargs: additional named parameters
        :return: depends on the service's type
        """
        raise NotImplementedError()


class DBService(Service):
    """
    This type of services is talking to a database using the CYPHER language. The only difference
    with a basic service is that you need to provide a database connection.
    This class also provide a fully implemented execute method. Internally, it uses the
    _build_query method to create the query. If you are subclassing, you have to redefined it.

    An example would be ::

        class MyCustomService(DBService):

            DEPENDENCIES = []

            @staticmethod
            def _build_query(**kwargs):
                query = "MATCH (a) RETURN a"
                return query

    You can create more complex queries by using the kwargs dictionary. Keys and values inside it
    are exactly the same as the one provided to the execute method. So you can write queries like ::

        @staticmethod
        def _build_query(**kwargs):
            query = "MATCH (r:Robot {"
            query += ", ".join([str(k) + ": $" + str(key) for key in kwargs])
            query += "})"
            query += " RETURN r"
            return query

    """

    def __init__(self, sub_store, service_store, connection):
        """
        Create a new DBService that will use the given connection to execute the query. It will
        create a new session and execute a transaction inside it.

        :param connection: a :class:`neo4j.v1.GraphDataBase` object
        :param sub_store: a SubscriptionStore
        :param service_store: a ServiceStore
        """
        super(DBService, self).__init__(sub_store, service_store)
        self.connection = connection

    def execute(self, *args, **kwargs):
        """
        Execute the service and get results. You can provide you own session by using the named
        parameter `session`.

        :param args: not used in DBService
        :param kwargs: extra parameters passed to the query. It will be used to replace named
            parameters int he query by the provided value.
        :return: the cypher query result
        """
        # Remove the session key as it could be problematic if a query builder is iterating
        # over keys to create/match nodes
        session = kwargs.get("session", None)
        if session is not None:
            del kwargs["session"]

        # Build the query after checking that the necessary parameters are passed in kwargs
        if not self.REQUIRED_PARAMS.issubset(kwargs.keys()):
            raise TypeError()

        query = self._build_query(**kwargs)

        # If a session is provided, the method will use it. Otherwise, it will create its own.
        if session is not None:
            with session.begin_transaction() as tx:
                result = tx.run(
                    query,
                    kwargs
                )
        else:
            with self.connection.session() as session:
                with session.begin_transaction() as tx:
                    result = tx.run(
                        query,
                        kwargs
                    )

        # Notify the subscription store that somme data has changed
        self.sub_store.notify_subscribers(self.__class__.DEPENDENCIES)

        # Return the result as a dict of things. Careful, it could be nodes and records
        return list(result)

    @staticmethod
    def _build_query(**kwargs):
        """
        Create the query that will run in the execute method.

        :param kwargs: the same data that will be passed to the query late.
        :return: a string, which is the CYPHER query.
        """
        raise NotImplementedError()


class IteratedDBService(DBService):

    @staticmethod
    def _build_query(**kwargs):
        pass

    def execute(self, *args, **kwargs):
        """
        Execute the service and get results. You can provide you own session by using the named
        parameter `session`.

        :param args: A list of tuples, each one being args and kwargs of the repeated service
        :param kwargs: not used in IteratedDBService
        :return: a list of each result
        """
        # Remove the session key as it could be problematic if a query builder is iterating
        # over keys to create/match nodes
        session = kwargs.get("session", None)
        if session is not None:
            del kwargs["session"]

        # Build the query after checking that the necessary parameters are passed in kwargs
        if not self.REQUIRED_PARAMS.issubset(kwargs.keys()):
            raise TypeError()

        # Future results
        result = []

        services_args = args[1:]
        service_name = args[0]

        # If a session is provided, the method will use it. Otherwise, it will create its own.
        if session is not None:
            for a, k in args:
                result.append(
                    self.service_store.get_service_class(service_name)(
                        connection=self.connection,
                        sub_store=self.sub_store,
                        service_store=self.service_store
                    ).execute(*a, session=session, **k)
                )
        else:
            with self.connection.session() as session:
                for a, k in args:
                    result.append(
                        self.service_store.get_service_class(service_name)(
                            connection=self.connection,
                            sub_store=self.sub_store,
                            service_store=self.service_store
                        ).execute(*a, session=session, **k)
                    )
        return result


class FindRunningAction(DBService):

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH (a:Robot)-[:EXECUTE]->(:AgentPlan)-[:RUNNING*]->(ac:Action)"
        query += " WHERE a.name = $name"
        query += " RETURN ac"
        return query


class FindExperiencesBefore(DBService):
    """
    This service is used to retrieve experiences that began before a given time
    The time should be given as a timestamp in an entry named beginTime
    """
    REQUIRED_PARAMS = {"begin_time"}

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH (e:Experience)"
        query += " WHERE e.beginTime <= $begin_time"
        query += " RETURN e"
        return query


class FindExperiencesAfter(DBService):
    """
    This Service is used to retrieve experiences that began after a given time
    The time should be given as a timestamp in an entry named beginTime
    """
    REQUIRED_PARAMS = {"begin_time"}

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH (e:Experience)"
        query += " WHERE e.beginTime >= $begin_time"
        query += " RETURN e"


class AddExperience(DBService):
    """
    This Service is used to add an experience to the database
    It requires three parameters:
    beginTime : the timestamp of the beginning of the experience
    passageTime : a number of minutes
    concerned_name : The name of the section or intersection concerned by the experience
    """
    DEPENDENCIES = [FindExperiencesAfter, FindExperiencesBefore]

    REQUIRED_PARAMS = {"begin_time", "passage_time", "concerned_name"}

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH (c{name: $concerned_name}) WHERE c:Intersection or c:Section "
        query += "CREATE (e:Experience {"
        query += "beginTime: $begin_time, "
        query += "passageTime: $passage_time})"
        query += "-[:CONCERNS]->(c)"
        return query


class FindExperience(DBService):
    """
    This method finds experiences optionally matching these criteria
    min_begin_time : the minimum timestamp for the beginning time of the experiences
    max_begin_time : the maximum timestamp for the beginning time of the experiences
    min_passage_time : the minimum passage time of the experiences
    max_passage_time : the maximum passage time of the experiences
    concerned_name : the name of the concerned intersection or section
    concerned_zone_name : the name of the concerned zone (it will be ignored if concerned_name is given)

    If concerned_name is not given, for each experience, the service will also return the concerned node
    """
    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH (e:Experience)-[:CONCERNS]-(a"
        # checking if we have a concerned section or intersection
        if "concerned_name" in kwargs.keys():
            query += "{name : $concerned_name}) "
        # if not we check if we have a concerned_zone
        elif "concerned_zone_name" in kwargs.keys():
            # The inclusion of the concerned section or intersection into the zone can be indirect
            query += ":Intersection)-[:CONTAINS*]-(z:Zone{name: $concerned_zone_name}) "
        else:
            query += ")"

        # if we have any of these parameters, we then have a Where statement
        if not {"min_begin_time", "max_begin_time", "min_passage_time", "max_passage_time"}.isdisjoint(kwargs.keys()):
            query += "WHERE "
            # an array of conditions
            conditions = []
            if "min_begin_time" in kwargs.keys():
                kwargs["min_begin_time"] = int(kwargs["min_begin_time"])
                conditions.append("e.beginTime>= $min_begin_time")
            if "max_begin_time" in kwargs.keys():
                kwargs["max_begin_time"] = int(kwargs["max_begin_time"])
                conditions.append("e.beginTime<= $max_begin_time")
            if "min_passage_time" in kwargs.keys():
                kwargs["min_passage_time"] = int(kwargs["min_passage_time"])
                conditions.append("e.passageTime>= $min_passage_time")
            if "max_passage_time" in kwargs.keys():
                kwargs["max_passage_time"] = int(kwargs["max_passage_time"])
                conditions.append("e.passageTime<= $max_passage_time")
            # joining the conditions with an AND
            query += " AND ".join(conditions)+" "

        query += "RETURN e as experience"
        # if concerned_name was not passed, we return the concerned node along with the experience
        if "concerned_name" not in kwargs.keys():
            query += " , a as concerned"

        return query


class GetMapGraph(DBService):
    """
    This Service is used to retrieve the map in a graph form
    """
    @staticmethod
    def _build_query(**kwargs):
        query = "match (a)-[:LINK]-(b) return a, b"
        return query


class FindAbstractionsService(DBService):

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH p = (i)-[:CONTAINS*]-(z) "
        query += " WHERE sqrt((i.x - $x) ^ 2 + (i.y - $y) ^ 2) <= i.r"
        query += " RETURN nodes(p)"
        return query
