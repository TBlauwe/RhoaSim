# -*- coding: utf-8 -*-

from commons.services.common import DBService

class SetArucoService(DBService):

    @staticmethod
    def _build_query(**kwargs):
        query = "MATCH (i)"
        query += " WHERE sqrt((i.x - $x) ^ 2 + (i.y - $y) ^ 2) <= i.r"
        query += " SET i.aruco = $aruco"
        query += " RETURN i"
        return query