# -*- coding: utf-8 -*-
"""
This module holds some classes for making your life easier.
"""
import logging
import json
import os
import threading

from logging.handlers import RotatingFileHandler
from neo4j.v1 import Record, Node
from datetime import datetime


class LoggerConfigurator(object):
    """
    A small utility class which is useful for configuring a logger.
    """

    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    @classmethod
    def get_logger(cls, name, conf):
        """
        Get a :class:`logging.Logger`, providing it a name (leave empty to get the main one). You
        have to give a conf parameter, which is a dict like object. Required fields are::

            {
                "file": {
                    "available": True or False,
                    "filename": "a filename",
                    "level": "DEBUG", "INFO", "WARNING", "ERROR" or "CRITICAL"
                },
                "console": {
                    "available": True or False,
                    "level": "DEBUG", "INFO", "WARNING", "ERROR" or "CRITICAL"
                }
            }

        You can then access to the new created logger by using `logging.getLogger(name)`.

        :param name: the name of the logger. See :meth:`logging.getLogger`
        :param conf: a dict like object
        :return: the logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # Format the printed messages
        formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(message)s")

        # If file entry is set to true, create a rotating file handler
        if conf["file"]["available"]:
            file_handler = RotatingFileHandler(conf["file"]["filename"], "a", 10 ** 6, 1)
            file_handler.setLevel(LoggerConfigurator.LEVELS[conf["file"]["level"]])
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # If the console entry is set to true, create a console handler
        if conf["console"]["available"]:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(LoggerConfigurator.LEVELS[conf["console"]["level"]])
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        return logger


class CustomJSONEncoder(json.JSONEncoder):
    """
    This is a customize json encoder, able to encode strange objects that are Nodes and Records.
    Use it to encode data returned by a DBService.

        json.dumps(data, cls=CustomJSONEncoder)

    """
    def record_node_to_dict(self, o):
        result = dict()
        if isinstance(o, Record):
            for key, value in o.items():
                result[key] = self.record_node_to_dict(value)
        if isinstance(o, Node):
            for key, item in o.properties.items():
                result[key] = item
        return result

    def default(self, o):
        """
        Is able to parse o if o is either a Record or a Node. Otherwise, call the super default
        method which raises TypeError.

        :param o: an object
        :return: a json encoded object
        :raise: TypeError
        """
        d = self.record_node_to_dict(o)
        return d
        '''
        if isinstance(o, (Record, Node)):
        return {
            str(key): self.encode(value) if not isinstance(value, str) else value
            for key, value in o.items()
        }
        return super(CustomJSONEncoder, self).default(o)
        '''



class MessageIDGenerator(object):
    """
    This utility class is designed to give you a unique id for your process. To produce such ids, it
    will get your process' pid and add it a number. Produced ids are like **1234_4**.

    **Notice**: this class is threadsafe, which means you will never get the same id, even if two
    threads are requiring a number at the same time.
    """

    # Keep track of the current id
    _current_id = 0

    @classmethod
    def get_new_message_id(cls):
        """
        This method returns a new unique id.

        :return: a string like **1234_4**
        """
        with threading.Lock():
            result = cls._current_id
            cls._current_id += 1
        return str(os.getpid()) + "_" + str(result)

    def __init__(self):
        """
        This is a static class, so you can't instantiate it.
        """
        raise NotImplementedError()


class ConfigurationLoader(object):
    """
    The configuration loader allows process to access to some configuration variables. You just
    have to now where the configuration file is. Once it's done, call :meth:`get_instance`
    method and set the file property to the configuration file path.

    You can access to the stored configuration like a dictionary (read-only). So if the
    configuration file is::

        {
            "some_entry": {
                "a_sub_entry": value,
                "another_sub_entry": other_value
            }
        }

    You can access to the `another_sub_entry` value like this::

        my_value = conf["some_entry"]["another_sub_entry"]

    Remember that some classes are using it, retrieving the configuration loader through the
    :meth:`get_instance` method. So if you are changing the file property, it should be the first
    thing you do.

    **Notice**: even if you can create your own instance of this class, remember any modification on
    the newly created object will not be reflected by the :meth:`get_instance`. So use it at
    your own risks.

    An example would be::

        conf = ConfigurationLoader.get_instance()

        # Change the configuration file location if needed
        conf.file = os.path.abspath("path/to/conf/file.conf")

        # From now, the ConfigurationLoader will serve  the file.conf file.

    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Get the configured ConfigurationLoader. You should always use this method, rather than
        create your own object (even if it's possible).

        :return: a ConfigurationLoader instance
        """
        if cls._instance is None:
            cls._instance = ConfigurationLoader()
        return cls._instance

    def __init__(self):
        """
        Create a brand new ConfigurationLoader. You should use it if you now what you are doing.
        Otherwise, use the :meth:`get_instance`:
        """
        self._file = None
        self._data = None

    @property
    def file(self):
        """
        Get the configuration file path to the currently served configuration or None if there is no
         configuration currently served.

        :return: a path-like object
        """
        return self._file

    @file.setter
    def file(self, value):
        """
        Change the configuration. Once it's done, the ConfigurationLoader will serve the new
        configuration file.

        :param value: a path to the configuration file
        """
        self._file = os.path.abspath(value)
        self.load()

    def load(self):
        """
        Load the configuration file. Raise an error if the is no file to read (the property
        `file` hasn't been set).
        """
        with open(self._file, "r") as fd:
            self._data = json.load(fd)

    def get(self, value, default):
        return self._data.get(value, default)

    def __getitem__(self, item):
        return self._data.__getitem__(item)

    def __iter__(self):
        return self._data.__iter__()

    def __repr__(self):
        return self._data.__repr__()


class HandlerStore(object):
    """
    A HandlerStore is where you can store callbacks for a provided message id.
    """
    def __init__(self):
        self._store = {}

    def register_handler_for(self, message_id, handler):
        """
        Add a new handler for the provided message id. If previous handlers were registered,
        they will remain.

        :param message_id: the message id
        :param handler: a callback function
        """
        if not self._store.get(message_id, False):
            self._store[message_id] = []
        self._store[message_id].append(handler)

    def set_handlers_for(self, message_id, handlers):
        """
        Erase previously registered handlers and set the provided ones instead.

        :param message_id: the message id
        :param handlers: the new handlers
        """
        self._store[message_id] = handlers[:]

    def get_handlers_for(self, message_id):
        """
        Get all registered handlers for the provided message id.

        :param message_id: the message id
        :return: an empty list if no handlers provided, the list of handlers else
        """
        return self._store.get(message_id, [])[:]

    def remove_handlers_for(self, message_id):
        """
        Remove all callbacks associated to the provided  message_id.

        :param message_id: the message id
        """
        if self._store.get(message_id, False):
            del self._store[message_id]


def get_final_classes(base_class):
    """
    This function retrieves the final classes (classes without any children) that derive from a
    given class

    :param base_class:
    The root class
    :return:
    A set of the final classes
    """
    result = set()
    sub_classes = base_class.__subclasses__()
    if len(sub_classes) == 0:
        return {base_class}

    for sub_class in sub_classes:
        result = result.union(get_final_classes(sub_class))
    return result


def create_datetime_from_time(t):
    """
    This method creates a datetime from a given time object
    The Year, Month, Day will all be set to one
    :param t:
    :return:
    """
    return datetime(1, 1, 1, t.hour, t.minute, t.second, t.microsecond)