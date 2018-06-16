# -*- coding: utf-8 -*-

from commons.services.common import DBService


class GetDrugStoreService(DBService):
    """
    This service is used to get all the information about a drugStore and the intersection that it's located on
    """
    @staticmethod
    def _build_query(**kwargs):
        query = "Match (a:Drugstore{name:$name})-[:CONTAINS]-(b:Intersection)"
        query += "Return a as drugstore, b as intersection"
        return query


class GetDepotStoreService(DBService):
    """
    This service is used to get all the information about a depot and the intersection that it's located on
    """
    @staticmethod
    def _build_query(**kwargs):
        query = "Match (a:Depot{name:$name})-[:CONTAINS]-(b:Intersection)"
        query += "Return a as depot, b as intersection"
        return query


class FuelLevelService(DBService):
    """
    This is a custom service. It is designed to check the fuel level of the given robot. As a
    DBService subclass, you have to provide a database connection.
    """

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH (a:Robot)"
        if kwargs.get("name", False):
            query += " WHERE a.name = $name"
        query += " RETURN a.fuel_level"
        return query


class SetFuelLevelService(DBService):
    """
    Set the fuel level of the provided robot.
    """

    # Dependencies
    DEPENDENCIES = [FuelLevelService]

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH (a:Robot {name: $name})"
        query += " SET a.fuel_level = $fuel_level"
        query += " RETURN a.name, a.fuel_level"
        return query


class GetRobotPosition(DBService):

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH(a: Robot {name: $name})-[: STATE]->(o:Odometry),"
        query += "(a) < -[: CONTAINS]-(i)"
        query += "OPTIONAL MATCH(i) < -[: CONTAINS *]-(z)"
        query += "RETURN o, i, z"

        return query


class SetRobotPosition(DBService):

    DEPENDENCIES = [GetRobotPosition]

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH (a:Robot {name: $name})-[:STATE]->(o:Odometry)"
        query += " SET o.x = $x, o.y = $y, o.z = $z"
        query += " WITH a, o"
        query += " MATCH (i), (a)<-[rel:CONTAINS]-()"
        query += " WHERE (i:Intersection OR i:Section) AND sqrt((i.x - $x) ^ 2 + (i.y - $y) ^ 2) " \
                 "<= i.radius"
        query += " DELETE rel "
        query += " CREATE (a)<-[:CONTAINS]-(i)"
        query += " RETURN a.name, o"
        return query


def load_services(service_store):
    """
    This method is designed to register our services to the service store. It is called by a
    ServiceLoader and the later will provide the store.

    :param service_store: the store where services will be stored
    """
    service_store.register_service(GetDrugStoreService)
    service_store.register_service(FuelLevelService)
    service_store.register_service(SetFuelLevelService)
    service_store.register_service(GetRobotPosition)
    service_store.register_service(SetRobotPosition)
