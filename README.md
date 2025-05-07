# FATES
Feasibility Assessment of Thermal Energy Storage

FATES is a Python-based tool developed to analyze the performance of Thermal Energy Storage (TES) systems. It serves two primary purposes:

## 🔍 1. Screening
FATES identifies the key input variables—also known as *heavy hitters*—that have the most significant influence on TES system performance. This helps streamline the focus of analysis and optimization efforts.

## ⚡ 2. Proxy Modeling
Once the heavy hitters are identified, FATES builds a lightweight, predictive *proxy model* that approximates the output of the full numerical simulator. This model is highly efficient and allows FATES to:
- Generate results in a fraction of a second.
- Run large-scale **Monte Carlo simulations** quickly and accurately.

[![Attention] The screening.py and proxy.py files should be run in different folder otherwise the results will be replaced. ATES.prj and Logo1.jpeg should also be available in each folder at time of run.

Installation Instructions

1. Install Python
- Download and install Python (tested with Python 3.10).
- Ensure Python is added to the system PATH during installation.

2. Install OpenGeoSys (OGS)
- Download and install OpenGeoSys from the official website.
- Activate the HT (Heat Transport) process in OGS.
- Installation tutorial: https://www.opengeosys.org/docs/tutorials/advancing-glacier/

3. Install Required Python Packages
Run the following command to install all necessary packages:

pip install VTUinterface numpy matplotlib pandas statsmodels scipy gmsh ogstools pyvista openpyxl  doepy ogs6py scikit-learn PyQt5 seaborn sys

4. Update Script Directories
- Locate the Python script for FATES.
- Replace the Python file directory (`directory`) with the actual directory path of the script.
- Replace the OGS executable (`ogs_exe`) with the path to the OGS executable file.

5. Run the Python Script (first screening.py to identify the heavy hitters. then replacing the heavy hitters as new parameters in the proxy.py. Finally, run the proxy.py to build the proxy model and generate GUI for Monte Carlo Simulation)

# After Simulations
- Once all simulations are completed, the software will:
  - Generate an Excel file containing the results.
  - Display a GUI for further analysis and visualisation.
