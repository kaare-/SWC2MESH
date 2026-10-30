# processing.py

import vtk
import time
import os
import glob
from multiprocessing import Pool
from datetime import datetime

def read_swc(filename):
    """Reads an SWC file and returns a list of node dictionaries."""
    data = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                # Skip comments and empty lines
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split()
                if len(parts) < 7:
                    continue  # Incomplete line
                n, t, x, y, z, r, p = map(float, parts[:7])
                data.append({
                    'n': int(n),
                    't': int(t),
                    'x': x,
                    'y': y,
                    'z': z,
                    'r': r,
                    'p': int(p)
                })
    except Exception as e:
        return [], f"Error reading SWC file {filename}: {e}"
    return data, None

def create_vtk_from_swc(swc_data):
    """Creates VTK PolyData from SWC data using polylines."""
    points = vtk.vtkPoints()
    radii = vtk.vtkDoubleArray()
    radii.SetName("Radius")
    radii.SetNumberOfComponents(1)

    index_map = {}  # Map SWC node ID to VTK point index

    # Add points and build index map
    for idx, node in enumerate(swc_data):
        n = node['n']
        x, y, z = node['x'], node['y'], node['z']
        r = node['r']
        points.InsertNextPoint(x, y, z)
        radii.InsertNextValue(r)
        index_map[n] = idx

    # Build child map
    child_map = {}
    for node in swc_data:
        p = node['p']
        n = node['n']
        if p != -1:
            child_map.setdefault(p, []).append(n)

    # Find root nodes (nodes with parent -1)
    root_nodes = [node['n'] for node in swc_data if node['p'] == -1]

    # Collect polylines iteratively
    polylines = []
    stack = []
    for root_id in root_nodes:
        stack.append((root_id, [index_map[root_id]]))

    while stack:
        node_id, current_polyline = stack.pop()
        children = child_map.get(node_id, [])
        if not children:
            # Leaf node, store the current polyline
            polylines.append(current_polyline)
        else:
            for child_id in children:
                child_polyline = current_polyline + [index_map[child_id]]
                stack.append((child_id, child_polyline))

    # Create lines from the polylines
    lines = vtk.vtkCellArray()
    for polyline_indices in polylines:
        if len(polyline_indices) < 2:
            continue
        poly_line = vtk.vtkPolyLine()
        poly_line.GetPointIds().SetNumberOfIds(len(polyline_indices))
        for i, idx in enumerate(polyline_indices):
            poly_line.GetPointIds().SetId(i, idx)
        lines.InsertNextCell(poly_line)

    # Create polydata object
    poly_data = vtk.vtkPolyData()
    poly_data.SetPoints(points)
    poly_data.SetLines(lines)
    poly_data.GetPointData().AddArray(radii)
    poly_data.GetPointData().SetActiveScalars("Radius")

    return poly_data

def decimate_polydata(poly_data, target_reduction=0.5):
    """Decimates the polyData to reduce the number of points."""
    decimate = vtk.vtkDecimatePolylineFilter()
    decimate.SetInputData(poly_data)
    decimate.SetTargetReduction(target_reduction)  # Fraction of points to remove (0.0 to 1.0)
    decimate.Update()
    return decimate.GetOutput()

def create_tube(poly_data, tube_sides=8):
    """Creates a tube (mesh) from the polyline data."""
    tube_filter = vtk.vtkTubeFilter()
    tube_filter.SetInputData(poly_data)
    tube_filter.SetNumberOfSides(tube_sides)  # Adjust as needed
    tube_filter.SetVaryRadiusToVaryRadiusByAbsoluteScalar()
    tube_filter.SetCapping(True)
    tube_filter.Update()
    return tube_filter.GetOutput()

def clean_mesh(input_mesh, tolerance=0.0):
    """Cleans the mesh by removing duplicate points and unused points."""
    cleaner = vtk.vtkCleanPolyData()
    cleaner.SetInputData(input_mesh)
    cleaner.SetTolerance(tolerance)
    cleaner.PointMergingOn()
    cleaner.Update()
    return cleaner.GetOutput()

def smooth_mesh(input_mesh, iterations=3, pass_band=0.1):
    """Applies a smoothing filter to the mesh."""
    smoother = vtk.vtkWindowedSincPolyDataFilter()
    smoother.SetInputData(input_mesh)
    smoother.SetNumberOfIterations(iterations)
    smoother.SetPassBand(pass_band)
    smoother.NormalizeCoordinatesOn()
    smoother.BoundarySmoothingOn()
    smoother.FeatureEdgeSmoothingOff()
    smoother.SetEdgeAngle(15.0)
    smoother.Update()
    return smoother.GetOutput()

def export_mesh_to_stl(input_mesh, filename):
    """Exports the mesh to an STL file in binary mode."""
    stl_writer = vtk.vtkSTLWriter()
    stl_writer.SetFileName(filename)
    stl_writer.SetInputData(input_mesh)
    stl_writer.SetFileTypeToBinary()  # Ensure binary mode
    stl_writer.Write()

def get_mesh_info(mesh):
    """Returns a string with mesh information."""
    num_points = mesh.GetNumberOfPoints()
    num_polys = mesh.GetNumberOfPolys()
    num_strips = mesh.GetNumberOfStrips()
    num_cells = mesh.GetNumberOfCells()
    return f"Points={num_points}, Polys={num_polys}, Strips={num_strips}, Cells={num_cells}"

def process_swc_file(args):
    """Processes a single SWC file and exports the mesh to an STL file."""
    # Unpack the arguments
    (swc_file, output_directory, target_reduction, tube_sides,
     enable_cleaning, smoothing_iterations, smoothing_pass_band) = args

    base_name = os.path.splitext(os.path.basename(swc_file))[0]
    stl_filename = os.path.join(output_directory, f"{base_name}.stl")
    log_entries = []
    try:
        start_time_total = time.time()
        log_entries.append(f"Processing file: {base_name}")
        log_entries.append(f"SWC File: {swc_file}")
        log_entries.append(f"Output STL File: {stl_filename}")

        # Record initial file size
        initial_file_size = os.path.getsize(swc_file)
        log_entries.append(f"Initial SWC file size: {initial_file_size} bytes")

        # Read the SWC file
        start_time = time.time()
        swc_data, error = read_swc(swc_file)
        if error or not swc_data:
            log_entries.append(f"[ERROR] Failed to read SWC data: {error}")
            return log_entries
        elapsed_time = time.time() - start_time
        log_entries.append(f"Read SWC file in {elapsed_time:.4f} seconds")

        # Record number of nodes in SWC data
        log_entries.append(f"Number of nodes in SWC data: {len(swc_data)}")

        # Create VTK PolyData from SWC data
        start_time = time.time()
        poly_data = create_vtk_from_swc(swc_data)
        if poly_data.GetNumberOfPoints() == 0 or poly_data.GetNumberOfLines() == 0:
            log_entries.append(f"[ERROR] PolyData is empty or has no lines.")
            return log_entries
        elapsed_time = time.time() - start_time
        log_entries.append(f"Created VTK PolyData in {elapsed_time:.4f} seconds")

        # Record initial PolyData information
        initial_points = poly_data.GetNumberOfPoints()
        initial_lines = poly_data.GetNumberOfLines()
        log_entries.append(f"Initial PolyData: Points={initial_points}, Lines={initial_lines}")

        # Decimate polyData to reduce the number of points
        start_time = time.time()
        poly_data = decimate_polydata(poly_data, target_reduction=target_reduction)
        elapsed_time = time.time() - start_time
        log_entries.append(f"Decimated PolyData in {elapsed_time:.4f} seconds")

        # Record decimated PolyData information
        decimated_points = poly_data.GetNumberOfPoints()
        decimated_lines = poly_data.GetNumberOfLines()
        log_entries.append(f"Decimated PolyData: Points={decimated_points}, Lines={decimated_lines}")

        # Create the tube (mesh) from the polyline data
        start_time = time.time()
        mesh = create_tube(poly_data, tube_sides=tube_sides)
        elapsed_time = time.time() - start_time
        log_entries.append(f"Created tube mesh in {elapsed_time:.4f} seconds")

        # Record mesh information after tube creation
        mesh_info = get_mesh_info(mesh)
        log_entries.append(f"Mesh after tube creation: {mesh_info}")

        # Clean the mesh to remove duplicates (if enabled)
        if enable_cleaning:
            start_time = time.time()
            mesh = clean_mesh(mesh)
            elapsed_time = time.time() - start_time
            log_entries.append(f"Cleaned mesh in {elapsed_time:.4f} seconds")
            # Record mesh information after cleaning
            mesh_info = get_mesh_info(mesh)
            log_entries.append(f"Mesh after cleaning: {mesh_info}")
        else:
            log_entries.append("Mesh cleaning skipped.")

        # Smooth the mesh with specified parameters
        start_time = time.time()
        mesh = smooth_mesh(mesh, iterations=smoothing_iterations, pass_band=smoothing_pass_band)
        elapsed_time = time.time() - start_time
        log_entries.append(f"Smoothed mesh in {elapsed_time:.4f} seconds")
        # Record mesh information after smoothing
        mesh_info = get_mesh_info(mesh)
        log_entries.append(f"Mesh after smoothing: {mesh_info}")

        # Export the mesh to an STL file
        start_time = time.time()
        export_mesh_to_stl(mesh, stl_filename)
        elapsed_time = time.time() - start_time
        log_entries.append(f"Exported mesh to STL in {elapsed_time:.4f} seconds")

        # Record final STL file size
        final_file_size = os.path.getsize(stl_filename)
        log_entries.append(f"Final STL file size: {final_file_size} bytes")

        total_elapsed_time = time.time() - start_time_total
        log_entries.append(f"Total processing time: {total_elapsed_time:.4f} seconds")
        log_entries.append("------------------------------------------------------------")

    except Exception as e:
        error_message = f"[ERROR] An exception occurred: {e}"
        log_entries.append(error_message)
        # Record the exception in the log file
        import traceback
        log_entries.append(traceback.format_exc())
    return log_entries

def process_swc_files(swc_directory, output_directory, target_reduction, tube_sides,
                      enable_cleaning, smoothing_iterations, smoothing_pass_band, num_processes):
    """Processes all SWC files in the given directory using parallel processing."""
    # Get a list of SWC files in the directory
    swc_files = glob.glob(os.path.join(swc_directory, '*.swc'))
    total_files = len(swc_files)
    messages = []
    messages.append(f"Found {total_files} SWC files to process.")

    if total_files == 0:
        messages.append("No SWC files found in the specified directory.")
        return messages

    # Create a dated output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dated_output_directory = os.path.join(output_directory, f"Processed_{timestamp}")
    os.makedirs(dated_output_directory, exist_ok=True)

    # Prepare arguments for each process
    args_list = [
        (swc_file, dated_output_directory, target_reduction, tube_sides,
         enable_cleaning, smoothing_iterations, smoothing_pass_band)
        for swc_file in swc_files
    ]

    # Process files in parallel
    start_time = time.time()
    with Pool(processes=num_processes) as pool:
        results = pool.map(process_swc_file, args_list)
    total_time = time.time() - start_time

    # Collect messages from all processes
    log_entries = []
    for result in results:
        log_entries.extend(result)

    messages.append(f"Completed processing {total_files} files in {total_time:.2f} seconds.")
    messages.append(f"Processed files are saved in: {dated_output_directory}")

    # Write the log entries to a log file in the dated output directory
    log_file_path = os.path.join(dated_output_directory, 'processing_log.txt')
    with open(log_file_path, 'w') as log_file:
        log_file.write('\n'.join(log_entries))

    # Append a message about the log file location
    messages.append(f"Processing log saved to: {log_file_path}")

    return messages
