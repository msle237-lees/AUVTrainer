# AUVTrainer
A repository using the Holoocean simulator to train reinforcement learning models to control various underwater vehicles. 

## Setup (HoloOcean)

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -e .

cd HoloOcean/client
python -m pip install .

python
>>> from holoocean import packagemanager
>>> packagemanager.install("Ocean")
