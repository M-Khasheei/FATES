import gmsh
import ogstools.msh2vtu
import pyvista as pv
from openpyxl import Workbook
import os
import vtuIO
import pandas as pd
from doepy import build
import numpy as np
import ogs6py.ogs
import matplotlib.pyplot as plt
import math
import shutil
import statsmodels.formula.api as smf
import statsmodels.api as sm
import sys
from scipy.stats import t
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QStackedWidget,
                             QMessageBox, QHBoxLayout, QSizePolicy)
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
plt.rcParams.update({'font.size': 16})

"""
==========================================================
Files & Directories
==========================================================
"""

directory = '/path/to/this/directory'
ogs_exe = '/path/to/ogs/bin'
project = 'ATES.prj'
factors_list = ['Injection_Temperature', 'Porosity', 'Injection_Volume', 'Horizontal_Permeability',
                'Vertical_Permeability', 'Aquifer_thickness', 'Thermal_conductivity', 'Specific_heat_capacity',
                'longitudinal_dispersivity', 'transverse_dispersivity', 'Temperature_gradient', 'Pressure_gradient',
                'Dip_Angle', 'Groundwater_flow', 'Dummy_Variable']

"""
==========================================================
Input Parameter Ranges
==========================================================
"""

water_SHC = 4100                        # specific heat capacity in j/kg/C
water_rho = 1000                        # density of water in kg/m^3
prod_start = 154                        # day
prod_end = 232                          # day
inj_start = 0                           # day
inj_end = 153                           # day
time_step = 1                           # days
porosity_max = 10                       # ---
porosity_min = 30                       # ---
horizontal_permeability_max = 500       # mD
horizontal_permeability_min = 50        # mD
vertical_permeability_max = 50          # mD
vertical_permeability_min = 1           # mD
Tinj_max = 90                           # degC
Tinj_min = 60                           # degC
inj_volume_min = 300000                 # m^3
inj_volume_max = 600000                 # m^3
h_min = 30                              # m
h_max = 60                              # m
thermal_conductivity_min = 1.8          # W/m/K
thermal_conductivity_max = 2.5          # W/m/K
specific_heat_capacity_min = 600        # J/kg/K
specific_heat_capacity_max = 900        # J/kg/K
longitudinal_dispersivity_min = 10      # cm
longitudinal_dispersivity_max = 5000    # cm
transverse_dispersivity_min = 1         # cm
transverse_dispersivity_max = 100       # cm
T_gradient_min = 30                     # degC Per km
T_gradient_max = 40                     # degC Per km
p_gradient_min = 100                    # bar Per km
p_gradient_max = 150                    # bar Per km
dip_min = 0                             # deg
dip_max = 15                            # deg
groundwater_min = 0                     # m/year
groundwater_max = 10                    # m/year
dummy_min = -1                          # ---
dummy_max = 1                           # ---
inj_time = inj_end - inj_start          # days
prod_time = prod_end - prod_start       # days
aquifer_depth = 850                     # m
cap_thickness = 60                      # m
T_surface = 13                          # degC
inj_T = 30                              # degC
n_z = 1                                 # number of cells in z direction

"""
==========================================================
Screening Design
==========================================================
"""

design = build.lhs(
    d={'Tinj': [Tinj_min, Tinj_max],
       'phi': [porosity_min, porosity_max],
       'Vinj': [inj_volume_min, inj_volume_max],
       'k_xy': [horizontal_permeability_min, horizontal_permeability_max],
       'k_z': [vertical_permeability_min, vertical_permeability_max],
       'h': [h_min, h_max],
       'TC': [thermal_conductivity_min, thermal_conductivity_max],
       'SHC': [specific_heat_capacity_min, specific_heat_capacity_max],
       'T_gradient': [T_gradient_min, T_gradient_max],
       'p_gradient': [p_gradient_min, p_gradient_max],
       'dip': [dip_min, dip_max],
       'l_alpha': [longitudinal_dispersivity_min, longitudinal_dispersivity_max],
       't_alpha': [transverse_dispersivity_min, transverse_dispersivity_max],
       'gwf': [groundwater_min, groundwater_max],
       'dummy': [dummy_min, dummy_max]}, num_samples=50
)

"""
==========================================================
Result csv File Initiation
==========================================================
"""

out_csv = Workbook()
result_sheet = out_csv.worksheets[0]
result_sheet['A1'] = 'Experiment'
result_sheet['B1'] = 'Temperature (degC)'
result_sheet['C1'] = 'Porosity'
result_sheet['D1'] = 'Injection_Volume (m^3)'
result_sheet['E1'] = 'Horizontal Permeability (mD)'
result_sheet['F1'] = 'Vertical Permeability (mD)'
result_sheet['G1'] = 'Aquifer_thickness (m)'
result_sheet['H1'] = 'Thermal_conductivity (W/m/K)'
result_sheet['I1'] = 'Specific_heat_capacity (J/kg/K)'
result_sheet['J1'] = 'Aquifer_longitudinal_dispersivity (m)'
result_sheet['K1'] = 'Aquifer_transverse_dispersivity (m)'
result_sheet['L1'] = 'Temperature_gradient (degC/m)'
result_sheet['M1'] = 'Pressure_gradient (bar/m)'
result_sheet['N1'] = 'Dip_Angle'
result_sheet['O1'] = 'Groundwater_flow (m/year)'
result_sheet['P1'] = 'Dummy_Variable'
result_sheet['Q1'] = 'E_out2 (Gwh)'
result_sheet['R1'] = 'E_out3 (Gwh)'
result_sheet['S1'] = 'E_out4 (Gwh)'
result_sheet['T1'] = 'E_out5 (Gwh)'
result_sheet['U1'] = 'E_out6 (Gwh)'
result_sheet['V1'] = 'E_out7 (Gwh)'
result_sheet['W1'] = 'E_out8 (Gwh)'
result_sheet['X1'] = 'E_out9 (Gwh)'
result_sheet['Y1'] = 'E_out10 (Gwh)'
result_sheet['Z1'] = 'E_in2 (Gwh)'
result_sheet['AA1'] = 'E_in3 (Gwh)'
result_sheet['AB1'] = 'E_in4 (Gwh)'
result_sheet['AC1'] = 'E_in5 (Gwh)'
result_sheet['AD1'] = 'E_in6 (Gwh)'
result_sheet['AE1'] = 'E_in7 (Gwh)'
result_sheet['AF1'] = 'E_in8 (Gwh)'
result_sheet['AG1'] = 'E_in9 (Gwh)'
result_sheet['AH1'] = 'E_in10 (Gwh)'
result_sheet['AI1'] = 'Net_E2 (Gwh)'
result_sheet['AJ1'] = 'Net_E3 (Gwh)'
result_sheet['AK1'] = 'Net_E4 (Gwh)'
result_sheet['AL1'] = 'Net_E5 (Gwh)'
result_sheet['AM1'] = 'Net_E6 (Gwh)'
result_sheet['AN1'] = 'Net_E7 (Gwh)'
result_sheet['AO1'] = 'Net_E8 (Gwh)'
result_sheet['AP1'] = 'Net_E9 (Gwh)'
result_sheet['AQ1'] = 'Net_E10 (Gwh)'
result_sheet['AR1'] = 'COP2'
result_sheet['AS1'] = 'COP3'
result_sheet['AT1'] = 'COP4'
result_sheet['AU1'] = 'COP5'
result_sheet['AV1'] = 'COP6'
result_sheet['AW1'] = 'COP7'
result_sheet['AX1'] = 'COP8'
result_sheet['AY1'] = 'COP9'
result_sheet['AZ1'] = 'COP10'
result_sheet['BA1'] = 'HRF2'
result_sheet['BB1'] = 'HRF3'
result_sheet['BC1'] = 'HRF4'
result_sheet['BD1'] = 'HRF5'
result_sheet['BE1'] = 'HRF6'
result_sheet['BF1'] = 'HRF7'
result_sheet['BG1'] = 'HRF8'
result_sheet['BH1'] = 'HRF9'
result_sheet['BI1'] = 'HRF10'

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
    porosity = row['phi'] / 100
    inj_volume = row['Vinj']
    permeability = f" {row['k_xy'] * 9.869e-16} 0 0 0 {row['k_xy'] * 9.869e-16} 0 0 0 {row['k_z'] * 9.869e-16}"
    h = row['h']
    TC = row['TC'] * 3600 * 24  # Scaled for daily time-steps
    SHC = row['SHC']
    l_alpha = row['l_alpha'] / 100
    t_alpha = row['t_alpha'] / 100
    T_gradient = row['T_gradient']
    p_gradient = row['p_gradient']
    dip = row['dip']
    gwf = row['gwf'] / 365
    dummy = row['dummy']
    # Constrain for ensuring higher injection temperature than aquifer temperature
    if temperature > T_surface + (T_gradient * (aquifer_depth + h + cap_thickness) / 1000) + 5:
        print(f"Row {index}: Temperature = {temperature}, Porosity = {porosity}, Injection Volume = {inj_volume}, "
              f"Permeability = {permeability}, Aquifer_thickness = {h}, Thermal_conductivity = {TC},"
              f"Specific_heat_capacity = {SHC}, Aquifer_longitudinal_dispersivity = {l_alpha}, "
              f"Aquifer_transverse_dispersivity = {t_alpha}, Temperature_gradient = {T_gradient},"
              f" Pressure_gradient = {p_gradient}, Dip angle = {dip}, Groundwater_flow = {gwf}, Dummy = {dummy}")

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
        new_data.replace_medium_property_value(mediumid=0, name="porosity", value=porosity)
        new_data.replace_medium_property_value(mediumid=0, name="permeability", value=permeability)
        new_data.replace_medium_property_value(mediumid=0, name="thermal_longitudinal_dispersivity", value=l_alpha)
        new_data.replace_medium_property_value(mediumid=0, name="thermal_transversal_dispersivity", value=t_alpha)
        new_data.replace_phase_property_value(mediumid=0, phase="Solid", name="thermal_conductivity", value=TC)
        new_data.replace_phase_property_value(mediumid=0, phase="Solid", name="specific_heat_capacity", value=SHC)
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
        new_data.replace_parameter_value(name="p_top_aquifer", value=p_gradient * 100000 * aquifer_depth / 1000)
        new_data.replace_parameter_value(name="p_bottom_aquifer",
                                         value=p_gradient * 100000 * (aquifer_depth + h) / 1000)
        new_data.replace_parameter_value(name="groundwater_flow_left", value=round(gwf, 5))
        new_data.replace_parameter_value(name="groundwater_flow_right", value=round(-1 * gwf, 5))
        new_data.write_input()

        # ----------------------------------------------------
        # Creating Geometry In Each Folder using Gmsh
        # ----------------------------------------------------
        lc = 100
        dip_rad = math.radians(dip)
        c = math.cos(dip_rad)  # deviation in x direction
        s = math.sin(dip_rad)  # deviation in y direction
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

        # Creating 3D body_Upper section non-discretized (1-cell model)
        gmsh.model.geo.extrude([(2, 1)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 2)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 3)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 4)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 5)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 6)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 7)], 0, 0, cap_thickness, [1], [], True)
        gmsh.model.geo.extrude([(2, 8)], 0, 0, cap_thickness, [1], [], True)

        # Creating 3D body_Lower section non-discretized (1-cell model)
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

        # Creating Boundary lines and surfacses
        left = gmsh.model.addPhysicalGroup(2, [401])
        gmsh.model.setPhysicalName(2, left, "left")

        right = gmsh.model.addPhysicalGroup(2, [493])
        gmsh.model.setPhysicalName(2, right, "right")

        top_aquifer = gmsh.model.geo.addPhysicalGroup(0, [1, 2])
        gmsh.model.setPhysicalName(0, top_aquifer, "top_aquifer")

        bottom_aquifer = gmsh.model.geo.addPhysicalGroup(0, [238, 242])
        gmsh.model.setPhysicalName(0, bottom_aquifer, "bottom_aquifer")

        top = gmsh.model.geo.addPhysicalGroup(2, [586, 564, 542, 608, 630, 652, 696, 674])
        gmsh.model.setPhysicalName(2, top, "top")

        bottom = gmsh.model.geo.addPhysicalGroup(2, [718, 784, 762, 740, 806, 850, 828, 872])
        gmsh.model.setPhysicalName(2, bottom, "bottom")

        # Creating source/sink lines
        hot_source = gmsh.model.addPhysicalGroup(1, [214])
        gmsh.model.setPhysicalName(1, hot_source, "hot_source")

        cold_source = gmsh.model.addPhysicalGroup(1, [282])
        gmsh.model.setPhysicalName(1, cold_source, "cold_source")

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

        # Converting .msh file to .vtu files for OGS
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
        result_sheet[f'C{index + 2}'] = porosity
        result_sheet[f'D{index + 2}'] = inj_volume
        result_sheet[f'E{index + 2}'] = row['k_xy']
        result_sheet[f'F{index + 2}'] = row['k_z']
        result_sheet[f'G{index + 2}'] = h
        result_sheet[f'H{index + 2}'] = TC / 86400
        result_sheet[f'I{index + 2}'] = SHC
        result_sheet[f'J{index + 2}'] = l_alpha
        result_sheet[f'K{index + 2}'] = t_alpha
        result_sheet[f'L{index + 2}'] = T_gradient / 1000
        result_sheet[f'M{index + 2}'] = p_gradient / 1000
        result_sheet[f'N{index + 2}'] = dip
        result_sheet[f'O{index + 2}'] = gwf
        result_sheet[f'P{index + 2}'] = dummy

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

        result_sheet[f'Q{index + 2}'] = total_prod_list[1]
        result_sheet[f'R{index + 2}'] = total_prod_list[2]
        result_sheet[f'S{index + 2}'] = total_prod_list[3]
        result_sheet[f'T{index + 2}'] = total_prod_list[4]
        result_sheet[f'U{index + 2}'] = total_prod_list[5]
        result_sheet[f'V{index + 2}'] = total_prod_list[6]
        result_sheet[f'W{index + 2}'] = total_prod_list[7]
        result_sheet[f'X{index + 2}'] = total_prod_list[8]
        result_sheet[f'Y{index + 2}'] = total_prod_list[9]
        result_sheet[f'Z{index + 2}'] = total_cons_prod_list[1] + total_cons_inj_list[1]
        result_sheet[f'AA{index + 2}'] = total_cons_prod_list[2] + total_cons_inj_list[2]
        result_sheet[f'AB{index + 2}'] = total_cons_prod_list[3] + total_cons_inj_list[3]
        result_sheet[f'AC{index + 2}'] = total_cons_prod_list[4] + total_cons_inj_list[4]
        result_sheet[f'AD{index + 2}'] = total_cons_prod_list[5] + total_cons_inj_list[5]
        result_sheet[f'AE{index + 2}'] = total_cons_prod_list[6] + total_cons_inj_list[6]
        result_sheet[f'AF{index + 2}'] = total_cons_prod_list[7] + total_cons_inj_list[7]
        result_sheet[f'AG{index + 2}'] = total_cons_prod_list[8] + total_cons_inj_list[8]
        result_sheet[f'AH{index + 2}'] = total_cons_prod_list[9] + total_cons_inj_list[9]
        result_sheet[f'AI{index + 2}'] = result_sheet[f'Q{index + 2}'].value - result_sheet[f'Z{index + 2}'].value
        result_sheet[f'AJ{index + 2}'] = result_sheet[f'R{index + 2}'].value - result_sheet[f'AA{index + 2}'].value
        result_sheet[f'AK{index + 2}'] = result_sheet[f'S{index + 2}'].value - result_sheet[f'AB{index + 2}'].value
        result_sheet[f'AL{index + 2}'] = result_sheet[f'T{index + 2}'].value - result_sheet[f'AC{index + 2}'].value
        result_sheet[f'AM{index + 2}'] = result_sheet[f'U{index + 2}'].value - result_sheet[f'AD{index + 2}'].value
        result_sheet[f'AN{index + 2}'] = result_sheet[f'V{index + 2}'].value - result_sheet[f'AE{index + 2}'].value
        result_sheet[f'AO{index + 2}'] = result_sheet[f'W{index + 2}'].value - result_sheet[f'AF{index + 2}'].value
        result_sheet[f'AP{index + 2}'] = result_sheet[f'X{index + 2}'].value - result_sheet[f'AG{index + 2}'].value
        result_sheet[f'AQ{index + 2}'] = result_sheet[f'Y{index + 2}'].value - result_sheet[f'AH{index + 2}'].value

        result_sheet[f'AR{index + 2}'] = result_sheet[f'Q{index + 2}'].value / result_sheet[f'Z{index + 2}'].value
        result_sheet[f'AS{index + 2}'] = result_sheet[f'R{index + 2}'].value / result_sheet[f'AA{index + 2}'].value
        result_sheet[f'AT{index + 2}'] = result_sheet[f'S{index + 2}'].value / result_sheet[f'AB{index + 2}'].value
        result_sheet[f'AU{index + 2}'] = result_sheet[f'T{index + 2}'].value / result_sheet[f'AC{index + 2}'].value
        result_sheet[f'AV{index + 2}'] = result_sheet[f'U{index + 2}'].value / result_sheet[f'AD{index + 2}'].value
        result_sheet[f'AW{index + 2}'] = result_sheet[f'V{index + 2}'].value / result_sheet[f'AE{index + 2}'].value
        result_sheet[f'AX{index + 2}'] = result_sheet[f'W{index + 2}'].value / result_sheet[f'AF{index + 2}'].value
        result_sheet[f'AY{index + 2}'] = result_sheet[f'X{index + 2}'].value / result_sheet[f'AG{index + 2}'].value
        result_sheet[f'AZ{index + 2}'] = result_sheet[f'Y{index + 2}'].value / result_sheet[f'AH{index + 2}'].value

        result_sheet[f'BA{index + 2}'] = total_prod_list[1] / total_inj_list[1]
        result_sheet[f'BB{index + 2}'] = total_prod_list[2] / total_inj_list[2]
        result_sheet[f'BC{index + 2}'] = total_prod_list[3] / total_inj_list[3]
        result_sheet[f'BD{index + 2}'] = total_prod_list[4] / total_inj_list[4]
        result_sheet[f'BE{index + 2}'] = total_prod_list[5] / total_inj_list[5]
        result_sheet[f'BF{index + 2}'] = total_prod_list[6] / total_inj_list[6]
        result_sheet[f'BG{index + 2}'] = total_prod_list[7] / total_inj_list[7]
        result_sheet[f'BH{index + 2}'] = total_prod_list[8] / total_inj_list[8]
        result_sheet[f'BI{index + 2}'] = total_prod_list[9] / total_inj_list[9]

        out_csv.save(directory + '/result.xlsx')

"""
==========================================================
Statistical Analysis GUI
in this section a graphical user interface will be generated
to use the data in '/result.xlsx' to perform screening analysis
for the desired response in a desired operational year
==========================================================
"""


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

        # Label for response type
        response_label = QLabel("Please select the response")
        response_label.setFont(QFont("Arial", 14))
        response_label.setAlignment(Qt.AlignCenter)
        response_label.setStyleSheet("color: white;")
        layout.addWidget(response_label, alignment=Qt.AlignCenter)

        # Dropdown for response type
        self.response_dropdown = QComboBox()
        self.response_dropdown.addItems(["Heat Recovery Factor", "Heat Production"])
        self.response_dropdown.setFixedWidth(1000)
        self.response_dropdown.setStyleSheet("""
                    QComboBox {
                        padding: 5px;
                        border: 1px solid #004d73;
                        border-radius: 4px;
                        min-width: 100px;
                        text-align: center;
                        background-color: #003c54;
                        color: white;
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
        layout.addWidget(self.response_dropdown, alignment=Qt.AlignCenter)

        # Label for year of operation
        year_label = QLabel("Please select the desired year for analysis")
        year_label.setFont(QFont("Arial", 14))
        year_label.setAlignment(Qt.AlignCenter)
        year_label.setStyleSheet("color: white;")
        layout.addWidget(year_label, alignment=Qt.AlignCenter)

        # Dropdown for year of operation
        self.year_dropdown = QComboBox()
        self.year_dropdown.addItems([f"{year}" for year in range(2, 11)])  # Years 2 to 10
        self.year_dropdown.setFixedWidth(300)
        self.year_dropdown.setStyleSheet("""
                    QComboBox {
                        padding: 5px;
                        border: 1px solid #004d73;
                        border-radius: 4px;
                        min-width: 100px;
                        text-align: center;
                        background-color: #003c54;
                        color: white;
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
        layout.addWidget(self.year_dropdown, alignment=Qt.AlignCenter)

        # Analyze button
        analyze_button = QPushButton("Analyze")
        analyze_button.setFont(QFont("Arial", 14))
        analyze_button.setFixedWidth(300)
        analyze_button.setStyleSheet("background-color: #004d73; color: white;")
        analyze_button.clicked.connect(self.perform_analysis)
        layout.addWidget(analyze_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def perform_analysis(self):
        selected_response = self.response_dropdown.currentText()
        selected_year = self.year_dropdown.currentText()

        if selected_response == "Heat Recovery Factor":
            column_name = f"HRF{selected_year}"
        else:
            column_name = f"E_out{selected_year} (Gwh)"

        self.analyze_data(column_name)

    def analyze_data(self, column_name):
        excel_file_path = os.path.join(directory, 'result.xlsx')
        df = pd.read_excel(excel_file_path, sheet_name=0)

        # Find column index by name
        if column_name not in df.columns:
            QMessageBox.critical(self, "Error", f"Column '{column_name}' not found in data.")
            return

        column_index = df.columns.get_loc(column_name)
        response_data = np.array(df.iloc[:, column_index])

        # Continue with the analysis (reusing your existing logic)
        matrix_arr = df.iloc[:, 1:-45]
        matrix_design = matrix_arr.to_numpy()
        matrix_design = pd.DataFrame(matrix_design, columns=factors_list)
        response = pd.DataFrame({'Response': response_data})
        matrix_design = sm.add_constant(matrix_design)
        matrix_design['Response'] = response
        data = matrix_design

        # Perform OLS regression
        model = smf.ols(formula='response ~ Injection_Temperature + Porosity + Injection_Volume + Horizontal_Permeability'
                                ' + Vertical_Permeability + Aquifer_thickness + Thermal_conductivity + Specific_heat_capacity'
                                ' + longitudinal_dispersivity + transverse_dispersivity + Temperature_gradient'
                                ' + Pressure_gradient + Dip_Angle + Groundwater_flow + Dummy_Variable', data=data).fit()

        print(model.summary())

        # Plot Q-Q and residual plots
        self.plot_qq(model)
        self.plot_residuals(model)
        self.plot_pareto_chart(model, response_data)

    def plot_qq(self, model):
        fig, ax = plt.subplots(figsize=(8, 6))
        sm.qqplot(model.resid, line='s', ax=ax)
        ax.set_xlabel('Theoretical Quantiles')
        ax.set_ylabel('Sample Quantiles')
        plt.show()

    def plot_residuals(self, model):
        y_pred = model.fittedvalues
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(y_pred, model.resid, s=20, c='blue', alpha=0.6)
        ax.axhline(y=0, color='red', linestyle='--', linewidth=2)
        ax.set_xlabel('Predicted Values')
        ax.set_ylabel('Residuals')
        plt.show()

    def plot_pareto_chart(self, model, response_data):
        obs = len(response_data)
        pred = len(model.params) - 1
        deg_free = obs - pred - 1
        alpha = 0.05
        t_critical = t.ppf(1 - alpha / 2, deg_free)
        print("t-critical:", t_critical)

        standardized_coeffs = model.params[1:] / model.bse[1:]
        sorted_coeffs = standardized_coeffs.abs().sort_values(ascending=True)

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.barh(sorted_coeffs.index, sorted_coeffs, color='blue', alpha=0.7)
        ax.axvline(x=t_critical, color='red', linestyle='--', label=f't-critical = {t_critical:.4f}')

        significant_level = model.params[model.pvalues == 0.05]
        for level in significant_level:
            ax.axvline(x=abs(level), color='red', linestyle='--')

        ax.set_ylabel('Parameter')
        ax.set_xlabel('t_value')
        ax.legend()
        plt.tight_layout()
        plt.show()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Heat Recovery Factor Tool")
        self.setFixedSize(1000, 500)
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

        # Add the pages to the QStackedWidget
        self.stacked_widget.addWidget(self.splash_screen)  # Logo screen
        self.stacked_widget.addWidget(self.landing_page)  # Index 1

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