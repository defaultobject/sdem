from pathlib import Path
import sys
sys.path.append('../../') #project root where experiment_manager is stored
from model_log import main

#Ensure folder structure exists
Path("results/").mkdir(exist_ok=True)
Path("models/").mkdir(exist_ok=True)
Path("models/runs").mkdir(exist_ok=True)

main.run()
