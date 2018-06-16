import os
import shutil

aruco_folder_name = "aruco_pillar"

os.makedirs("result");
for index in range(1024):
    root_folder_name = "result/" + aruco_folder_name + "_" + str(index);

    os.makedirs(root_folder_name);
    os.makedirs(root_folder_name + "/materials");
    os.makedirs(root_folder_name + "/materials/scripts");
    os.makedirs(root_folder_name + "/materials/textures");
    os.makedirs(root_folder_name + "/materials/textures/aruco");

    modelConfigFile = open(root_folder_name + "/model.config","w");

    modelConfigFile.write('<?xml version="1.0"?>\n');
    modelConfigFile.write("<model>\n");
    modelConfigFile.write(" <name> Aruco Pillar " + str(index) + " </name>\n");
    modelConfigFile.write(" <version>1.0</version>\n");
    modelConfigFile.write(' <sdf version="1.4">model.sdf</sdf>\n');
    modelConfigFile.write('\n');
    modelConfigFile.write(' <author>\n');
    modelConfigFile.write('     <name>Tristan de BLAUWE</name>\n');
    modelConfigFile.write('     <email>tdb.work@outlook.fr</email>\n');
    modelConfigFile.write(' </author>\n');
    modelConfigFile.write('');
    modelConfigFile.write(' <description>\n');
    modelConfigFile.write('     Pillier où se trouve le code aruco ' + str(index) + "\n");
    modelConfigFile.write(' </description>\n');
    modelConfigFile.write("</model>\n");

    modelConfigFile.close();

    modelSDFFile = open(root_folder_name + "/model.sdf","w");

    modelSDFFile.write('<?xml version="1.0"?>\n');
    modelSDFFile.write('<sdf version="1.4">\n');
    modelSDFFile.write('<model name="aruco_pillar_'+ str(index) + '">\n');
    modelSDFFile.write('    <pose>0 0 0 0 0 0</pose>\n');
    modelSDFFile.write('    <static>true</static>\n');
    modelSDFFile.write('		<link name="pillar">\n');
    modelSDFFile.write('		<pose>0 0 0.2 0 0 0</pose>\n');
    modelSDFFile.write('		<inertial>\n');
    modelSDFFile.write('			<mass>1.0</mass>\n');
    modelSDFFile.write('			<inertia> <!-- inertias are tricky to compute -->\n');
    modelSDFFile.write('				<!-- http://gazebosim.org/tutorials?tut=inertia&cat=build_robot -->\n');
    modelSDFFile.write('				<ixx>0.083</ixx>       <!-- for a box: ixx = 0.083 * mass * (y*y + z*z) -->\n');
    modelSDFFile.write('				<ixy>0.0</ixy>         <!-- for a box: ixy = 0 -->\n');
    modelSDFFile.write('				<ixz>0.0</ixz>         <!-- for a box: ixz = 0 -->\n');
    modelSDFFile.write('				<iyy>0.083</iyy>       <!-- for a box: iyy = 0.083 * mass * (x*x + z*z) -->\n');
    modelSDFFile.write('				<iyz>0.0</iyz>         <!-- for a box: iyz = 0 -->\n');
    modelSDFFile.write('				<izz>0.083</izz>       <!-- for a box: izz = 0.083 * mass * (x*x + y*y) -->\n');
    modelSDFFile.write('			</inertia>\n');
    modelSDFFile.write('		</inertial>\n');
    modelSDFFile.write('		<collision name="collision">\n');
    modelSDFFile.write('			<geometry>\n');
    modelSDFFile.write('			  <box>\n');
    modelSDFFile.write('				<size>0.15 0.15 0.40</size>\n');
    modelSDFFile.write('			  </box>\n');
    modelSDFFile.write('			</geometry>\n');
    modelSDFFile.write('			</collision>\n');
    modelSDFFile.write('		<visual name="visual">\n');
    modelSDFFile.write('			<geometry>\n');
    modelSDFFile.write('			  <box>\n');
    modelSDFFile.write('				<size>0.15 0.15 0.40</size>\n');
    modelSDFFile.write('			  </box>\n');
    modelSDFFile.write('			</geometry>\n');
    modelSDFFile.write('		</visual>\n');
    modelSDFFile.write('	</link>\n');
    modelSDFFile.write('		<link name="aruco_marker">\n');
    modelSDFFile.write('		<pose>0.076 0 0.30 0 0 0</pose>\n');
    modelSDFFile.write('		<inertial>\n');
    modelSDFFile.write('			<mass>0.1</mass>\n');
    modelSDFFile.write('			<inertia> <!-- inertias are tricky to compute -->\n');
    modelSDFFile.write('				<!-- http://gazebosim.org/tutorials?tut=inertia&cat=build_robot -->\n');
    modelSDFFile.write('				<ixx>0.083</ixx>       <!-- for a box: ixx = 0.083 * mass * (y*y + z*z) -->\n');
    modelSDFFile.write('				<ixy>0.0</ixy>         <!-- for a box: ixy = 0 -->\n');
    modelSDFFile.write('				<ixz>0.0</ixz>         <!-- for a box: ixz = 0 -->\n');
    modelSDFFile.write('				<iyy>0.083</iyy>       <!-- for a box: iyy = 0.083 * mass * (x*x + z*z) -->\n');
    modelSDFFile.write('				<iyz>0.0</iyz>         <!-- for a box: iyz = 0 -->\n');
    modelSDFFile.write('				<izz>0.083</izz>       <!-- for a box: izz = 0.083 * mass * (x*x + y*y) -->\n');
    modelSDFFile.write('			</inertia>\n');
    modelSDFFile.write('		</inertial>\n');
    modelSDFFile.write('		<collision name="collision">\n');
    modelSDFFile.write('			<geometry>\n');
    modelSDFFile.write('			  <box>\n');
    modelSDFFile.write('				<size>0.15 0.15 1e-5</size>\n');
    modelSDFFile.write('			  </box>\n');
    modelSDFFile.write('			</geometry>\n');
    modelSDFFile.write('			<pose>0 0 0 0 -1.5708 0</pose>\n');
    modelSDFFile.write('		</collision>\n');
    modelSDFFile.write('		<visual name="visual">\n');
    modelSDFFile.write('			<geometry>\n');
    modelSDFFile.write('			  <box>\n');
    modelSDFFile.write('				<size>0.15 0.15 1e-5</size>\n');
    modelSDFFile.write('			  </box>\n');
    modelSDFFile.write('			</geometry>\n');
    modelSDFFile.write('			<pose>0 0 0 0 -1.5708 0</pose>\n');
    modelSDFFile.write('			<material>\n');
    modelSDFFile.write('				<script>\n');
    modelSDFFile.write('					<uri>model://aruco_pillar_' + str(index) + '/materials/scripts</uri>\n');
    modelSDFFile.write('					<uri>model://aruco_pillar_' + str(index) + '/materials/textures</uri>\n');
    modelSDFFile.write('					<name>aruco_pillar_' + str(index) + '/Diffuse</name>\n');
    modelSDFFile.write('				</script>\n');
    modelSDFFile.write('				<ambient>1 1 1 1</ambient>\n');
    modelSDFFile.write('				<diffuse>1 1 1 1</diffuse>\n');
    modelSDFFile.write('				<specular>0 0 0 1</specular>\n');
    modelSDFFile.write('				<emissive>1 1 1 0</emissive>\n');
    modelSDFFile.write('				<shader type="vertex">\n');
    modelSDFFile.write('					<normal_map>__default__</normal_map>\n');
    modelSDFFile.write('				</shader>\n');
    modelSDFFile.write('			</material>\n');
    modelSDFFile.write('		</visual>\n');
    modelSDFFile.write('	</link>\n');
    modelSDFFile.write('</model>\n');
    modelSDFFile.write('</sdf>\n');

    modelSDFFile.close();

    modelScriptFile = open(root_folder_name + "/materials/scripts/aruco_marker_" + str(index) + ".material","w");

    modelScriptFile.write("material aruco_pillar_" + str(index) + "/Diffuse\n");
    modelScriptFile.write("{\n");
    modelScriptFile.write("    receive_shadows off\n");
    modelScriptFile.write("    technique\n");
    modelScriptFile.write("    {\n");
    modelScriptFile.write("        pass\n");
    modelScriptFile.write("        {\n");
    modelScriptFile.write("            texture_unit\n");
    modelScriptFile.write("            {\n");
    modelScriptFile.write("                texture aruco/" + str(index) + ".png\n");
    modelScriptFile.write("                filtering anistropic\n");
    modelScriptFile.write("                max_anisotropy 16\n");
    modelScriptFile.write("            }\n");
    modelScriptFile.write("        }\n");
    modelScriptFile.write("    }\n");
    modelScriptFile.write("}\n");

    modelScriptFile.close();

    if index < 10:
        shutil.copy("Aruco_png/marker_000" + str(index) + ".png", root_folder_name + "/materials/textures/aruco/" + str(index) + ".png");
    elif index < 100:
        shutil.copy("Aruco_png/marker_00" + str(index) + ".png", root_folder_name + "/materials/textures/aruco/" + str(index) + ".png");
    elif index < 1000:
        shutil.copy("Aruco_png/marker_0" + str(index) + ".png", root_folder_name + "/materials/textures/aruco/" + str(index) + ".png");
    else:
        shutil.copy("Aruco_png/marker_" + str(index) + ".png", root_folder_name + "/materials/textures/aruco/" + str(index) + ".png");
