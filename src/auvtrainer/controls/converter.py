from types import NoneType
from typing import Optional, Tuple

import numpy as np

from auvtrainer.client.requests import DBApiClient


class Converter:
    """
    Converts input rows from the database into output motor commands and posts them.
    """

    def __init__(self) -> None:
        self.client = DBApiClient("http://localhost:8000")
        # NOTE: these arrays appear to be placeholder/scalar ranges; keep as-is to avoid changing behavior
        self.in_mins = np.array([-25, -10])
        self.in_maxs = np.array([25, 10])
        self.out_mins = np.array([-25, -10])
        self.out_maxs = np.array([25, 10])

        self.mapping = np.array(
            [
                #    M1 M2 M3 M4 M5  M6 M7  M8
                [0, 0, 0, 0, 1, 1, 1, 1],  # X
                [0, 0, 0, 0, 1, -1, 1, -1],  # Y
                [1, 1, 1, 1, 0, 0, 0, 0],  # Z
                [0, 0, 0, 0, 1, -1, 1, -1],  # Yaw
            ]
        )

    def _get_inputs(self) -> Tuple[np.ndarray, bool, Optional[int]]:
        """
        Fetch the newest inputs row from the DB.

        Returns:
          - inputs: numpy array of numeric fields (fallback to zeros if no row)
          - arm: boolean flag from the row (False if no row)
          - inputs_id: integer id of the row, or None if there is no row
        """
        inputs = self.client.table_get_newest("inputs")
        print(f"Retrieved inputs: {inputs}")
        if inputs is None or type(inputs) is NoneType:
            arm = False
            inputs_id = None
            inputs_arr = np.array([0.0] * 8)
        else:
            arm = bool(inputs["newest_row"].get("arm", False))
            inputs_id = (
                int(inputs["newest_row"]["id"]) if type(inputs["newest_row"]["id"]) is int else None
            )
            # Collect numeric values from the row in deterministic order
            inputs_arr = np.array(
                [
                    value
                    for _, value in inputs["newest_row"].items()
                    if isinstance(value, (int, float))
                ]
            )
        return inputs_arr, arm, inputs_id

    def _post_outputs(self, outputs: np.ndarray, inputs_id: Optional[int]) -> None:
        """
        Post outputs to the DB. Accepts an Optional[int] inputs_id; if it's None,
        the function will skip posting since outputs can't be associated.
        """
        if inputs_id is None or type(inputs_id) is NoneType:
            # Nothing to associate the outputs with; skip posting.
            # Could log here if desired.
            return

        outputs_dict = {
            "inputs_id": str(inputs_id),
            "m1": float(outputs[0]),
            "m2": float(outputs[1]),
            "m3": float(outputs[2]),
            "m4": float(outputs[3]),
            "m5": float(outputs[4]),
            "m6": float(outputs[5]),
            "m7": float(outputs[6]),
            "m8": float(outputs[7]),
        }
        self.client.table_append("outputs", outputs_dict)

    def _map(self, value: float, i: int) -> float:
        # Preserve existing mapping behavior
        return (value - self.in_mins[i]) * (self.out_maxs[i] - self.out_mins[i]) / (
            self.in_maxs[i] - self.in_mins[i]
        ) + self.out_mins[i]

    def _mapInputs(self, inputs: np.ndarray, arm: bool) -> np.ndarray:
        """
        Map joystick-like inputs into motor command array of length 8.
        """
        command = np.array([0.0] * 8)
        if arm:
            if inputs[0] > inputs[1] > inputs[3]:
                command = inputs[0] * self.mapping[0]  # X
            elif inputs[1] > inputs[0] > inputs[3]:
                command = inputs[1] * self.mapping[1]  # Y
            elif inputs[3] > inputs[0] > inputs[1]:
                command = inputs[3] * self.mapping[3]  # Yaw

            if inputs[2] > 0:
                command[0:4] = (inputs[2] * self.mapping[2])[0:4]  # Z
        else:
            command = np.array([0.0] * 8)
        return command

    def run_conversion_step(self) -> None:
        """
        Perform a single conversion step: fetch inputs, map them, and post outputs.
        _post_outputs accepts Optional[int], so we can pass inputs_id directly.
        """
        inputs, arm, inputs_id = self._get_inputs()
        mapped_inputs = self._mapInputs(inputs, arm)
        # _post_outputs will handle the None case for inputs_id
        self._post_outputs(mapped_inputs, inputs_id)


if __name__ == "__main__":
    converter = Converter()
    import time

    while True:
        converter.run_conversion_step()
        time.sleep(0.01)
