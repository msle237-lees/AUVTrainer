import holoocean
import numpy as np

from auvtrainer.client.requests import DBApiClient
from auvtrainer.simulation.scenario import scenario

class ManualDatabase:
    def __init__(self):
        self.client = DBApiClient("http://127.0.0.1:8000")
        
        tables = self.client.list_tables()
        self.output_schema = self.client.table_schema("outputs")

        self.env = holoocean.make(scenario_cfg=scenario)

    def generate_command(self):
        command = self.client.table_get_newest("outputs")
        if command is None:
            command = {
                "M1": 0.0,
                "M2": 0.0,
                "M3": 0.0,
                "M4": 0.0,
                "M5": 0.0,
                "M6": 0.0,
                "M7": 0.0,
                "M8": 0.0
            }
        else:
            command = np.array([value for key, value in command.items() if key.startswith("M")])

        return command
    
    def run_simulation_step(self):
        command = self.generate_command()
        self.env.act("auv0", command)
        state = self.env.tick()
        state_data = state["state"]
        print(f"Command: {command} \nState Data: {state_data}")

    def run(self):
        with self.env:
            while True:
                self.run_simulation_step()

if __name__ == "__main__":
    manual_db = ManualDatabase()
    manual_db.run()