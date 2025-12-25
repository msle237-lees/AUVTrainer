from __future__ import annotations

import holoocean
import numpy as np

from auvtrainer.client.requests import DBApiClient
from auvtrainer.simulation.scenario import scenario


class ManualDatabase:
    """
    Pulls the newest thruster command from the DB API (/db/tables/outputs/get/newest)
    and applies it to the HoloOcean simulation.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.client = DBApiClient(base_url)

        # Optional: sanity checks (will raise if API is down or table missing)
        _ = self.client.status()
        _ = self.client.list_tables()
        self.output_schema = self.client.table_schema("outputs")

        self.env = holoocean.make(scenario_cfg=scenario)

        # Column order we expect from the outputs table
        self._motor_cols = ("m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8")

    def _default_command(self) -> np.ndarray:
        """
        Default command when the outputs table is empty.
        """
        return np.zeros(8, dtype=np.float32)

    def generate_command(self) -> np.ndarray:
        """
        Read newest outputs row and convert to a HoloOcean action vector.

        Returns:
            np.ndarray shape (8,) float32
        """
        payload = self.client.table_get_newest("outputs")
        newest_row = payload.get("newest_row")

        if not newest_row:
            return self._default_command()

        # Build command in a stable order (m1..m8). Missing keys -> 0.
        cmd = np.array(
            [float(newest_row.get(col, 0)) for col in self._motor_cols], dtype=np.float32
        )
        return cmd

    def run_simulation_step(self) -> None:
        command = self.generate_command()

        self.env.act("auv0", command)
        state = self.env.tick()

        depth = state.get("DepthSensor")
        imu = state.get("IMUSensor")

        print(f"Command: {command}\nDepth Data: {depth}\nIMU Data: {imu}\n")

    def run(self) -> None:
        with self.env:
            while True:
                self.run_simulation_step()


if __name__ == "__main__":
    manual_db = ManualDatabase()
    manual_db.run()
