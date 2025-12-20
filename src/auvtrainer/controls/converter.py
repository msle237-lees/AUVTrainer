import numpy as np
from typing import Tuple

from auvtrainer.client.requests import DBApiClient

class Converter:
    def __init__(self):
        self.client = DBApiClient("http://localhost:8000")
        self.in_mins = np.array([-25, -10])
        self.in_maxs = np.array([25, 10])
        self.out_mins = np.array([-25, -10])
        self.out_maxs = np.array([25, 10])

        self.mapping = np.array(
            [
            #    M1 M2 M3 M4 M5  M6 M7  M8
                [ 0, 0, 0, 0, 1,  1, 1,  1],   # X
                [ 0, 0, 0, 0, 1, -1, 1, -1], # Y
                [ 1, 1, 1, 1, 0,  0, 0,  0],   # Z
                [ 0, 0, 0, 0, 1, -1, 1, -1]  # Yaw
            ]
        )

    def _get_inputs(self) -> Tuple[np.ndarray, bool]:
        inputs = self.client.table_get_newest("inputs")
        print(f"Retrieved inputs: {inputs}")
        if inputs is None:
            arm = False
            inputs = np.array([0.0] * 8)
        else:
            arm = inputs["newest_row"]["arm"]
            inputs = np.array([value for _, value in inputs["newest_row"].items() if isinstance(value, (int, float))])
        return inputs, arm
    
    def _post_outputs(self, outputs : np.ndarray) -> None:
        outputs_dict = {
            "M1": float(outputs[0]),
            "M2": float(outputs[1]),
            "M3": float(outputs[2]),
            "M4": float(outputs[3]),
            "M5": float(outputs[4]),
            "M6": float(outputs[5]),
            "M7": float(outputs[6]),
            "M8": float(outputs[7])
        }
        self.client.table_append("outputs", outputs_dict)

    def _map(self, value: float, i : int) -> float:
        return (value - self.in_mins[i]) * (self.out_maxs[i] - self.out_mins[i]) / (self.in_maxs[i] - self.in_mins[i]) + self.out_mins[i]
    
    def _mapInputs(self, inputs : np.ndarray, arm : bool) -> np.ndarray:
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
        inputs, arm = self._get_inputs()
        mapped_inputs = self._mapInputs(inputs, arm)
        self._post_outputs(mapped_inputs)

if __name__ == "__main__":
    converter = Converter()
    import time
    while True:
        converter.run_conversion_step()
        time.sleep(0.01)