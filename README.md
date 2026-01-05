# AUVTrainer
A repository using the Holoocean simulator to train reinforcement learning models to control various underwater vehicles. 

## Setup (AUVTainer + HoloOcean)

```bash
git submodule update --init --recursive

python -m venv venv
source venv/bin/activate
python -m pip install -e .

cd HoloOcean/client
python -m pip install .

python
>>> from holoocean import packagemanager
>>> packagemanager.install("Ocean")

# Copy the initialization SQL file, change pythonX.X to your Python version
cp ../src/auvtrainer/db/initialization_sql.sql venv/lib/pythonX.X/site-packages/auvtrainer/db/initialization_sql.sql
```

## Running the Manual Keyboard Control Simulation

```bash
bash scripts/manual.sh
```
