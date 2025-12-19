import time
import argparse
import subprocess
from auvtrainer import __version__


def _manual_db_process():
    subprocess.run(["uvicorn", "auvtrainer.db.app:app", "--reload"])
    subprocess.run(["python", "-m", "auvtrainer.controls.keyboard_input"])
    subprocess.run(["python", "-m", "auvtrainer.simulation.manual_database"])


def main():
    parser = argparse.ArgumentParser(description="AUVTrainer Command Line Interface")
    parser.add_argument('--version', action='version', version=f'AUVTrainer {__version__}')
    parser.add_argument('--simulation_type', type=str, choices=['manual_db'], help='Type of simulation to run')

    args = parser.parse_args()
    
    if args.simulation_type == 'manual_db':
        _manual_db_process()
    else:
        print("Please specify a valid simulation type. Use --help for more information.")