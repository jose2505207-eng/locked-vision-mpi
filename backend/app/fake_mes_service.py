"""Fake MES service — the SOURCE OF TRUTH.

Loads work orders, MPI step definitions, and zone definitions from the data
files. This module only serves authoritative data; it never decides flow and
never trusts vision to change the work-order definition.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class FakeMESService:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self._work_orders = self._load("work_orders.json")["work_orders"]
        self._mpi = self._load("mpi_steps.json")
        self._zones = self._load("zones.json")

    def _load(self, name):
        with open(os.path.join(self.data_dir, name)) as f:
            return json.load(f)

    def list_work_orders(self):
        return self._work_orders

    def get_work_order(self, work_order_id):
        return next(
            (w for w in self._work_orders if w["work_order_id"] == work_order_id),
            None,
        )

    def get_mpi(self, mpi_id):
        return self._mpi.get(mpi_id)

    def get_steps(self, mpi_id):
        return self._mpi[mpi_id]["steps"]

    def get_final_6s(self, mpi_id):
        return self._mpi[mpi_id]["final_6s"]

    def get_zones(self):
        return self._zones
