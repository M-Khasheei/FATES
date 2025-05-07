import gmsh
import ogstools.msh2vtu
import pyvista as pv
import os
import vtuIO
import pandas as pd
import numpy as np
import ogs6py.ogs
import matplotlib.pyplot as plt
import math
import shutil
import subprocess
import seaborn as sns
import sys
from vtk import *
from openpyxl import Workbook
from doepy import build

from sklearn.preprocessing import MinMaxScaler, PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
                             QStackedWidget, QMessageBox, QFormLayout, QHBoxLayout, QSizePolicy)
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve

from scipy.stats import truncnorm, uniform, lognorm, triang, expon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
plt.rcParams.update({'font.size': 16})

"""
==========================================================
Files & Directories
==========================================================
"""

directory = '/path/to/this/directory'
ogs_exe = '/path/to/ogs/bin'
project = 'ATES.prj'
factors_list = ['Injection_Temperature', 'Injection_Volume', 'longitudinal_dispersivity', 'Temperature_gradient']

"""
==========================================================
Input Parameter Ranges
==========================================================
"""

water_SHC = 4100                       # specific heat capacity in j/kg/C
water_rho = 1000                       # density of water in kg/m^3
prod_start = 154                       # day
prod_end = 232                         # day
inj_start = 0                          # day
inj_end = 153                          # day
time_step = 1                          # days
Tinj_max = 90                          # degC
Tinj_min = 60                          # degC
inj_volume_min = 300000                # m^3
inj_volume_max = 600000                # m^3
longitudinal_dispersivity_min = 10     # cm
longitudinal_dispersivity_max = 5000   # cm
T_gradient_min = 30                    # degC Per km
T_gradient_max = 40                    # degC Per km
p_gradient = 100                       # bar/km
inj_time = inj_end - inj_start         # days
prod_time = prod_end - prod_start      # days
aquifer_depth = 850                    # m
h = 50                                 # m
dip = 0                                # degree
cap_thickness = 60                     # m
T_surface = 13                         # degC
inj_T = 30                             # degC
n_z = 1                                # number of cells in z direction

"""
==========================================================
Screening Design
==========================================================
"""
np.random.seed(14)
design = build.lhs(
    d={'Tinj': [Tinj_min, Tinj_max],
       'Vinj': [inj_volume_min, inj_volume_max],
       'T_gradient': [T_gradient_min, T_gradient_max],
       'l_alpha': [longitudinal_dispersivity_min, longitudinal_dispersivity_max]}, num_samples=50
)

print(design)

"""
==========================================================
Result csv File
==========================================================
"""

out_csv = Workbook()
result_sheet = out_csv.worksheets[0]
result_sheet['A1'] = 'Experiment'
result_sheet['B1'] = 'Temperature (degC)'
result_sheet['C1'] = 'Injection_Volume (m^3)'
result_sheet['D1'] = 'Aquifer_longitudinal_dispersivity (m)'
result_sheet['E1'] = 'Temperature_gradient (degC/m)'
result_sheet['F1'] = 'E_out2 (Gwh)'
result_sheet['G1'] = 'E_out3 (Gwh)'
result_sheet['H1'] = 'E_out4 (Gwh)'
result_sheet['I1'] = 'E_out5 (Gwh)'
result_sheet['J1'] = 'E_out6 (Gwh)'
result_sheet['K1'] = 'E_out7 (Gwh)'
result_sheet['L1'] = 'E_out8 (Gwh)'
result_sheet['M1'] = 'E_out9 (Gwh)'
result_sheet['N1'] = 'E_out10 (Gwh)'
result_sheet['O1'] = 'E_in2 (Gwh)'
result_sheet['P1'] = 'E_in3 (Gwh)'
result_sheet['Q1'] = 'E_in4 (Gwh)'
result_sheet['R1'] = 'E_in5 (Gwh)'
result_sheet['S1'] = 'E_in6 (Gwh)'
result_sheet['T1'] = 'E_in7 (Gwh)'
result_sheet['U1'] = 'E_in8 (Gwh)'
result_sheet['V1'] = 'E_in9 (Gwh)'
result_sheet['W1'] = 'E_in10 (Gwh)'
result_sheet['X1'] = 'Net_E2 (Gwh)'
result_sheet['Y1'] = 'Net_E3 (Gwh)'
result_sheet['Z1'] = 'Net_E4 (Gwh)'
result_sheet['AA1'] = 'Net_E5 (Gwh)'
result_sheet['AB1'] = 'Net_E6 (Gwh)'
result_sheet['AC1'] = 'Net_E7 (Gwh)'
result_sheet['AD1'] = 'Net_E8 (Gwh)'
result_sheet['AE1'] = 'Net_E9 (Gwh)'
result_sheet['AF1'] = 'Net_E10 (Gwh)'
result_sheet['AG1'] = 'COP2'
result_sheet['AH1'] = 'COP3'
result_sheet['AI1'] = 'COP4'
result_sheet['AJ1'] = 'COP5'
result_sheet['AK1'] = 'COP6'
result_sheet['AL1'] = 'COP7'
result_sheet['AM1'] = 'COP8'
result_sheet['AN1'] = 'COP9'
result_sheet['AO1'] = 'COP10'
result_sheet['AP1'] = 'HRF2'
result_sheet['AQ1'] = 'HRF3'
result_sheet['AR1'] = 'HRF4'
result_sheet['AS1'] = 'HRF5'
result_sheet['AT1'] = 'HRF6'
result_sheet['AU1'] = 'HRF7'
result_sheet['AV1'] = 'HRF8'
result_sheet['AW1'] = 'HRF9'
result_sheet['AX1'] = 'HRF10'

"""
==========================================================
Main Loop
it creates folder for each experiment, creates geometry in
folder, copies the main project file in each folder and add
the new parameters, run ogs in each folder separately and 
save the output results in each folder and in the main csv.
==========================================================
"""

for index, row in design.iterrows():
    # ----------------------------------------------------
    # Reading Data From Design
    # ----------------------------------------------------
    temperature = row['Tinj']
    inj_volume = row['Vinj']
    l_alpha = row['l_alpha'] / 100
    T_gradient = row['T_gradient']
    if temperature > T_surface + (T_gradient * (aquifer_depth + h + cap_thickness) / 1000) + 5:
        print(f"Row {index}: Temperature = {temperature}, Injection Volume = {inj_volume}, "
              f"Aquifer_longitudinal_dispersivity = {l_alpha}, Temperature_gradient = {T_gradient},")

        # ----------------------------------------------------
        # Creating New Folders And Copy .prj File In Each
        # ----------------------------------------------------
        folder_path = os.path.join(directory, str(index))
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder '{str(index)}' created in {directory}")
        else:
            print(f"Folder '{str(index)}' already exists in {directory}")
        project_copy = shutil.copy(directory + "/" + project, folder_path)
        project_name, project_extension = os.path.splitext(os.path.basename(project_copy))
        new_project_name = project_name + str(index) + project_extension
        os.rename(folder_path + "/" + project, folder_path + "/" + new_project_name)
        if not os.path.exists(os.path.join(folder_path, 'out' + str(index))):
            os.makedirs(os.path.join(folder_path, 'out' + str(index)))

        # ----------------------------------------------------
        # Replacing New Parameters In New .prj Files
        # ----------------------------------------------------
        new_data = ogs6py.ogs.OGS(INPUT_FILE=directory + "/" + project,
                                  PROJECT_FILE=folder_path + "/" + new_project_name)
        new_data.replace_medium_property_value(mediumid=0, name="thermal_longitudinal_dispersivity", value=l_alpha)
        inj_rate = round(inj_volume / inj_time / h, 5)
        prod_rate = round(inj_volume * (-1) / prod_time / h, 5)
        new_data.replace_parameter_value(name="hot_source_in", value=inj_rate)
        new_data.replace_parameter_value(name="hot_source_out", value=prod_rate)
        new_data.replace_parameter_value(name="cold_source_in", value=-1 * prod_rate)
        new_data.replace_parameter_value(name="cold_source_out", value=-1 * inj_rate)
        new_data.replace_parameter_value(name="t_hot_inj", value=temperature)
        new_data.replace_parameter_value(name="t_top",
                                         value=T_surface + (T_gradient * (aquifer_depth - cap_thickness) / 1000))
        new_data.replace_parameter_value(name="t_bottom",
                                         value=T_surface + (T_gradient * (aquifer_depth + h + cap_thickness) / 1000))
        new_data.write_input()

        # ----------------------------------------------------
        # Creating Geometry In Each Folder
        # ----------------------------------------------------
        lc = 100
        dip_rad = math.radians(dip)
        c = math.cos(dip_rad)
        s = math.sin(dip_rad)
        gmsh.initialize()

        # Hot well
        gmsh.model.geo.addPoint(-250 * c, 0, (-1 * aquifer_depth) - 250 * s, 0.2, 0)
        gmsh.model.geo.addPoint(-249.5 * c, 0.5, (-1 * aquifer_depth) - 249.5 * s, 0.5, 101)
        gmsh.model.geo.addPoint(-249.5 * c, -0.5, (-1 * aquifer_depth) - 249.5 * s, 0.5, 102)
        gmsh.model.geo.addPoint(-250.5 * c, -0.5, (-1 * aquifer_depth) - 250.5 * s, 0.5, 103)
        gmsh.model.geo.addPoint(-250.5 * c, 0.5, (-1 * aquifer_depth) - 250.5 * s, 0.5, 104)

        gmsh.model.geo.addCircleArc(101, 0, 102, 101)
        gmsh.model.geo.addCircleArc(102, 0, 103, 102)
        gmsh.model.geo.addCircleArc(103, 0, 104, 103)
        gmsh.model.geo.addCircleArc(104, 0, 101, 104)

        gmsh.model.geo.addLine(0, 101, 105)
        gmsh.model.geo.addLine(0, 102, 106)
        gmsh.model.geo.addLine(0, 103, 107)
        gmsh.model.geo.addLine(0, 104, 108)

        gmsh.model.geo.addCurveLoop([105, 101, -106], 101)
        gmsh.model.geo.addCurveLoop([106, 102, -107], 102)
        gmsh.model.geo.addCurveLoop([107, 103, -108], 103)
        gmsh.model.geo.addCurveLoop([108, 104, -105], 104)

        gmsh.model.geo.addPlaneSurface([101], 101)
        gmsh.model.geo.addPlaneSurface([102], 102)
        gmsh.model.geo.addPlaneSurface([103], 103)
        gmsh.model.geo.addPlaneSurface([104], 104)

        # Cold well
        gmsh.model.geo.addPoint(250 * c, 0, (-1 * aquifer_depth) + 250 * s, 0.2, 200)
        gmsh.model.geo.addPoint(249.5 * c, 0.5, (-1 * aquifer_depth) + 249.5 * s, 0.5, 201)
        gmsh.model.geo.addPoint(249.5 * c, -0.5, (-1 * aquifer_depth) + 249.5 * s, 0.5, 202)
        gmsh.model.geo.addPoint(250.5 * c, -0.5, (-1 * aquifer_depth) + 250.5 * s, 0.5, 203)
        gmsh.model.geo.addPoint(250.5 * c, 0.5, (-1 * aquifer_depth) + 250.5 * s, 0.5, 204)

        gmsh.model.geo.addCircleArc(201, 200, 202, 201)
        gmsh.model.geo.addCircleArc(202, 200, 203, 202)
        gmsh.model.geo.addCircleArc(203, 200, 204, 203)
        gmsh.model.geo.addCircleArc(204, 200, 201, 204)

        gmsh.model.geo.addLine(200, 201, 205)
        gmsh.model.geo.addLine(200, 202, 206)
        gmsh.model.geo.addLine(200, 203, 207)
        gmsh.model.geo.addLine(200, 204, 208)

        gmsh.model.geo.addCurveLoop([206, -201, -205], 201)
        gmsh.model.geo.addCurveLoop([207, -202, -206], 202)
        gmsh.model.geo.addCurveLoop([208, -203, -207], 203)
        gmsh.model.geo.addCurveLoop([205, -204, -208], 204)

        gmsh.model.geo.addPlaneSurface([201], 201)
        gmsh.model.geo.addPlaneSurface([202], 202)
        gmsh.model.geo.addPlaneSurface([203], 203)
        gmsh.model.geo.addPlaneSurface([204], 204)

        # Aquifer around hot well
        gmsh.model.geo.addPoint(0, 250, (-1 * aquifer_depth), lc, 1)
        gmsh.model.geo.addPoint(0, -250, (-1 * aquifer_depth), lc, 2)
        gmsh.model.geo.addPoint(-500 * c, -250, (-1 * aquifer_depth) - 500 * s, lc, 3)
        gmsh.model.geo.addPoint(-500 * c, 250, (-1 * aquifer_depth) - 500 * s, lc, 4)

        gmsh.model.geo.addLine(1, 2, 1)
        gmsh.model.geo.addLine(2, 3, 2)
        gmsh.model.geo.addLine(3, 4, 3)
        gmsh.model.geo.addLine(4, 1, 4)
        gmsh.model.geo.addLine(101, 1, 5)
        gmsh.model.geo.addLine(102, 2, 6)
        gmsh.model.geo.addLine(103, 3, 7)
        gmsh.model.geo.addLine(104, 4, 8)

        gmsh.model.geo.addCurveLoop([5, 1, -6, -101], 1)
        gmsh.model.geo.addCurveLoop([6, 2, -7, -102], 2)
        gmsh.model.geo.addCurveLoop([7, 3, -8, -103], 3)
        gmsh.model.geo.addCurveLoop([8, 4, -5, -104], 4)

        gmsh.model.geo.addPlaneSurface([1], 1)
        gmsh.model.geo.addPlaneSurface([2], 2)
        gmsh.model.geo.addPlaneSurface([3], 3)
        gmsh.model.geo.addPlaneSurface([4], 4)

        # Aquifer around cold well
        gmsh.model.geo.addPoint(500 * c, -250, (-1 * aquifer_depth) + 500 * s, lc, 5)
        gmsh.model.geo.addPoint(500 * c, 250, (-1 * aquifer_depth) + 500 * s, lc, 6)

        gmsh.model.geo.addLine(2, 5, 9)
        gmsh.model.geo.addLine(5, 6, 10)
        gmsh.model.geo.addLine(6, 1, 11)
        gmsh.model.geo.addLine(201, 1, 12)
        gmsh.model.geo.addLine(202, 2, 13)
        gmsh.model.geo.addLine(203, 5, 14)
        gmsh.model.geo.addLine(204, 6, 15)

        gmsh.model.geo.addCurveLoop([201, 13, -1, -12], 5)
        gmsh.model.geo.addCurveLoop([202, 14, -9, -13], 6)
        gmsh.model.geo.addCurveLoop([203, 15, -10, -14], 7)
        gmsh.model.geo.addCurveLoop([204, 12, -11, -15], 8)

        gmsh.model.geo.addPlaneSurface([5], 5)
        gmsh.model.geo.addPlaneSurface([6], 6)
        gmsh.model.geo.addPlaneSurface([7], 7)
        gmsh.model.geo.addPlaneSurface([8], 8)

        # Creating 3D body with extruding all surfaces
        gmsh.model.geo.extrude([(2, 101)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 102)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 103)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 104)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 201)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 202)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 203)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 204)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 1)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 2)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 3)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 4)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 5)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 6)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 7)], 0, 0, -1 * h, [n_z], [], True)
        gmsh.model.geo.extrude([(2, 8)], 0, 0, -1 * h, [n_z], [], True)

        # Creating 3D body_Upper section non-discretized
        gmsh.model.geo.extrude([(2, 1)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 2)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 3)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 4)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 5)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 6)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 7)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 8)], 0, 0, cap_thickness, [1], [], True)

        # Creating 3D body_Lower section non-discretized
        gmsh.model.geo.extrude([(2, 388)], 0, 0, -1 * cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 366)], 0, 0, -1 * cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 432)], 0, 0, -1 * cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 410)], 0, 0, -1 * cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 454)], 0, 0, -1 * cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 520)], 0, 0, -1 * cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 476)], 0, 0, -1 * cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 498)], 0, 0, -1 * cap_thickness, [1], [], True)

        # Creating Main Domains
        aquifer = gmsh.model.addPhysicalGroup(3, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16])
        gmsh.model.setPhysicalName(3, aquifer, "aquifer")

        upper_layer = gmsh.model.addPhysicalGroup(3, [17, 18, 19, 20, 21, 22, 23, 24])
        gmsh.model.setPhysicalName(3, upper_layer, "upper_layer")

        lower_layer = gmsh.model.addPhysicalGroup(3, [25, 26, 27, 28, 29, 30, 31, 32])
        gmsh.model.setPhysicalName(3, lower_layer, "lower_layer")

        left = gmsh.model.addPhysicalGroup(2, [401])
        gmsh.model.setPhysicalName(2, left, "left")

        right = gmsh.model.addPhysicalGroup(2, [493])
        gmsh.model.setPhysicalName(2, right, "right")

        hot_source = gmsh.model.addPhysicalGroup(1, [214])
        gmsh.model.setPhysicalName(1, hot_source, "hot_source")

        cold_source = gmsh.model.addPhysicalGroup(1, [282])
        gmsh.model.setPhysicalName(1, cold_source, "cold_source")

        top_aquifer = gmsh.model.geo.addPhysicalGroup(0, [1, 2])
        gmsh.model.setPhysicalName(0, top_aquifer, "top_aquifer")

        bottom_aquifer = gmsh.model.geo.addPhysicalGroup(0, [238, 242])
        gmsh.model.setPhysicalName(0, bottom_aquifer, "bottom_aquifer")

        top = gmsh.model.geo.addPhysicalGroup(2, [586, 564, 542, 608, 630, 652, 696, 674])
        gmsh.model.setPhysicalName(2, top, "top")

        bottom = gmsh.model.geo.addPhysicalGroup(2, [718, 784, 762, 740, 806, 850, 828, 872])
        gmsh.model.setPhysicalName(2, bottom, "bottom")

        gmsh.model.geo.synchronize()
        gmsh.model.mesh.setTransfiniteCurve(5, 20, "Progression", 1.21)
        gmsh.model.mesh.setTransfiniteCurve(6, 20, "Progression", 1.21)
        gmsh.model.mesh.setTransfiniteCurve(7, 20, "Progression", 1.21)
        gmsh.model.mesh.setTransfiniteCurve(8, 20, "Progression", 1.21)
        gmsh.model.mesh.setTransfiniteCurve(12, 20, "Progression", 1.21)
        gmsh.model.mesh.setTransfiniteCurve(13, 20, "Progression", 1.21)
        gmsh.model.mesh.setTransfiniteCurve(14, 20, "Progression", 1.21)
        gmsh.model.mesh.setTransfiniteCurve(15, 20, "Progression", 1.21)
        gmsh.model.mesh.setRecombine(1, 5)
        gmsh.model.mesh.setRecombine(1, 6)
        gmsh.model.mesh.setRecombine(1, 7)
        gmsh.model.mesh.setRecombine(1, 8)
        gmsh.model.mesh.setRecombine(1, 12)
        gmsh.model.mesh.setRecombine(1, 13)
        gmsh.model.mesh.setRecombine(1, 14)
        gmsh.model.mesh.setRecombine(1, 15)

        gmsh.model.mesh.generate(3)
        gmsh.write(os.path.join(folder_path, "main.msh"))

        ogstools.msh2vtu.msh2vtu(input_filename=os.path.join(folder_path, "main.msh"),
                                 output_path=folder_path,
                                 output_prefix="",
                                 dim=0,
                                 delz=False,
                                 swapxy=False,
                                 rdcd=True,
                                 ogs=True,
                                 ascii=False,
                                 log_level="DEBUG", )
        gmsh.finalize()

        # ----------------------------------------------------
        # Adding Pressure And Temperature Gradient to Geometry
        # ----------------------------------------------------
        geometry = pv.read(folder_path + '/' + "main_domain.vtu")
        y_coordinates = geometry.points[:, 2]


        def temperature_gradient(y):
            T_top = T_surface + (T_gradient * (aquifer_depth - cap_thickness) / 1000)
            T_bottom = T_surface + (T_gradient * (aquifer_depth + h + cap_thickness) / 1000)
            gradient = T_bottom - (
                    (T_bottom - T_top) * (y - np.min(y_coordinates)) / (np.max(y_coordinates) - np.min(y_coordinates)))
            return gradient


        def pressure_gradient(y):
            p_top = p_gradient * 100000 * (aquifer_depth - cap_thickness) / 1000
            p_bottom = p_gradient * 100000 * (aquifer_depth + h + cap_thickness) / 1000
            gradient = p_bottom - (
                    (p_bottom - p_top) * (y - np.min(y_coordinates)) / (np.max(y_coordinates) - np.min(y_coordinates)))
            return gradient


        temperatures = np.array([temperature_gradient(y) for y in y_coordinates])
        pressures = np.array([pressure_gradient(y) for y in y_coordinates])

        geometry.point_data["T_ref"] = temperatures.reshape(-1, 1)
        geometry.point_data["p_ref"] = pressures.reshape(-1, 1)
        geometry.save(folder_path + '/' + "main_domain.vtu")

        # ----------------------------------------------------
        # Running The Simulator
        # ----------------------------------------------------
        os.chdir(os.path.join(folder_path, 'out' + str(index)))
        simulation = ogs6py.ogs.OGS(INPUT_FILE=folder_path + "/" + new_project_name,
                                    PROJECT_FILE=folder_path + "/" + new_project_name)
        simulation.run_model(path=ogs_exe)

        # ----------------------------------------------------
        # Saving Output Data
        # ----------------------------------------------------
        folder_path = os.path.join(directory, str(index))
        os.chdir(os.path.join(folder_path, 'out' + str(index)))
        dip_rad = math.radians(dip)
        c = math.cos(dip_rad)
        s = math.sin(dip_rad)

        simulation_pvd = vtuIO.PVDIO(filename="ATES.pvd", dim=3)
        hot_point = {}
        for i in range(n_z + 1):
            hot_point[f"pt{i}"] = (-250 * c, 0, (-1 * aquifer_depth) - (i * (h / n_z)) - 250 * s)
        cold_point = {}
        for i in range(n_z + 1):
            cold_point[f"pt{i}"] = (250 * c, 0, (-1 * aquifer_depth) - (i * (h / n_z)) + 250 * s)
        T_result_hot = {}
        T_result_cold = {}
        P_result_hot = {}
        P_result_cold = {}
        times = []
        T_result_hot["Temperature"] = simulation_pvd.read_time_series(fieldname="T", pts=hot_point)
        T_result_cold["Temperature"] = simulation_pvd.read_time_series(fieldname="T", pts=cold_point)
        P_result_hot["Pressure"] = simulation_pvd.read_time_series(fieldname="p", pts=hot_point)
        P_result_cold["Pressure"] = simulation_pvd.read_time_series(fieldname="p", pts=cold_point)
        T_results_hot = [sum(column) / len(column) for column in zip(*T_result_hot["Temperature"].values())]
        T_results_cold = [sum(column) / len(column) for column in zip(*T_result_cold["Temperature"].values())]
        P_results_hot = [sum(column) / len(column) for column in zip(*P_result_hot["Pressure"].values())]
        P_results_cold = [sum(column) / len(column) for column in zip(*P_result_cold["Pressure"].values())]
        for time in simulation_pvd.timesteps:
            times = times + [time]
        out_sheet = out_csv.create_sheet(title=str(index))
        out_sheet['A1'] = 'Time(day)'
        out_sheet['B1'] = 'Hot Well Temperature (degC)'
        out_sheet['C1'] = 'Cold Well Temperature (degC)'
        out_sheet['D1'] = 'Energy Production (Mw)'
        out_sheet['E1'] = 'Energy Production (Gwh)'
        out_sheet['F1'] = 'Hot Well Pressure (Pa)'
        out_sheet['G1'] = 'Cold Well Pressure (Pa)'
        out_sheet['H1'] = 'Energy Consumption (Mw)'
        out_sheet['I1'] = 'Energy Consumption (Gwh)'
        out_sheet['J1'] = 'Temperature Difference (degC)'
        out_sheet['K1'] = 'Energy Stored (Mw)'
        out_sheet['L1'] = 'Energy Stored (Gwh)'
        for i, value in enumerate(times, start=2):
            out_sheet[f'A{i}'] = value
        for i, value in enumerate(T_results_hot, start=2):
            out_sheet[f'B{i}'] = value
        for i, value in enumerate(T_results_cold, start=2):
            out_sheet[f'C{i}'] = value
        for i, value in enumerate(P_results_hot, start=2):
            out_sheet[f'F{i}'] = value
        for i, value in enumerate(P_results_cold, start=2):
            out_sheet[f'G{i}'] = value
        result_sheet[f'A{index + 2}'] = index
        result_sheet[f'B{index + 2}'] = temperature
        result_sheet[f'C{index + 2}'] = inj_volume
        result_sheet[f'D{index + 2}'] = l_alpha
        result_sheet[f'E{index + 2}'] = T_gradient / 1000

        # ----------------------------------------------------
        # Calculating Energy Production & Consumption
        # ----------------------------------------------------
        total_prod_list = []
        total_inj_list = []
        total_cons_prod_list = []
        total_cons_inj_list = []
        sum_deltaT_prod_list = []
        sum_deltaT_inj_list = []
        for year in range(10):
            total_prod = 0
            total_inj = 0
            total_cons_prod = 0
            total_cons_inj = 0
            sum_deltaT_prod = 0
            sum_deltaT_inj = 0
            for cell in out_sheet['A']:
                if (cell.value is not None and isinstance(cell.value, (int, float)) and prod_start + (
                        year * 365) < cell.value <
                        prod_end + (year * 365)):
                    # Energy Production
                    out_sheet[f'D{cell.row}'] = ((out_sheet[f'B{cell.row}'].value - out_sheet[f'C{cell.row}'].value)
                                                 * ((inj_volume / prod_time) / (24 * 3600)) * water_rho * water_SHC /
                                                 1000000)
                    out_sheet[f'E{cell.row}'] = ((out_sheet[f'A{cell.row}'].value - out_sheet[f'A{cell.row - 1}'].value)
                                                 * out_sheet[f'D{cell.row}'].value * 24 / 1000)
                    # Energy Consumption During Production
                    out_sheet[f'H{cell.row}'] = (
                            abs(out_sheet[f'F{cell.row}'].value - out_sheet[f'G{cell.row}'].value) *
                            ((inj_volume / prod_time) / (24 * 3600)) / 0.5 / 1000000)
                    out_sheet[f'I{cell.row}'] = ((out_sheet[f'A{cell.row}'].value - out_sheet[f'A{cell.row - 1}'].value)
                                                 * out_sheet[f'H{cell.row}'].value * 24 / 1000)

                    out_sheet[f'J{cell.row}'] = out_sheet[f'B{cell.row}'].value - out_sheet[f'C{cell.row}'].value

                    total_prod += out_sheet[f'E{cell.row}'].value
                    total_cons_prod += out_sheet[f'I{cell.row}'].value
                    sum_deltaT_prod += out_sheet[f'J{cell.row}'].value
                if (cell.value is not None and isinstance(cell.value, (int, float)) and inj_start + (
                        year * 365) < cell.value <
                        inj_end + (year * 365)):
                    # Energy Consumption During Injection
                    out_sheet[f'H{cell.row}'] = (
                            abs(out_sheet[f'F{cell.row}'].value - out_sheet[f'G{cell.row}'].value) *
                            ((inj_volume / inj_time) / (24 * 3600)) / 0.5 / 1000000)
                    out_sheet[f'I{cell.row}'] = ((out_sheet[f'A{cell.row}'].value - out_sheet[f'A{cell.row - 1}'].value)
                                                 * out_sheet[f'H{cell.row}'].value * 24 / 1000)
                    out_sheet[f'J{cell.row}'] = out_sheet[f'B{cell.row}'].value - out_sheet[f'C{cell.row}'].value

                    # Energy Injection
                    out_sheet[f'K{cell.row}'] = ((out_sheet[f'B{cell.row}'].value - out_sheet[f'C{cell.row}'].value)
                                                 * ((inj_volume / inj_time) / (
                                    24 * 3600)) * water_rho * water_SHC / 1000000)
                    out_sheet[f'L{cell.row}'] = ((out_sheet[f'A{cell.row}'].value - out_sheet[f'A{cell.row - 1}'].value)
                                                 * out_sheet[f'K{cell.row}'].value * 24 / 1000)

                    total_inj += out_sheet[f'L{cell.row}'].value
                    total_cons_inj += out_sheet[f'I{cell.row}'].value
                    sum_deltaT_inj += out_sheet[f'J{cell.row}'].value

            total_prod_list.append(total_prod)
            total_inj_list.append(total_inj)
            total_cons_prod_list.append(total_cons_prod)
            total_cons_inj_list.append(total_cons_inj)
            sum_deltaT_prod_list.append(sum_deltaT_prod)
            sum_deltaT_inj_list.append(sum_deltaT_inj)

        result_sheet[f'F{index + 2}'] = total_prod_list[1]
        result_sheet[f'G{index + 2}'] = total_prod_list[2]
        result_sheet[f'H{index + 2}'] = total_prod_list[3]
        result_sheet[f'I{index + 2}'] = total_prod_list[4]
        result_sheet[f'J{index + 2}'] = total_prod_list[5]
        result_sheet[f'K{index + 2}'] = total_prod_list[6]
        result_sheet[f'L{index + 2}'] = total_prod_list[7]
        result_sheet[f'M{index + 2}'] = total_prod_list[8]
        result_sheet[f'N{index + 2}'] = total_prod_list[9]
        result_sheet[f'O{index + 2}'] = total_cons_prod_list[1] + total_cons_inj_list[1]
        result_sheet[f'P{index + 2}'] = total_cons_prod_list[2] + total_cons_inj_list[2]
        result_sheet[f'Q{index + 2}'] = total_cons_prod_list[3] + total_cons_inj_list[3]
        result_sheet[f'R{index + 2}'] = total_cons_prod_list[4] + total_cons_inj_list[4]
        result_sheet[f'S{index + 2}'] = total_cons_prod_list[5] + total_cons_inj_list[5]
        result_sheet[f'T{index + 2}'] = total_cons_prod_list[6] + total_cons_inj_list[6]
        result_sheet[f'U{index + 2}'] = total_cons_prod_list[7] + total_cons_inj_list[7]
        result_sheet[f'V{index + 2}'] = total_cons_prod_list[8] + total_cons_inj_list[8]
        result_sheet[f'W{index + 2}'] = total_cons_prod_list[9] + total_cons_inj_list[9]
        result_sheet[f'X{index + 2}'] = result_sheet[f'F{index + 2}'].value - result_sheet[f'O{index + 2}'].value
        result_sheet[f'Y{index + 2}'] = result_sheet[f'G{index + 2}'].value - result_sheet[f'P{index + 2}'].value
        result_sheet[f'Z{index + 2}'] = result_sheet[f'H{index + 2}'].value - result_sheet[f'Q{index + 2}'].value
        result_sheet[f'AA{index + 2}'] = result_sheet[f'I{index + 2}'].value - result_sheet[f'R{index + 2}'].value
        result_sheet[f'AB{index + 2}'] = result_sheet[f'J{index + 2}'].value - result_sheet[f'S{index + 2}'].value
        result_sheet[f'AC{index + 2}'] = result_sheet[f'K{index + 2}'].value - result_sheet[f'T{index + 2}'].value
        result_sheet[f'AD{index + 2}'] = result_sheet[f'L{index + 2}'].value - result_sheet[f'U{index + 2}'].value
        result_sheet[f'AE{index + 2}'] = result_sheet[f'M{index + 2}'].value - result_sheet[f'V{index + 2}'].value
        result_sheet[f'AF{index + 2}'] = result_sheet[f'N{index + 2}'].value - result_sheet[f'W{index + 2}'].value

        result_sheet[f'AG{index + 2}'] = result_sheet[f'F{index + 2}'].value / result_sheet[f'O{index + 2}'].value
        result_sheet[f'AH{index + 2}'] = result_sheet[f'G{index + 2}'].value / result_sheet[f'P{index + 2}'].value
        result_sheet[f'AI{index + 2}'] = result_sheet[f'H{index + 2}'].value / result_sheet[f'Q{index + 2}'].value
        result_sheet[f'AJ{index + 2}'] = result_sheet[f'I{index + 2}'].value / result_sheet[f'R{index + 2}'].value
        result_sheet[f'AK{index + 2}'] = result_sheet[f'J{index + 2}'].value / result_sheet[f'S{index + 2}'].value
        result_sheet[f'AL{index + 2}'] = result_sheet[f'K{index + 2}'].value / result_sheet[f'T{index + 2}'].value
        result_sheet[f'AM{index + 2}'] = result_sheet[f'L{index + 2}'].value / result_sheet[f'U{index + 2}'].value
        result_sheet[f'AN{index + 2}'] = result_sheet[f'M{index + 2}'].value / result_sheet[f'V{index + 2}'].value
        result_sheet[f'AO{index + 2}'] = result_sheet[f'N{index + 2}'].value / result_sheet[f'W{index + 2}'].value

        result_sheet[f'AP{index + 2}'] = total_prod_list[1] / total_inj_list[1]
        result_sheet[f'AQ{index + 2}'] = total_prod_list[2] / total_inj_list[2]
        result_sheet[f'AR{index + 2}'] = total_prod_list[3] / total_inj_list[3]
        result_sheet[f'AS{index + 2}'] = total_prod_list[4] / total_inj_list[4]
        result_sheet[f'AT{index + 2}'] = total_prod_list[5] / total_inj_list[5]
        result_sheet[f'AU{index + 2}'] = total_prod_list[6] / total_inj_list[6]
        result_sheet[f'AV{index + 2}'] = total_prod_list[7] / total_inj_list[7]
        result_sheet[f'AW{index + 2}'] = total_prod_list[8] / total_inj_list[8]
        result_sheet[f'AX{index + 2}'] = total_prod_list[9] / total_inj_list[9]

        out_csv.save(directory + '/result.xlsx')

"""
==========================================================
Proxy GUI
in this section a graphical user interface will be generated
to use the data in '/result.xlsx' to build a proxy model and 
perform Monte Carlo Simulation
==========================================================
"""


# Inverse normalized data
def inverse_normalize(scaler, data):
    return scaler.inverse_transform(data)


# Normalizing input dataset
def normalizing_outdataset(X_train_newdata, y_train_newdata):
    scaler_X = MinMaxScaler()
    scaler_Y = MinMaxScaler()

    X_normalized = scaler_X.fit_transform(X_train_newdata)
    y_normalized = scaler_Y.fit_transform(y_train_newdata.values.reshape(-1, 1))
    return X_normalized, y_normalized, scaler_X, scaler_Y


# Reading the data
excel_file_path = 'result.xlsx'
df = pd.read_excel(excel_file_path, sheet_name=0)

# Define the heavy hitters
X = df[['Temperature (degC)', 'Injection_Volume (m^3)', 'Temperature_gradient (degC/m)',
        'Aquifer_longitudinal_dispersivity (m)']]


# Function to train a model based on the year_number
def train_model(year_number):
    # Select the correct HRF and E column based on year_number
    if year_number == 2:
        y_HRF = df['HRF2']
        y_E = df['E_out2 (Gwh)']
    elif year_number == 3:
        y_HRF = df['HRF3']
        y_E = df['E_out3 (Gwh)']
    elif year_number == 4:
        y_HRF = df['HRF4']
        y_E = df['E_out4 (Gwh)']
    elif year_number == 5:
        y_HRF = df['HRF5']
        y_E = df['E_out5 (Gwh)']
    elif year_number == 6:
        y_HRF = df['HRF6']
        y_E = df['E_out6 (Gwh)']
    elif year_number == 7:
        y_HRF = df['HRF7']
        y_E = df['E_out7 (Gwh)']
    elif year_number == 8:
        y_HRF = df['HRF8']
        y_E = df['E_out8 (Gwh)']
    elif year_number == 9:
        y_HRF = df['HRF9']
        y_E = df['E_out9 (Gwh)']
    elif year_number == 10:
        y_HRF = df['HRF10']
        y_E = df['E_out10 (Gwh)']
    else:
        raise ValueError("Invalid year_number. Please choose 2, 3, or 4.")

    # Normalize the dataset
    X_normalized_HRF, y_normalized_HRF, scaler_X_HRF, scaler_Y_HRF = normalizing_outdataset(X, y_HRF)
    X_normalized_E, y_normalized_E, scaler_X_E, scaler_Y_E = normalizing_outdataset(X, y_E)

    # Split the dataset into training and testing sets
    train_size = int(0.7 * len(X))
    X_train_HRF, X_test_HRF = X_normalized_HRF[:train_size], X_normalized_HRF[train_size:]
    y_train_HRF, y_test_HRF = y_normalized_HRF[:train_size], y_normalized_HRF[train_size:]

    X_train_E, X_test_E = X_normalized_E[:train_size], X_normalized_E[train_size:]
    y_train_E, y_test_E = y_normalized_E[:train_size], y_normalized_E[train_size:]

    # Create Polynomial Features
    degree = 2
    poly = PolynomialFeatures(degree=degree, include_bias=False)

    X_train_poly_HRF = poly.fit_transform(X_train_HRF)
    X_test_poly_HRF = poly.transform(X_test_HRF)

    X_train_poly_E = poly.fit_transform(X_train_E)
    X_test_poly_E = poly.transform(X_test_E)

    lin_reg_model_HRF = LinearRegression()
    lin_reg_model_HRF.fit(X_train_poly_HRF, y_train_HRF)

    lin_reg_model_E = LinearRegression()
    lin_reg_model_E.fit(X_train_poly_E, y_train_E)

    y_pred_normalized_HRF = lin_reg_model_HRF.predict(X_test_poly_HRF)
    y_pred_normalized_E = lin_reg_model_E.predict(X_test_poly_E)

    y_pred_HRF = inverse_normalize(scaler_Y_HRF, y_pred_normalized_HRF.reshape(-1, 1))
    y_test_HRF_orig = inverse_normalize(scaler_Y_HRF, y_test_HRF)

    y_pred_E = inverse_normalize(scaler_Y_E, y_pred_normalized_E.reshape(-1, 1))
    y_test_E_orig = inverse_normalize(scaler_Y_E, y_test_E)

    # Evaluate the models
    r2_HRF = r2_score(y_test_HRF_orig, y_pred_HRF)
    rmse_test_HRF = math.sqrt(mean_squared_error(y_test_HRF_orig, y_pred_HRF))

    r2_E = r2_score(y_test_E_orig, y_pred_E)
    rmse_test_E = math.sqrt(mean_squared_error(y_test_E_orig, y_pred_E))

    intercept_HRF = lin_reg_model_HRF.intercept_[0]
    coefficients_HRF = lin_reg_model_HRF.coef_[0]
    feature_names = poly.get_feature_names_out(['A', 'B', 'C', 'D'])

    equation_terms_HRF = [f'{intercept_HRF:.3f}']
    for feature_name, coef in zip(feature_names, coefficients_HRF):
        equation_terms_HRF.append(f'({coef:.3f} * {feature_name})')
    regression_equation_HRF = f'HRF{year_number} = ' + ' + '.join(equation_terms_HRF)

    intercept_E = lin_reg_model_E.intercept_[0]
    coefficients_E = lin_reg_model_E.coef_[0]

    equation_terms_E = [f'{intercept_E:.3f}']
    for feature_name, coef in zip(feature_names, coefficients_E):
        equation_terms_E.append(f'({coef:.3f} * {feature_name})')
    regression_equation_E = f'E{year_number} = ' + ' + '.join(equation_terms_E)

    print(f"Model for HRF{year_number}: {regression_equation_HRF}")
    print(f"R^2 (HRF{year_number}): {r2_HRF}, RMSE: {rmse_test_HRF}")

    print(f"Model for E{year_number}: {regression_equation_E}")
    print(f"R^2 (E{year_number}): {r2_E}, RMSE: {rmse_test_E}")

    return {
        "HRF": {
            "model": lin_reg_model_HRF,
            "equation": regression_equation_HRF,
            "degree": degree,
            "r2": r2_HRF,
            "rmse": rmse_test_HRF
        },
        "E": {
            "model": lin_reg_model_E,
            "equation": regression_equation_E,
            "degree": degree,
            "r2": r2_E,
            "rmse": rmse_test_E
        },
        "poly_features": poly,
        "scalers": {
            "X": scaler_X_HRF,  # Assuming same scaler for both
            "Y_HRF": scaler_Y_HRF,
            "Y_E": scaler_Y_E
        }
    }


# Function to predict HRF
def predict_HRF(injection_temp, injection_vol, temp_gradient, dispersivity, year_number):
    try:
        model_data = train_model(year_number)
        lin_reg_model_HRF = model_data["HRF"]["model"]
        poly = model_data["poly_features"]
        scaler_X = model_data["scalers"]["X"]
        scaler_Y_HRF = model_data["scalers"]["Y_HRF"]
        regression_equation_HRF = model_data["HRF"]["equation"]
        r2_HRF = model_data["HRF"]["r2"]
        rmse_test_HRF = model_data["HRF"]["rmse"]

        input_values = np.array([[injection_temp, injection_vol, temp_gradient, dispersivity]])
        input_normalized = scaler_X.transform(input_values)
        input_poly = poly.transform(input_normalized)
        pred_normalized_HRF = lin_reg_model_HRF.predict(input_poly)
        pred_HRF = inverse_normalize(scaler_Y_HRF, pred_normalized_HRF.reshape(-1, 1))
        return (
            pred_HRF[0, 0],
            regression_equation_HRF,
            model_data["HRF"]["degree"],
            r2_HRF,
            rmse_test_HRF
        )
    except ValueError:
        return None, None, None, None, None  # Return None for all outputs in case of error


def predict_E(injection_temp, injection_vol, temp_gradient, dispersivity, year_number):
    try:
        model_data = train_model(year_number)
        lin_reg_model_E = model_data["E"]["model"]
        poly = model_data["poly_features"]
        scaler_X = model_data["scalers"]["X"]
        scaler_Y_E = model_data["scalers"]["Y_E"]
        regression_equation_E = model_data["E"]["equation"]
        r2_E = model_data["E"]["r2"]
        rmse_test_E = model_data["E"]["rmse"]

        input_values = np.array([[injection_temp, injection_vol, temp_gradient, dispersivity]])
        input_normalized = scaler_X.transform(input_values)
        input_poly = poly.transform(input_normalized)
        pred_normalized_E = lin_reg_model_E.predict(input_poly)
        pred_E = inverse_normalize(scaler_Y_E, pred_normalized_E.reshape(-1, 1))
        return (
            pred_E[0, 0],
            regression_equation_E,
            model_data["E"]["degree"],
            r2_E,
            rmse_test_E
        )
    except ValueError:
        return None, None, None, None, None  # Return None for all outputs in case of error


# Function to calculate mean and standard deviation for normal distribution approximation
def calculate_mean_std(min_val, max_val):
    mean = (min_val + max_val) / 2
    std_dev = (max_val - min_val) / 6  # Approximation
    return mean, std_dev


# Function to generate samples based on distribution type
def get_samples(dist_type, mean, std, min_val, max_val, mode, n_samples):
    if dist_type == 'normal':
        a, b = (min_val - mean) / std, (max_val - mean) / std
        return truncnorm.rvs(a, b, loc=mean, scale=std, size=n_samples)
    elif dist_type == 'uniform':
        return uniform.rvs(loc=min_val, scale=(max_val - min_val), size=n_samples)
    elif dist_type == 'triangular':
        return triang.rvs((mode - min_val) / (max_val - min_val), loc=min_val, scale=(max_val - min_val),
                          size=n_samples)
    elif dist_type == 'exponential':
        lambda_param = 1 / mean  # Lambda is the inverse of the mean
        samples = []
        threshold = 5
        while len(samples) < n_samples:
            # Generate samples in batches, to reduce the need for looping too many times
            new_samples = expon.rvs(scale=1 / lambda_param, size=n_samples)
            # Filter and keep only the samples that are above the threshold
            samples.extend(sample for sample in new_samples if sample > threshold)
        # Only return the required number of samples
        return np.array(samples[:n_samples])
    elif dist_type == 'lognormal':
        shape = std  # shape parameter (σ)
        scale = mean  # scale parameter (exp(μ))
        samples = []
        while len(samples) < n_samples:
            # Generate samples in batches
            new_samples = lognorm.rvs(shape, scale=scale, size=n_samples)
            # Filter and keep only the samples that are within the limits
            valid_samples = new_samples[(new_samples >= min_val) & (new_samples <= max_val)]
            samples.extend(valid_samples)
        return np.array(samples[:n_samples])
    else:
        raise ValueError("Unsupported distribution type")


class SplashScreen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        pixmap = QPixmap('Logo1.jpeg')
        pixmap = pixmap.scaled(900, 900, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background: transparent;")
        layout.addWidget(label)
        self.setLayout(layout)
        self.setStyleSheet("background-color: black;")

        # Set up animation
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(5000)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self.go_to_page1)
        self.animation.start()

    def go_to_page1(self):
        self.stacked_widget.setCurrentIndex(1)

    def go_to_page1(self):
        self.stacked_widget.setCurrentIndex(1)


class LandingPage(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget

        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#001f3f"))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Button, QColor("#004d73"))
        palette.setColor(QPalette.ButtonText, Qt.white)
        self.setPalette(palette)

        layout = QVBoxLayout()
        title_label = QLabel("FATES\n"
                             "(Feasibility Assessment of Thermal Energy Storage)")
        title_label.setFont(QFont("Arial", 40, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white;")  # White title text
        layout.addWidget(title_label)

        # HRF Prediction button
        hrf_button = QPushButton("Predict")
        hrf_button.setFont(QFont("Arial", 14))
        hrf_button.setFixedWidth(300)
        hrf_button.setStyleSheet("background-color: #004d73; color: white;")
        hrf_button.clicked.connect(self.go_to_hrf_prediction)
        layout.addWidget(hrf_button, alignment=Qt.AlignCenter)

        # Trend button
        hrf_button = QPushButton("Trend")
        hrf_button.setFont(QFont("Arial", 14))
        hrf_button.setFixedWidth(300)
        hrf_button.setStyleSheet("background-color: #004d73; color: white;")
        hrf_button.clicked.connect(self.go_to_hrf_trend)
        layout.addWidget(hrf_button, alignment=Qt.AlignCenter)

        # Monte-Carlo Simulation button
        mc_button = QPushButton("Monte-Carlo Simulation")
        mc_button.setFont(QFont("Arial", 14))
        mc_button.setFixedWidth(300)
        mc_button.setStyleSheet("background-color: #004d73; color: white;")
        mc_button.clicked.connect(self.go_to_monte_carlo)
        layout.addWidget(mc_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def go_to_hrf_prediction(self):
        self.stacked_widget.setCurrentIndex(2)

    def go_to_hrf_trend(self):
        self.stacked_widget.setCurrentIndex(3)

    def go_to_monte_carlo(self):
        self.stacked_widget.setCurrentIndex(4)


# Page 2 - Prediction Page
class PredictionApp(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()

        self.stacked_widget = stacked_widget

        self.setWindowTitle("Heat Recovery Factor Predictor")
        self.setGeometry(100, 100, 600, 400)

        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#001f3f"))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Button, QColor("#004d73"))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.Base, QColor("#004d73"))
        palette.setColor(QPalette.Text, Qt.white)
        self.setPalette(palette)

        # Main layout
        main_layout = QVBoxLayout()
        title_label = QLabel("Heat Recovery Factor Prediction")
        title_label.setFont(QFont("Helvetica", 18, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        main_layout.addWidget(title_label)

        # Equation and metrics
        equation_label = QLabel("Regression Equation:")
        equation_label.setFont(QFont("Arial", 14, QFont.Bold))
        equation_label.setStyleSheet("color: white;")
        main_layout.addWidget(equation_label)

        # Create a placeholder for the equation text
        self.equation_text = QLabel("")
        self.equation_text.setFont(QFont("Arial", 12))
        self.equation_text.setStyleSheet("color: white;")
        self.equation_text.setWordWrap(True)
        main_layout.addWidget(self.equation_text)

        self.metrics_label = QLabel("")
        self.metrics_label.setFont(QFont("Arial", 12))
        self.metrics_label.setStyleSheet("color: white;")
        main_layout.addWidget(self.metrics_label)

        input_form_layout = QFormLayout()

        param_info = {
            'A': ('Injection Temperature (degC)', 60, 90),
            'B': ('Injection Volume (m^3)', 300000, 600000),
            'C': ('Temperature Gradient (degC/m)', 0.03, 0.04),
            'D': ('Aquifer Longitudinal Dispersivity (m)', 0.1, 50),
            'E': ('Desired Year', 2, 10)
        }

        self.inputs = {}
        for param, (desc, min_val, max_val) in param_info.items():
            desc_label = QLabel(f'{desc}:')
            desc_label.setFont(QFont("Arial", 12))
            desc_label.setStyleSheet("color: white;")
            entry = QLineEdit()
            entry.setFixedWidth(100)
            entry.setFont(QFont("Arial", 12))
            entry.setStyleSheet("background-color: #004d73; color: white;")
            self.inputs[param] = entry

            min_max_label = QLabel(f"(Min: {min_val}, Max: {max_val})")
            min_max_label.setFont(QFont("Arial", 10))
            min_max_label.setStyleSheet("color: white;")
            param_layout = QVBoxLayout()
            param_layout.addWidget(entry)
            param_layout.addWidget(min_max_label)

            input_form_layout.addRow(desc_label, param_layout)

        main_layout.addLayout(input_form_layout)

        # Predict button
        predict_button = QPushButton("Predict")
        predict_button.setFixedWidth(100)
        predict_button.setFont(QFont("Arial", 12))
        predict_button.setStyleSheet("background-color: #004d73; color: white;")
        predict_button.clicked.connect(self.predict)
        main_layout.addWidget(predict_button, alignment=Qt.AlignCenter)

        self.result_label = QLabel("")
        self.result_label.setFont(QFont("Arial", 12))
        self.result_label.setStyleSheet("color: white;")
        main_layout.addWidget(self.result_label)

        # Back button
        back_button = QPushButton("Back")
        back_button.setFixedWidth(100)
        back_button.setFont(QFont("Arial", 12))
        back_button.setStyleSheet("background-color: #004d73; color: white;")
        back_button.clicked.connect(self.go_back)
        main_layout.addWidget(back_button, alignment=Qt.AlignCenter)

        self.setLayout(main_layout)

    def predict(self):
        try:
            # Retrieve the input values from the form
            injection_temp = float(self.inputs['A'].text())
            injection_vol = float(self.inputs['B'].text())
            temp_gradient = float(self.inputs['C'].text())
            dispersivity = float(self.inputs['D'].text())
            year_number = int(self.inputs['E'].text())

            # Call the predict_HRF function
            pred_HRF, regression_equation_HRF, degree_HRF, r2_HRF, rmse_test_HRF = predict_HRF(
                injection_temp, injection_vol, temp_gradient, dispersivity, year_number
            )

            # Call the predict_E function
            pred_E, regression_equation_E, degree_E, r2_E, rmse_test_E = predict_E(
                injection_temp, injection_vol, temp_gradient, dispersivity, year_number
            )

            # Initialize result messages
            result_message = ""
            equation_message = ""
            metrics_message = ""

            # Display the results for HRF
            if pred_HRF is not None:
                result_message += f"Predicted HRF: {pred_HRF:.3f}\n"
                equation_message += f"HRF Equation: {regression_equation_HRF}\n"
                metrics_message += f"HRF Degree: {degree_HRF}\nR²: {r2_HRF:.3f}\nRMSE: {rmse_test_HRF:.3f}\n"
            else:
                result_message += "Invalid input for HRF. Please enter valid numbers.\n"

            # Display the results for E
            if pred_E is not None:
                result_message += f"Predicted E: {pred_E:.3f}\n"
                equation_message += f"E Equation: {regression_equation_E}\n"
                metrics_message += f"E Degree: {degree_E}\nR²: {r2_E:.3f}\nRMSE: {rmse_test_E:.3f}\n"
            else:
                result_message += "Invalid input for E. Please enter valid numbers.\n"

            # Update the labels with the results
            self.result_label.setText(result_message.strip())
            self.equation_text.setText(equation_message.strip())
            self.metrics_label.setText(metrics_message.strip())

        except ValueError:
            self.result_label.setText("Invalid input. Please enter valid numbers.")

    def go_back(self):
        self.stacked_widget.setCurrentIndex(1)


class PredictionApp1(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()

        self.stacked_widget = stacked_widget

        self.setWindowTitle("Heat Recovery Factor Predictor")
        self.setGeometry(100, 100, 600, 400)

        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#001f3f"))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Button, QColor("#004d73"))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.Base, QColor("#004d73"))
        palette.setColor(QPalette.Text, Qt.white)
        self.setPalette(palette)

        # Main layout
        main_layout = QVBoxLayout()
        title_label = QLabel("Heat Recovery Factor Prediction")
        title_label.setFont(QFont("Helvetica", 18, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        main_layout.addWidget(title_label)

        self.equation_text = QLabel("")
        self.equation_text.setFont(QFont("Arial", 12))
        self.equation_text.setStyleSheet("color: white;")
        self.equation_text.setWordWrap(True)
        main_layout.addWidget(self.equation_text)

        self.metrics_label = QLabel("")
        self.metrics_label.setFont(QFont("Arial", 12))
        self.metrics_label.setStyleSheet("color: white;")
        main_layout.addWidget(self.metrics_label)

        input_form_layout = QFormLayout()
        param_info = {
            'A': ('Injection Temperature (degC)', 60, 90),
            'B': ('Injection Volume (m^3)', 300000, 600000),
            'C': ('Temperature Gradient (degC/m)', 0.03, 0.04),
            'D': ('Aquifer Longitudinal Dispersivity (m)', 0.1, 50),
        }

        self.inputs = {}
        for param, (desc, min_val, max_val) in param_info.items():
            desc_label = QLabel(f'{desc}:')
            desc_label.setFont(QFont("Arial", 12))
            desc_label.setStyleSheet("color: white;")
            entry = QLineEdit()
            entry.setFixedWidth(100)
            entry.setFont(QFont("Arial", 12))
            entry.setStyleSheet("background-color: #004d73; color: white;")
            self.inputs[param] = entry

            min_max_label = QLabel(f"(Min: {min_val}, Max: {max_val})")
            min_max_label.setFont(QFont("Arial", 10))
            min_max_label.setStyleSheet("color: white;")

            param_layout = QVBoxLayout()
            param_layout.addWidget(entry)
            param_layout.addWidget(min_max_label)

            input_form_layout.addRow(desc_label, param_layout)

        main_layout.addLayout(input_form_layout)

        # Plot Graph button
        plot_graph_button = QPushButton("Plot Graph")
        plot_graph_button.setFixedWidth(200)
        plot_graph_button.setFont(QFont("Arial", 12))
        plot_graph_button.setStyleSheet("background-color: #004d73; color: white;")
        plot_graph_button.clicked.connect(self.plot_graph)
        main_layout.addWidget(plot_graph_button, alignment=Qt.AlignCenter)

        self.result_label = QLabel("")
        self.result_label.setFont(QFont("Arial", 12))
        self.result_label.setStyleSheet("color: white;")
        main_layout.addWidget(self.result_label)

        # Back button
        back_button = QPushButton("Back")
        back_button.setFixedWidth(100)
        back_button.setFont(QFont("Arial", 12))
        back_button.setStyleSheet("background-color: #004d73; color: white;")
        back_button.clicked.connect(self.go_back)
        main_layout.addWidget(back_button, alignment=Qt.AlignCenter)

        self.setLayout(main_layout)

    def plot_graph(self):
        try:
            # Retrieve the input values from the form
            injection_temp = float(self.inputs['A'].text())
            injection_vol = float(self.inputs['B'].text())
            temp_gradient = float(self.inputs['C'].text())
            dispersivity = float(self.inputs['D'].text())

            # Call the predict_HRF function for all three years
            preds_hrf = [predict_HRF(injection_temp, injection_vol, temp_gradient, dispersivity, year) for year in
                         [2, 3, 4, 5, 6, 7, 8, 9, 10]]
            preds_e = [predict_E(injection_temp, injection_vol, temp_gradient, dispersivity, year) for year in
                       [2, 3, 4, 5, 6, 7, 8, 9, 10]]

            # Unpack predictions and metrics for HRF
            hrf_results = []
            for pred in preds_hrf:
                if pred[0] is not None:
                    hrf, regression_equation, degree, r2, rmse_test = pred
                    hrf_results.append(hrf)
                else:
                    hrf_results.append(None)

            # Unpack predictions and metrics for E
            e_results = []
            for pred in preds_e:
                if pred[0] is not None:
                    e, regression_equation, degree, r2, rmse_test = pred
                    e_results.append(e)
                else:
                    e_results.append(None)
            print("Gooz", e_results)
            # Display the results for HRF and E
            if all(hrf is not None for hrf in hrf_results) and all(e is not None for e in e_results):
                hrf2, hrf3, hrf4, hrf5, hrf6, hrf7, hrf8, hrf9, hrf10 = hrf_results
                e2, e3, e4, e5, e6, e7, e8, e9, e10 = e_results
                self.result_label.setText(
                    f"Predicted HRF2: {hrf2:.3f}, HRF3: {hrf3:.3f}, HRF4: {hrf4:.3f}, HRF5: {hrf5:.3f},"
                    f" HRF6: {hrf6:.3f}, HRF7: {hrf7:.3f}, HRF8: {hrf8:.3f}, HRF9: {hrf9:.3f}, HRF10: {hrf10:.3f}\n"
                    f"Predicted E2: {e2:.3f}, E3: {e3:.3f}, E4: {e4:.3f}, E5: {e5:.3f}, E6: {e6:.3f}, E7: {e7:.3f},"
                    f" E8: {e8:.3f}, E9: {e9:.3f}, E10: {e10:.3f}"
                )
                self.plot_trend_graph(hrf_results, e_results)
            else:
                self.result_label.setText("Invalid input. Please enter valid numbers.")
        except ValueError:
            self.result_label.setText("No")

    def plot_trend_graph(self, hrf_results, e_results):
        years = [2, 3, 4, 5, 6, 7, 8, 9, 10]

        fig, axs = plt.subplots(1, 2, figsize=(12, 5))

        # Plot HRF
        axs[0].plot(years, hrf_results, marker='o', linestyle='-', color='blue')
        axs[0].set_xlabel('Time (year)')
        axs[0].set_ylabel('HRF')
        axs[0].set_xticks(years)
        axs[0].grid()
        axs[0].legend()

        # Plot E
        axs[1].plot(years, e_results, marker='o', linestyle='-', color='green')
        axs[1].set_xlabel('Time (year)')
        axs[1].set_ylabel('Heat Production (GWh/year)')
        axs[1].set_xticks(years)
        axs[1].grid()
        axs[1].legend()

        plt.tight_layout()
        plt.show()

    def go_back(self):
        self.stacked_widget.setCurrentIndex(1)


class Page2DistributionType(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.dist_types = {}
        self.year_number = None
        self.initUI()

    def initUI(self):
        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#001f3f"))
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

        layout = QVBoxLayout()
        layout.addStretch(1)

        title_label = QLabel("Select Distribution Type for Each Parameter")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white;")
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        self.dist_type_combos = {}
        parameters = ['Injection Temperature (degC)', 'Injection Volume (m^3)', 'Temperature Gradient (degC/m)',
                      'Aquifer Longitudinal Dispersivity (m)']

        for param in parameters:
            label = QLabel(f"{param}:")
            label.setStyleSheet("color: white;")
            combo = QComboBox()
            combo.addItems(["normal", "uniform", "triangular", "exponential", "lognormal"])
            combo.setStyleSheet("""
                QComboBox {
                    padding: 5px;
                    border: 1px solid #004d73;  /* Change border color to match the theme */
                    border-radius: 4px;
                    min-width: 100px;
                    text-align: center;
                    background-color: #003c54;  /* Darker background for combo box */
                    color: white;                /* White text inside combo box */
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 0px; 
                }
                QComboBox::down-arrow {
                    image: none;
                }
            """)
            self.dist_type_combos[param] = combo
            form_layout.addRow(label, combo)

        year_label = QLabel("Desired Year:")
        year_label.setStyleSheet("color: white;")
        self.year_entry = QLineEdit()
        self.year_entry.setPlaceholderText("Enter the desired year")
        self.year_entry.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #004d73;
                border-radius: 4px;
                font-size: 14px;
                background-color: #003c54;
                color: white;
            }
        """)
        form_layout.addRow(year_label, self.year_entry)

        form_container = QWidget()
        form_container.setLayout(form_layout)
        form_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        layout.addWidget(form_container, alignment=Qt.AlignCenter)

        layout.addStretch(1)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)

        # Back Button
        back_button = QPushButton('Back', self)
        back_button.setStyleSheet(
            "QPushButton { background-color: #004d73; color: white; padding: 10px 24px; border: none;"
            " border-radius: 5px; font-size: 16px; } QPushButton:hover { background-color: #003d61; }")
        back_button.clicked.connect(self.go_back)
        button_layout.addWidget(back_button)

        # Next Button
        next_button = QPushButton('Next', self)
        next_button.setStyleSheet(
            "QPushButton { background-color: #004d73; color: white; padding: 10px 24px; border: none;"
            " border-radius: 5px; font-size: 16px; } QPushButton:hover { background-color: #003d61; }")
        next_button.clicked.connect(self.save_and_go)
        button_layout.addWidget(next_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def go_back(self):
        self.stacked_widget.setCurrentIndex(1)

    def save_and_go(self):
        # Save selected distribution types
        self.dist_types = {param: self.dist_type_combos[param].currentText() for param in self.dist_type_combos}

        # Save the entered year
        try:
            self.year_number = int(self.year_entry.text())
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter a valid year number.")
            return

        # Check if Page2Parameters exists and remove it
        if self.stacked_widget.count() >= 3:
            self.stacked_widget.removeWidget(self.stacked_widget.widget(4))

        # Add a new Page2Parameters and pass the year_number
        self.stacked_widget.addWidget(Page2Parameters(self.stacked_widget, self.dist_types, self.year_number))
        self.stacked_widget.setCurrentIndex(4)


class Page2Parameters(QWidget):
    def __init__(self, stacked_widget, dist_types, year_number):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.dist_types = dist_types
        self.year_number = year_number  # Store the passed year number
        self.mean_entries = {}
        self.std_entries = {}
        self.min_entries = {}
        self.max_entries = {}
        self.mode_entries = {}
        self.initUI()

    def initUI(self):
        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#001f3f"))
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

        layout = QVBoxLayout()
        layout.addStretch(1)

        title_label = QLabel("Input Parameter Ranges")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        line_edit_style = """
            QLineEdit {
                padding: 5px;
                border: 1px solid #004d73;
                border-radius: 4px;
                font-size: 14px;
                background-color: #003c54;
                color: white;
            }
        """
        label_style = "color: white; font-size: 14px;"  # White text for labels

        for param, dist_type in self.dist_types.items():
            if dist_type in ["normal"]:
                mean_entry = QLineEdit()
                std_entry = QLineEdit()
                min_entry = QLineEdit()
                max_entry = QLineEdit()
                mean_entry.setStyleSheet(line_edit_style)
                std_entry.setStyleSheet(line_edit_style)
                min_entry.setStyleSheet(line_edit_style)
                max_entry.setStyleSheet(line_edit_style)

                mean_label = QLabel(f"{param} Mean:")
                mean_label.setStyleSheet(label_style)
                std_label = QLabel(f"{param} Std:")
                std_label.setStyleSheet(label_style)
                min_label = QLabel(f"{param} Min:")
                min_label.setStyleSheet(label_style)
                max_label = QLabel(f"{param} Max:")
                max_label.setStyleSheet(label_style)

                form_layout.addRow(mean_label, mean_entry)
                form_layout.addRow(std_label, std_entry)
                form_layout.addRow(min_label, min_entry)
                form_layout.addRow(max_label, max_entry)

                self.mean_entries[param] = mean_entry
                self.std_entries[param] = std_entry
                self.min_entries[param] = min_entry
                self.max_entries[param] = max_entry

            elif dist_type == "triangular":
                min_entry = QLineEdit()
                max_entry = QLineEdit()
                mode_entry = QLineEdit()
                min_entry.setStyleSheet(line_edit_style)
                max_entry.setStyleSheet(line_edit_style)
                mode_entry.setStyleSheet(line_edit_style)

                min_label = QLabel(f"{param} Min:")
                min_label.setStyleSheet(label_style)
                max_label = QLabel(f"{param} Max:")
                max_label.setStyleSheet(label_style)
                mode_label = QLabel(f"{param} Mode:")
                mode_label.setStyleSheet(label_style)

                form_layout.addRow(min_label, min_entry)
                form_layout.addRow(max_label, max_entry)
                form_layout.addRow(mode_label, mode_entry)

                self.min_entries[param] = min_entry
                self.max_entries[param] = max_entry
                self.mode_entries[param] = mode_entry

            elif dist_type == "exponential":
                mean_entry = QLineEdit()
                mean_entry.setStyleSheet(line_edit_style)
                mean_label = QLabel(f"{param} Mean (1/lambda):")
                mean_label.setStyleSheet(label_style)
                form_layout.addRow(mean_label, mean_entry)
                self.mean_entries[param] = mean_entry

            elif dist_type == "lognormal":
                shape_entry = QLineEdit()
                scale_entry = QLineEdit()
                min_entry = QLineEdit()
                max_entry = QLineEdit()
                shape_entry.setStyleSheet(line_edit_style)
                scale_entry.setStyleSheet(line_edit_style)
                min_entry.setStyleSheet(line_edit_style)
                max_entry.setStyleSheet(line_edit_style)

                min_label = QLabel(f"{param} Min:")
                min_label.setStyleSheet(label_style)
                max_label = QLabel(f"{param} Max:")
                max_label.setStyleSheet(label_style)
                shape_label = QLabel(f"{param} Shape (σ):")
                shape_label.setStyleSheet(label_style)
                scale_label = QLabel(f"{param} Scale (exp(μ)):")
                scale_label.setStyleSheet(label_style)

                form_layout.addRow(min_label, min_entry)
                form_layout.addRow(max_label, max_entry)
                form_layout.addRow(shape_label, shape_entry)
                form_layout.addRow(scale_label, scale_entry)

                self.min_entries[param] = min_entry
                self.max_entries[param] = max_entry
                self.mean_entries[param] = shape_entry
                self.std_entries[param] = scale_entry

            else:  # uniform distribution
                min_entry = QLineEdit()
                max_entry = QLineEdit()
                min_entry.setStyleSheet(line_edit_style)
                max_entry.setStyleSheet(line_edit_style)

                min_label = QLabel(f"{param} Min:")
                min_label.setStyleSheet(label_style)
                max_label = QLabel(f"{param} Max:")
                max_label.setStyleSheet(label_style)

                form_layout.addRow(min_label, min_entry)
                form_layout.addRow(max_label, max_entry)

                self.min_entries[param] = min_entry
                self.max_entries[param] = max_entry

        form_container = QWidget()
        form_container.setLayout(form_layout)
        form_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        layout.addWidget(form_container, alignment=Qt.AlignCenter)

        layout.addStretch(1)

        # Button layout and style
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)

        back_button = QPushButton('Back', self)
        back_button.setStyleSheet(
            """
            QPushButton {
                background-color: #004d73;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #003d61;
            }
            """
        )
        back_button.clicked.connect(self.go_back)
        button_layout.addWidget(back_button)

        next_button = QPushButton('Next', self)
        next_button.setStyleSheet(
            """
            QPushButton {
                background-color: #004d73;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #003d61;
            }
            """
        )
        next_button.clicked.connect(self.save_and_calculate)
        button_layout.addWidget(next_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def go_back(self):
        # Remove current and upper pages
        while self.stacked_widget.currentIndex() + 1 < self.stacked_widget.count():
            self.stacked_widget.removeWidget(self.stacked_widget.widget(self.stacked_widget.currentIndex() + 1))
        # Navigate to the previous page
        self.stacked_widget.setCurrentIndex(self.stacked_widget.currentIndex() - 1)

    def save_and_calculate(self):
        ranges = {}

        for param, dist_type in self.dist_types.items():
            try:
                if dist_type == "normal":
                    mean_val = float(self.mean_entries[param].text())
                    std_val = float(self.std_entries[param].text())
                    min_val = float(self.min_entries[param].text())
                    max_val = float(self.max_entries[param].text())
                    ranges[param] = {
                        'mean': mean_val,
                        'std': std_val,
                        'min': min_val,
                        'max': max_val,
                        'dist_type': dist_type,
                        'mode': None
                    }

                elif dist_type == "triangular":
                    min_val = float(self.min_entries[param].text())
                    max_val = float(self.max_entries[param].text())
                    mode_val = float(self.mode_entries[param].text())
                    ranges[param] = {
                        'min': min_val,
                        'max': max_val,
                        'mode': mode_val,
                        'dist_type': dist_type,
                        'mean': None,
                        'std': None
                    }

                elif dist_type == "exponential":
                    mean_val = float(self.mean_entries[param].text())
                    ranges[param] = {
                        'min': None,
                        'max': None,
                        'mode': None,
                        'dist_type': dist_type,
                        'mean': mean_val,
                        'std': None
                    }

                elif dist_type == "lognormal":
                    min_val = float(self.min_entries[param].text())
                    max_val = float(self.max_entries[param].text())
                    shape_val = float(self.mean_entries[param].text())
                    scale_val = float(self.std_entries[param].text())
                    ranges[param] = {
                        'min': min_val,
                        'max': max_val,
                        'mode': None,
                        'dist_type': dist_type,
                        'mean': shape_val,
                        'std': scale_val,
                    }

                elif dist_type == "uniform":
                    min_val = float(self.min_entries[param].text())
                    max_val = float(self.max_entries[param].text())
                    ranges[param] = {
                        'min': min_val,
                        'max': max_val,
                        'dist_type': dist_type,
                        'mean': None,
                        'std': None,
                        'mode': None
                    }

            except ValueError:
                QMessageBox.warning(self, "Input Error", f"Please enter valid values for {param}.")
                return

        # Save ranges and calculate samples
        n_samples = 100000
        samples = {
            param: get_samples(params['dist_type'], params.get('mean'), params.get('std'), params.get('min'),
                               params.get('max'), params.get('mode'), n_samples)
            for param, params in ranges.items()
        }

        HRF_results = []
        E_results = []

        # Loop over input_scenarios and predict HRF and E for each set of inputs
        for T, D, K, H in zip(samples['Injection Temperature (degC)'],
                              samples['Injection Volume (m^3)'],
                              samples['Temperature Gradient (degC/m)'],
                              samples['Aquifer Longitudinal Dispersivity (m)']):
            # Ensure that predict_HRF returns a tuple or list, not a scalar
            HRF_result = predict_HRF(T, D, K, H, self.year_number)
            E_result = predict_E(T, D, K, H, self.year_number)
            HRF_results.append(HRF_result[0])
            E_results.append(E_result[0])

        HRF_results = np.array(HRF_results)
        E_results = np.array(E_results)

        # Update or add Page3 and Page4
        if self.stacked_widget.count() > 4:
            self.stacked_widget.removeWidget(self.stacked_widget.widget(5))
        self.stacked_widget.addWidget(Page3(self.stacked_widget, samples))
        self.stacked_widget.addWidget(Page4(self.stacked_widget, samples, HRF_results, E_results))
        self.stacked_widget.setCurrentIndex(5)


class Page3(QWidget):
    def __init__(self, stacked_widget, samples):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.samples = samples
        self.initUI()

    def initUI(self):
        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#001f3f"))
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

        layout = QVBoxLayout()

        # Create the figure and subplots
        fig1, axs1 = plt.subplots(2, 2, figsize=(10, 8))

        # Plot 1: Injection Temperature (degC)
        axs1[0, 0].hist(self.samples['Injection Temperature (degC)'], bins=100, color='b', alpha=0.7)
        axs1[0, 0].set_xlabel('Injection Temperature (degC)', fontsize=12, color='white')
        axs1[0, 0].set_ylabel('Frequency', fontsize=12, color='white')
        axs1[0, 0].set_xlim(self.samples['Injection Temperature (degC)'].min(),
                            self.samples['Injection Temperature (degC)'].max())
        axs1[0, 0].set_facecolor('white')
        axs1[0, 0].tick_params(colors='white')

        # Plot 2: Injection Volume (m^3)
        axs1[0, 1].hist(self.samples['Injection Volume (m^3)'], bins=100, color='g', alpha=0.7)
        axs1[0, 1].set_xlabel('Injection Volume (m^3)', fontsize=12, color='white')
        axs1[0, 1].set_ylabel('Frequency', fontsize=12, color='white')
        axs1[0, 1].set_xlim(self.samples['Injection Volume (m^3)'].min(),
                            self.samples['Injection Volume (m^3)'].max())
        axs1[0, 1].set_facecolor('white')
        axs1[0, 1].tick_params(colors='white')

        # Plot 3: Temperature Gradient (degC/m)
        axs1[1, 0].hist(self.samples['Temperature Gradient (degC/m)'], bins=100, color='m', alpha=0.7)
        axs1[1, 0].set_xlabel('Temperature Gradient (degC/m)', fontsize=12, color='white')
        axs1[1, 0].set_ylabel('Frequency', fontsize=12, color='white')
        axs1[1, 0].set_xlim(self.samples['Temperature Gradient (degC/m)'].min(),
                            self.samples['Temperature Gradient (degC/m)'].max())
        axs1[1, 0].set_facecolor('white')
        axs1[1, 0].tick_params(colors='white')

        # Plot 4: Aquifer Longitudinal Dispersivity (m)
        axs1[1, 1].hist(self.samples['Aquifer Longitudinal Dispersivity (m)'], bins=100, color='r', alpha=0.7)
        axs1[1, 1].set_xlabel('Aquifer Longitudinal Dispersivity (m)', fontsize=12, color='white')
        axs1[1, 1].set_ylabel('Frequency', fontsize=12, color='white')
        axs1[1, 1].set_xlim(self.samples['Aquifer Longitudinal Dispersivity (m)'].min(),
                            self.samples['Aquifer Longitudinal Dispersivity (m)'].max())
        axs1[1, 1].set_facecolor('white')
        axs1[1, 1].tick_params(colors='white')

        fig1.tight_layout()
        fig1.patch.set_facecolor('#001f3f')

        canvas1 = FigureCanvas(fig1)
        layout.addWidget(canvas1)

        button_layout = QHBoxLayout()

        # Back button
        back_button = QPushButton('Back', self)
        back_button.setStyleSheet(
            """
            QPushButton {
                background-color: #004d73;
                color: white;
                padding: 10px 24px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #003d61;
            }
            """
        )
        back_button.clicked.connect(self.go_back)
        button_layout.addWidget(back_button)

        # Next button
        next_button = QPushButton('Next', self)
        next_button.setStyleSheet(
            """
            QPushButton {
                background-color: #004d73;
                color: white;
                padding: 10px 24px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #003d61;
            }
            """
        )
        next_button.clicked.connect(self.go_to_next)
        button_layout.addWidget(next_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def go_back(self):
        # Remove current and upper pages
        while self.stacked_widget.currentIndex() + 1 < self.stacked_widget.count():
            self.stacked_widget.removeWidget(self.stacked_widget.widget(self.stacked_widget.currentIndex() + 1))
        # Navigate to the previous page
        self.stacked_widget.setCurrentIndex(self.stacked_widget.currentIndex() - 1)

    def go_to_next(self):
        self.stacked_widget.setCurrentIndex(6)


class Page4(QWidget):
    def __init__(self, stacked_widget, samples, HRF_results, E_results):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.samples = samples
        self.HRF_results = HRF_results
        self.E_results = E_results
        self.initUI()

    def initUI(self):
        self.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#001f3f"))
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

        layout = QVBoxLayout()
        fig, (ax_HRF, ax_E) = plt.subplots(1, 2, figsize=(18, 6), gridspec_kw={'wspace': 0.4})

        # -------- Plot HRF Results --------
        sns.histplot(self.HRF_results, kde=True, bins=50, color='g', alpha=0.7, stat="density", ax=ax_HRF)
        ax_HRF.set_facecolor('white')
        ax_HRF.tick_params(colors='black')
        ax_HRF.set_xlabel('Heat Recovery Factor (HRF)', fontsize=12, color='black')
        ax_HRF.set_ylabel('Density', fontsize=12, color='black')

        # Plot cumulative density (ECDF) for HRF
        sorted_HRF = np.sort(self.HRF_results)
        y_values_HRF = np.arange(1, len(sorted_HRF) + 1) / len(sorted_HRF)
        ax_HRF_twin = ax_HRF.twinx()
        ax_HRF_twin.plot(sorted_HRF, y_values_HRF, 'b-', linewidth=2, label='Cumulative Density')
        ax_HRF_twin.set_ylabel('Cumulative Density', color='b')
        ax_HRF_twin.set_ylim(0, 1)
        ax_HRF_twin.tick_params(colors='black')

        # Calculate P10, P50, P90 for HRF
        P10_HRF = np.percentile(self.HRF_results, 10)
        P50_HRF = np.percentile(self.HRF_results, 50)
        P90_HRF = np.percentile(self.HRF_results, 90)

        # Add P10, P50, P90 lines and annotations for HRF
        ax_HRF_twin.axhline(0.10, color='b', linestyle='--', linewidth=1)
        ax_HRF_twin.axhline(0.50, color='b', linestyle='--', linewidth=1)
        ax_HRF_twin.axhline(0.90, color='b', linestyle='--', linewidth=1)
        xmax_HRF = ax_HRF.get_xlim()[1]
        ax_HRF_twin.text(xmax_HRF, 0.10, f'P10: {P10_HRF:.2f}', color='b', va='center', ha='right', backgroundcolor='w')
        ax_HRF_twin.text(xmax_HRF, 0.50, f'P50: {P50_HRF:.2f}', color='b', va='center', ha='right', backgroundcolor='w')
        ax_HRF_twin.text(xmax_HRF, 0.90, f'P90: {P90_HRF:.2f}', color='b', va='center', ha='right', backgroundcolor='w')

        # -------- Plot E Results --------
        sns.histplot(self.E_results, kde=True, bins=50, color='r', alpha=0.7, stat="density", ax=ax_E)
        ax_E.set_facecolor('white')
        ax_E.tick_params(colors='black')
        ax_E.set_xlabel('Heat Production (GWh/year)', fontsize=12, color='black')
        ax_E.set_ylabel('Density', fontsize=12, color='black')

        # Plot cumulative density (ECDF) for E
        sorted_E = np.sort(self.E_results)
        y_values_E = np.arange(1, len(sorted_E) + 1) / len(sorted_E)
        ax_E_twin = ax_E.twinx()
        ax_E_twin.plot(sorted_E, y_values_E, 'b-', linewidth=2, label='Cumulative Density')
        ax_E_twin.set_ylabel('Cumulative Density', color='b')
        ax_E_twin.set_ylim(0, 1)
        ax_E_twin.tick_params(colors='black')

        # Calculate P10, P50, P90 for E
        P10_E = np.percentile(self.E_results, 10)
        P50_E = np.percentile(self.E_results, 50)
        P90_E = np.percentile(self.E_results, 90)

        # Add P10, P50, P90 lines and annotations for E
        ax_E_twin.axhline(0.10, color='b', linestyle='--', linewidth=1)
        ax_E_twin.axhline(0.50, color='b', linestyle='--', linewidth=1)
        ax_E_twin.axhline(0.90, color='b', linestyle='--', linewidth=1)
        xmax_E = ax_E.get_xlim()[1]
        ax_E_twin.text(xmax_E, 0.10, f'P10: {P10_E:.2f} GWh', color='b', va='center', ha='right', backgroundcolor='w')
        ax_E_twin.text(xmax_E, 0.50, f'P50: {P50_E:.2f} GWh', color='b', va='center', ha='right', backgroundcolor='w')
        ax_E_twin.text(xmax_E, 0.90, f'P90: {P90_E:.2f} GWh', color='b', va='center', ha='right', backgroundcolor='w')

        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        button_layout = QHBoxLayout()

        # Back button - navigate to the previous page
        back_button = QPushButton('Back', self)
        back_button.setStyleSheet(
            """
            QPushButton {
                background-color: #004d73;
                color: white;
                padding: 10px 24px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #003d61;
            }
            """
        )
        back_button.clicked.connect(self.go_back)
        button_layout.addWidget(back_button)

        home_button = QPushButton('Go to Home', self)
        home_button.setStyleSheet(
            """
            QPushButton {
                background-color: #004d73;
                color: white;
                padding: 10px 24px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #003d61;
            }
            """
        )
        home_button.clicked.connect(self.go_to_page_0)
        button_layout.addWidget(home_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def go_back(self):
        while self.stacked_widget.currentIndex() + 1 < self.stacked_widget.count():
            self.stacked_widget.removeWidget(self.stacked_widget.widget(self.stacked_widget.currentIndex() + 1))
        self.stacked_widget.setCurrentIndex(self.stacked_widget.currentIndex() - 1)

    def go_to_page_0(self):
        self.stacked_widget.setCurrentIndex(1)


# Main Application Class with Stacked Widget
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Heat Recovery Factor Tool")
        self.setFixedSize(1000, 900)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        top_layout.addWidget(spacer)

        logo_label = QLabel(self)
        pixmap = QPixmap('Logo.jpeg')

        pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignTop | Qt.AlignRight)

        top_layout.addWidget(logo_label)

        main_layout.addLayout(top_layout)
        self.stacked_widget = QStackedWidget()

        # Create instances of the pages
        self.splash_screen = SplashScreen(self.stacked_widget)
        self.landing_page = LandingPage(self.stacked_widget)
        self.prediction_page = PredictionApp(self.stacked_widget)
        self.prediction_page1 = PredictionApp1(self.stacked_widget)
        self.distrbutionType_page = Page2DistributionType(self.stacked_widget)

        # Add the pages to the QStackedWidget
        self.stacked_widget.addWidget(self.splash_screen)  # Logo screen
        self.stacked_widget.addWidget(self.landing_page)  # Index 1
        self.stacked_widget.addWidget(self.prediction_page)  # Index 2
        self.stacked_widget.addWidget(self.prediction_page1)  # Index 3
        self.stacked_widget.addWidget(self.distrbutionType_page)  # Index 4

        # Main layout
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)


# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setStyleSheet("""
            /* Background color for the main window */
            QWidget {
                background-color: #001f3f;  /* Navy blue */
                color: white;  /* White text for all widgets */
            }

            /* Style for labels */
            QLabel {
                color: white;  /* White text */
                font-size: 16px;
            }

            /* Style for QLineEdit and QComboBox */
            QLineEdit, QComboBox {
                padding: 8px;
                border: 1px solid #bdbdbd;
                border-radius: 4px;
                background-color: white;  /* White background for input fields */
                color: #333;  /* Dark text inside input fields */
            }

            /* Button style */
            QPushButton {
                background-color: #B22222;  /* Firebrick red */
                color: white;
                padding: 10px 24px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }

            /* Hover state for buttons */
            QPushButton:hover {
                background-color: #8B0000;  /* Dark red on hover */
            }

            /* Layout margins and padding reset */
            QVBoxLayout, QFormLayout, QHBoxLayout {
                margin: 0;
                padding: 0;
            }
        """)
    window.show()
    sys.exit(app.exec_())
