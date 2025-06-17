import os
import numpy as np
import nrrd
import glob
import matplotlib.pyplot as plt
from skimage import measure, filters
from scipy.ndimage import binary_erosion
from scipy.interpolate import interp1d

def rotate_segmentations(input_folder, temp_dir):
    rotated_files = []
    nrrd_files = [f for f in os.listdir(input_folder) if f.endswith('.nrrd')]

    if not nrrd_files:
        return None

    post_file = os.path.join(input_folder, nrrd_files[0])
    rotated_post, spacing_post, matrix, z_coords, axis = rotation(post_file)
    rotated_post_uint8 = rotated_post.astype(np.uint8)

    post_out_path = os.path.join(temp_dir, nrrd_files[0].replace('.nrrd', '_rotated.nrrd'))
    nrrd.write(post_out_path, rotated_post_uint8, header={'spacings': spacing_post})
    rotated_files.append(post_out_path)

    for file in nrrd_files[1:]:
        pre_path = os.path.join(input_folder, file)
        rotated_pre, spacing_pre = apply_same_transformation(pre_path, matrix, z_coords, axis)
        rotated_pre_uint8 = rotated_pre.astype(np.uint8)
        pre_out_path = os.path.join(temp_dir, file.replace('.nrrd', '_rotated.nrrd'))
        nrrd.write(pre_out_path, rotated_pre_uint8, header={'spacings': spacing_pre})
        rotated_files.append(pre_out_path)

    return rotated_files


def calculate_ticks(size, resolution):
    step = round(size / 4) - 1
    pixels = range(0, size, step)
    mm_labels = [x * resolution for x in pixels]
    labels = [f'{val:.2f}' for val in mm_labels]
    return pixels, labels


def generate_perimeter_plots(output_path, patient_id, res_x, res_y, peri_up, peri_low, pre_up, post_up, pre_low, post_low):
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axs = plt.subplots(1, 2)

    for idx, (data, title) in enumerate(zip([peri_up, peri_low], ["Upper section", "Lower section"])):
        axs[idx].imshow(data)
        pix_x, labels_x = calculate_ticks(data.shape[1], res_x)
        pix_y, labels_y = calculate_ticks(data.shape[0], res_y)
        axs[idx].set_xticks(pix_x)
        axs[idx].set_xticklabels(labels_x)
        axs[idx].set_yticks(pix_y)
        axs[idx].set_yticklabels(labels_y)
        axs[idx].set_title(title)
        axs[idx].set_xlabel("Transverse axis [mm]")
        axs[idx].set_ylabel("Anteroposterior axis [mm]")

    fig.text(0.1, 0.1, 'RED: PRE', color='red')
    fig.text(0.3, 0.1, 'BLUE: POST', color='blue')
    fig.suptitle(f'Patient {patient_id}', y=0.9)
    plt.subplots_adjust(wspace=0.6)

    plot_path = os.path.join(output_path, f'Patient_{patient_id}_Mean_perimeters.png')
    plt.savefig(plot_path)
    plt.close(fig)

    # Save raw arrays
    np.save(os.path.join(output_path, f'Patient_{patient_id}_PRE_UP_perimeter.npy'), pre_up)
    np.save(os.path.join(output_path, f'Patient_{patient_id}_POST_UP_perimeter.npy'), post_up)
    np.save(os.path.join(output_path, f'Patient_{patient_id}_PRE_LOW_perimeter.npy'), pre_low)
    np.save(os.path.join(output_path, f'Patient_{patient_id}_POST_LOW_perimeter.npy'), post_low)

    return plot_path

def apply_transformation(binary_mask, rotation_matrix, z_coord, caso, target_axis,
                         enlargement_factor=2, dilation_radius=1):
    import numpy as np
    import matplotlib.pyplot as plot
    from scipy.ndimage import binary_dilation, find_objects
    
    """
    Esta función sirve para aplicar la matriz de rotación calculada a la
    máscara binaria. Para ello, es necesario aumentar el tamaño de la matriz 
    de la máscara (para que al rotarla, el objeto siga encajando en la máscara).

    Parameters
    ----------
    binary_mask : TYPE
        DESCRIPTION.
    rotation_matrix : TYPE
        DESCRIPTION.
    z_coord : TYPE
        DESCRIPTION.
    enlargement_factor : TYPE, optional
        DESCRIPTION. The default is 2.
    dilation_radius : TYPE, optional
        DESCRIPTION. The default is 1.

    Returns
    -------
    rotated_mask : Array of bool 
        Máscara del objeto rotada.

    """
    
    
    def calculate_centroid(objeto):
        """
        Esta función permite calcular el centroide de una máscara.
    
        Parameters
        ----------
        objeto :  Array of bool 
        Máscara de un objeto.
    
        Returns
        -------
        centroid : Array of float
            Coordenadas del centroide del objeto.
    
        """
        # Encuentra las coordenadas de los píxeles donde el objeto está presente
        coordinates = np.column_stack(np.where(objeto == 1))
    
        # Calcula el centroide como el promedio de las coordenadas
        centroid = np.mean(coordinates, axis=0)
    
        return centroid
    
    # Aumentar el tamaño de la matriz
    enlarged_shape = np.array(binary_mask.shape) * enlargement_factor
    enlarged_rotated_mask = np.zeros(enlarged_shape, dtype=binary_mask.dtype)
    
    # Calcular la posición central para copiar la máscara rotada
    center_position_enlarged = np.array(enlarged_shape) // 2
    start_position = center_position_enlarged - np.array(binary_mask.shape) // 2
    end_position = start_position + binary_mask.shape
    
    # Copiar la máscara rotada en la posición central
    enlarged_rotated_mask[start_position[0]:end_position[0], start_position[1]:end_position[1],
    start_position[2]:end_position[2]] = binary_mask
    
    # Obtener las coordenadas de los voxels donde el objeto está presente en la máscara AMPLIADA
    coords_rotated = np.column_stack(np.where(enlarged_rotated_mask == 1))
    
    # Aplicar la matriz de transformación a las coordenadas homogéneas
    transformed_coords = np.dot(rotation_matrix, coords_rotated.T).T[:, :3]
    
    # Crear una nueva máscara con las coordenadas transformadas centradas
    new_mask = np.zeros_like(enlarged_rotated_mask)
    
    # Obtener las dimensiones de la nueva máscara
    mask_shape = new_mask.shape
    
    # Calcular el centro de la nueva máscara
    center_x, center_y, center_z = mask_shape[0] // 2, mask_shape[1] // 2, mask_shape[2] // 2
    
    # Calcular el desplazamiento necesario para centrar las coordenadas transformadas
    offset_x, offset_y, offset_z = center_x - np.round(transformed_coords[:, 0]).mean(), \
                                  center_y - np.round(transformed_coords[:, 1]).mean(), \
                                  center_z - np.round(transformed_coords[:, 2]).mean()
    
    
    # Aplicar el desplazamiento a las coordenadas transformadas
    transformed_coords[:, 0] += offset_x
    transformed_coords[:, 1] += offset_y
    transformed_coords[:, 2] += offset_z
    
    # Redondear las nuevas coordenadas para obtener índices enteros y aplicar el desplazamiento
    transformed_coords = np.round(transformed_coords).astype(int)
    
    # Actualizar la nueva máscara con los valores del objeto rotado
    new_mask[transformed_coords[:, 0], transformed_coords[:, 1], transformed_coords[:, 2]] = 1
    
    # Aplicar dilatación para corregir los píxeles con valor '0' dentro del objeto
    rotated_mask = binary_dilation(new_mask, iterations=dilation_radius)
    
    # Encontrar los límites de la máscara dilatada
    slices = find_objects(rotated_mask)[0]
    
    # Recortar la máscara dilatada para ajustarla a los límites del objeto
    rotated_mask = rotated_mask[slices]

    """
    Descomentar para visualizar   
    
    # Segundo gráfico - Máscara Rotada
    # Calcular el centroide de la máscara rotada
    centroid = calculate_centroid(rotated_mask)
    fig, ax = plot.subplots(figsize=(12, 6))
      
    ax.imshow(rotated_mask[:, :, z_coord], cmap='gray')
    ax.set_title(f'Máscara Rotada  {caso}')
      
      # Dibujar el eje objetivo en rojo
    ax.quiver(centroid[1], centroid[0],
                      target_axis[1], target_axis[0],
                      color='red', scale=0.001, scale_units='xy', width=0.01)
    ax.quiver(centroid[1], centroid[0],
                      -target_axis[1], -target_axis[0],
                      color='red', scale=0.001, scale_units='xy', width=0.01)
     
    plot.show()
    """
        
    return rotated_mask

def apply_same_transformation(nrrd_path, rotation_matrix, z_coords, target_axis):
    """
    Applies a precomputed rotation (from POST mask) to a new NRRD volume (e.g. PRE).

    Parameters
    ----------
    nrrd_path : str
        Path to the .nrrd file to transform (typically the PRE mask).
    rotation_matrix : ndarray
        Rotation matrix obtained from aligning the POST mask.
    z_coords : ndarray
        Z-axis coordinates used during the rotation of the POST mask.
    target_axis : str
        Axis used to reorient the original image.

    Returns
    -------
    rotated_mask : np.ndarray
        Transformed binary mask.
    pixel_spacing : tuple
        Resolution of the input volume.
    """
    import SimpleITK as sitk
    
    def load_nrrd(nrrd_path):
        """
        Loads a binary mask and pixel spacing from a NRRD file.

        Returns:
        --------
        mask : np.ndarray
        spacing : tuple
        label : str ("PRE" or "POST")
        """
        image = sitk.ReadImage(nrrd_path)
        spacing = image.GetSpacing()
        mask = sitk.GetArrayFromImage(image)
        label = "PRE" if "PRE" in os.path.basename(nrrd_path) else "POST"
        return mask, spacing, label

    mask, spacing, label = load_nrrd(nrrd_path)
    rotated = apply_transformation(mask, rotation_matrix, z_coords, label, target_axis)
    return rotated, spacing


def rotation(nrrd_file_path):
    import SimpleITK as sitk
    import numpy as np
    import matplotlib.pyplot as plot
    
    """
    Función base que contiene las demás funciones. Le entra la ruta a un archivo
    .nrrd y devuelve la mascara rotada y su espaciado de los píxeles.

    Parameters
    ----------
    mask : str
        Ruta al archivo .nrrd.

    Returns
    -------
    rotated_mask : Array of bool 
        Máscara del objeto rotada.
    pixel_spacing : tuple
        Espaciado de los píxeles del objeto (resolución)

    """
    
    def load_nrrd_file(nrrd_file):
        """
        Esta función permite cargar el archivo nrrd en python, así como obtener
        la máscara binaria del volumen y el espaciado de los píxeles.

        Parameters
        ----------
        nrrd_file : str
            Ruta al archivo .nrrd.

        Returns
        -------
        binary_mask : Array of bool 
            Máscara del objeto.
        pixel_spacing : tuple
            Espaciado de los píxeles del objeto (resolución)

        """
        # Load the NRRD file
        es_pre = 'PRE' in nrrd_file
        es_post = 'POST' in nrrd_file
        
        if es_pre:
            caso='PRE'
        if es_post:
            caso='POST'
        
        
        image = sitk.ReadImage(nrrd_file)
        pixel_spacing = image.GetSpacing()
       
        binary_mask = sitk.GetArrayFromImage(image)

        return binary_mask, pixel_spacing, caso
    
    
    def calculate_centroid(objeto):
        """
        Esta función permite calcular el centroide de una máscara.
    
        Parameters
        ----------
        objeto :  Array of bool 
        Máscara de un objeto.
    
        Returns
        -------
        centroid : Array of float
            Coordenadas del centroide del objeto.
    
        """
        # Encuentra las coordenadas de los píxeles donde el objeto está presente
        coordinates = np.column_stack(np.where(objeto == 1))
    
        # Calcula el centroide como el promedio de las coordenadas
        centroid = np.mean(coordinates, axis=0)
    
        return centroid
    
    

    def compute_principal_axis(binary_mask):
        """
        Esta función permite encontrar el eje principal de la máscara binaria
        encontrada.
    
        Parameters
        ----------
        binary_mask : Array of bool 
            Máscara del objeto.
    
        Returns
        -------
        object_axis : Array of int32
            Eje principal del objeto.
        coords : Array
            Matriz con las posiciones de la máscara donde hay objeto.
    
        """
        # Get voxel coordinates where the object is present
        coords = np.column_stack(np.where(binary_mask == 1))
        
        # Compute the covariance matrix
        covariance_matrix = np.cov(coords, rowvar=False)
        
        # Compute eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)
        
        # Sort eigenvalues and eigenvectors in descending order
        sorted_indices = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[sorted_indices]
        eigenvectors = eigenvectors[:, sorted_indices]
        
        # Principal axis is the eigenvector corresponding to the largest eigenvalue
        object_axis = np.round(eigenvectors[:, 0], 3)
        return object_axis, coords

    def find_base_direction(binary_mask, object_axis, coords, caso):
        """
        Esta función sirve para encontrar la orientación del objeto a partir de su 
        base superior, es decir, medir su inclinación.

        Parameters
        ----------
        binary_mask : Array of bool 
            Máscara del objeto.
        object_axis : Array of int32
            Eje principal del objeto.
        coords :  Array of float
            Matriz con las posiciones de la máscara donde hay objeto.

        Returns
        -------
        base_direction : Array of int32
            Eje de la base del objeto (inclinación)
        z_coord : int
            Slice central del objeto en el plano Z.

        """
        # Encontrar la coordenada Z del eje del objeto
        z_coord = int(np.mean(coords[:, 2]))

        # Seleccionar la slice del plano XY que pasa por el eje del objeto
        xy_slice = binary_mask[:, :, z_coord]
            
        # Crear un vector que represente el eje del objeto en el plano XY
        if object_axis[0] == 0 and object_axis[1] == 0:
            # Si el objeto está orientado verticalmente, crea un vector vertical
            object_axis_xy = np.array([0, 1])
        else:
            object_axis_xy = np.array([-object_axis[1], object_axis[0]])

        y_coords, x_coords = np.where(xy_slice == 1)
        xy_coords = np.column_stack((y_coords, x_coords))
        
        # Calcular la posición relativa a la proyección del eje del objeto
        relative_positions = np.dot(xy_coords - coords[:, :2].mean(axis=0), object_axis_xy)

        # Dividir el plano en 2 secciones a la izquierda y a la derecha del eje
        left_mask = relative_positions < 0
        right_mask = relative_positions >= 0

        left_half = xy_coords[left_mask]
        right_half = xy_coords[right_mask]

        # Encontrar el punto más alto en cada mitad según el eje z
        left_highest_point = left_half[np.argmax(left_half[:, 0])]
        right_highest_point = right_half[np.argmax(right_half[:, 0])]

        # Crear un eje que una esos dos puntos
        base_direction = right_highest_point - left_highest_point
        
        """
        Descomentar para visualizar

        
        # VISUALIZACIÓN
        centroid = calculate_centroid(binary_mask)
        base_direction_d=-base_direction
        base_direction_d[0]=base_direction[0]
        object_axis[0]=-object_axis[0]

        # Crear un solo gráfico
        fig, ax = plot.subplots(figsize=(12, 6))
        ax.imshow(binary_mask[:, :, z_coord], cmap='gray')
        ax.set_title(f'Máscara Original {caso}')

        #EJE OBJETIVO EN AMARILLO Y DISCONTINUO
        ax.quiver(centroid[1], centroid[0],
                       target_axis[1], target_axis[0],
                       color='y', scale=0.001, scale_units='xy', width=0.01, )
        ax.quiver(centroid[1], centroid[0],
                       -target_axis[1], -target_axis[0],
                       color='y', scale=0.001, scale_units='xy', width=0.01, label='Eje objetivo')


         #EJE A ROTAR DEL OBJETO EN VERDE
        ax.quiver(centroid[1], centroid[0],
                        base_direction_d[1], base_direction_d[0],
                        color='g', scale=0.001, scale_units='xy', width=0.01)
        ax.quiver(centroid[1], centroid[0],
                        -base_direction_d[1], -base_direction_d[0],
                        color='g', scale=0.001, scale_units='xy', width=0.01, label='Eje a rotar')
         
         #EJE PRINCIPAL DEL OBJETO EN AZUL
        ax.quiver(centroid[1], centroid[0],
                        object_axis[1], object_axis[0],
                        color='c', scale=0.001, scale_units='xy', width=0.01)
        ax.quiver(centroid[1], centroid[0],
                        -object_axis[1], -object_axis[0],
                        color='c', scale=0.001, scale_units='xy', width=0.01, label='Eje del saco')
         
        ax.scatter([left_highest_point[1], right_highest_point[1]],
                     [left_highest_point[0], right_highest_point[0]], c='r', marker='o', label='Highest Points')

        ax.plot([left_highest_point[1], right_highest_point[1]],
                     [left_highest_point[0], right_highest_point[0]], 'r-', label='Base Direction')

         
        ax.scatter(centroid[1], centroid[0], c='b', marker='x', label='Centroid')
         
        ax.legend()
         
        ax.invert_yaxis()
        ax.invert_xaxis()
        """
        
        base_direction = np.append(base_direction, 0) 
        
        return base_direction, z_coord
    
    
        
    
    
    def transformation(from_vector, to_vector, binary_mask, z_coord, caso, tolerance=1e-6):
        """
        Esta función sirve para calcular la transformación que se debe aplicar al
        objeto para convertir el vector de la dirección de la base en un vector
        paralelo al eje objetivo (que es el [0,1,0], es decir, poner la base plana).
    
        Parameters
        ----------
        from_vector : Array of int32
            Eje incial de la transformación.
        to_vector : Array of int32
            Eje final tras la transformación.
        binary_mask : Array of bool 
            Máscara del objeto.
        z_coord : int
            Slice central del objeto en el plano Z.
        tolerance : float, optional
            Valor que indica a partir de que ángulo se considera que el objeto
            ya está bien orientado y no requiere transformación.
            The default is 1e-6.
    
        Returns
        -------
        rotated_mask : TYPE
            DESCRIPTION.
            
        """
        
            
        def rotation_matrix_from_axis_angle(axis, angle):
            """
            Esta función permite encontrar la matriz de rotación a partir del eje de
            rotación y el ángulo entre los 2 vectores
        
            Parameters
            ----------
            axis : Array of int
                Eje de rotación necesario para transformar un vector en otro en un
                espacio tridimensional.
            angle : float
                Ángulo entre los dos vectores from_vector y to_vector en radianes. 
                Este ángulo es una medida de cuán "cercanos" o alineados están los dos 
                vectores en el espacio tridimensional.
        
            Returns
            -------
            rotation_matrix : Array
                Matriz de rotación necesaria para orientar correctamente el objeto.
        
            """
            # Normalize the axis vector
            axis = np.array(axis) / np.linalg.norm(axis)
            
            # Compute the components of the rotation matrix
            c = np.cos(angle)
            s = np.sin(angle)
            t = 1 - c
            
            # Matriz de rotación en el plano XY
            rotation_matrix = np.array([
                [t * axis[0]**2 + c, t * axis[0] * axis[1] - s * axis[2], t * axis[0] * axis[2] + s * axis[1]],
                [t * axis[0] * axis[1] + s * axis[2], t * axis[1]**2 + c, t * axis[1] * axis[2] - s * axis[0]],
                [t * axis[0] * axis[2] - s * axis[1], t * axis[1] * axis[2] + s * axis[0], t * axis[2]**2 + c]
            ])
            
            return rotation_matrix        
        
        
        # Normalize input vectors to ensure they are unit vectors
        from_vector = np.array(from_vector) / np.linalg.norm(from_vector)
        to_vector = np.array(to_vector) / np.linalg.norm(to_vector)
      
        # Check if the vectors have a small angle between them
        dot_product = np.dot(from_vector, to_vector)
        angle = np.arccos(np.clip(dot_product, -1.0, 1.0))  # Avoid numerical issues with arccos
        
        
        if np.abs(angle) == 0 or np.abs(angle - np.pi) < tolerance:
            rotated_mask=binary_mask
            rotation_matrix = np.identity(3)
            
        else:
            # Compute the rotation axis using the cross product
            rotation_axis = np.cross(from_vector, to_vector)
    
            # Create the rotation matrix
            rotation_matrix = rotation_matrix_from_axis_angle(rotation_axis, angle)
    
            # Aplicar la transformación al objeto dentro de la máscara
            rotated_mask = apply_transformation(binary_mask, rotation_matrix, z_coord, caso, target_axis)
    
    
        return rotated_mask, rotation_matrix
    
    
    # FUNCION PRINCIPAL, DIVIDA EN VARIAS FUNCIONES
    # Definir el eje objetivo
    target_axis = np.array([0, 1, 0])
    
    # Cargar la máscara del objeto
    binary_mask, pixel_spacing, caso = load_nrrd_file(nrrd_file_path)
    
    # Obtener el eje del objeto
    object_axis, coords= compute_principal_axis(binary_mask)
    
    # Calcular el eje a rotar (paralelo a la base)
    base_direction, z_coord  = find_base_direction(binary_mask, object_axis, coords, caso)
    
    # Aplicar la rotacion
    rotated_mask, rotation_matrix = transformation(base_direction, target_axis, binary_mask, z_coord, caso)
        
    return rotated_mask, pixel_spacing, rotation_matrix, z_coord, target_axis
 


# shape_statistics.py (modular version)

def extract_perimeter(mask):
    """Computes binary perimeter of a 2D mask using erosion."""
    eroded = binary_erosion(mask)
    return mask - eroded


def compute_perimeter_length(perimeter_mask):
    """Estimates total perimeter length using 8-connected neighbors."""
    y, x = np.where(perimeter_mask)
    neighbors = np.array([
        [-1, 0], [1, 0], [0, -1], [0, 1],  # 4-connectivity
        [-1, -1], [-1, 1], [1, -1], [1, 1]  # diagonals
    ])
    length = 0
    visited_pairs = set()

    for i in range(len(x)):
        for n in neighbors:
            x2, y2 = x[i] + n[1], y[i] + n[0]
            if 0 <= x2 < perimeter_mask.shape[1] and 0 <= y2 < perimeter_mask.shape[0]:
                if perimeter_mask[y2, x2]:
                    j = np.where((x == x2) & (y == y2))[0]
                    if j.size > 0:
                        pair = tuple(sorted([i, j[0]]))
                        if pair not in visited_pairs:
                            visited_pairs.add(pair)
                            length += np.sqrt(2) if np.sum(np.abs(n)) == 2 else 1
    return length


def read_nrrds_and_extract(ruta_sacos_procesados):
    """Reads PRE and POST .nrrd files and calculates perimeter and area per slice."""
    files = glob.glob(os.path.join(ruta_sacos_procesados, '*.nrrd'))
    pre_file, post_file = "", ""
    for f in files:
        if "PRE" in f:
            pre_file = f
        elif "POST" in f:
            post_file = f

    results = {}
    for label, path in zip(["PRE", "POST"], [pre_file, post_file]):
        vol, info = nrrd.read(path)
        spacing = info['spacings']
        perimeters = []
        areas = []

        for slice_img in vol:
            slice_2d = np.squeeze(slice_img)
            perimeter_mask = extract_perimeter(slice_2d)
            length = compute_perimeter_length(perimeter_mask) * spacing[0]
            perimeters.append(length)

            threshold = filters.threshold_otsu(slice_2d)
            binary = slice_2d > threshold
            labeled = measure.label(binary)
            area = sum([prop.area for prop in measure.regionprops(labeled)]) * spacing[0] * spacing[1]
            areas.append(area)

        results[f'Perimeters_{label}'] = np.array(perimeters)
        results[f'Areas_{label}'] = np.array(areas)

    return results


def remove_outliers(data):
    """Removes outliers using IQR trimming (middle 75%) for each series."""
    clean = {}
    for key, arr in data.items():
        n = len(arr)
        trimmed = arr[int(n * 0.0625): int(n * 0.9375)]
        q1, q3 = np.percentile(trimmed, [25, 75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        clean[key] = trimmed[(trimmed >= lower) & (trimmed <= upper)]
    return clean


def interpolate_series(data, length=350):
    """Interpolates each time series to a fixed number of points."""
    result = {}
    for key, values in data.items():
        x_orig = np.arange(1, len(values) + 1)
        x_new = np.linspace(1, len(values), length)
        f = interp1d(x_orig, values, kind='linear')
        result[key] = f(x_new)
    return result


def plot_comparison_graph(data, out_dir, patient_id, label, unit):
    """Generates area/perimeter comparison and %increase plots."""
    pre_key = [k for k in data if "PRE" in k][0]
    post_key = [k for k in data if "POST" in k][0]
    pre = data[pre_key]
    post = data[post_key]
    x = np.linspace(0, 100, len(pre))
    increase = (post - pre) / pre * 100

    # Plot PRE vs POST
    fig, ax = plt.subplots()
    ax.plot(x, pre, 'r', label="Pre", linewidth=2)
    ax.plot(x, post, 'b', label="Post", linewidth=2)
    ax.fill_between(x, pre, post, alpha=0.3, color='gray')
    ax.set_title(f"{label} Comparison")
    ax.set_xlabel("Slice position [%]")
    ax.set_ylabel(f"{label} [{unit}]")
    ax.legend()
    comp_path = os.path.join(out_dir, f"Patient_{patient_id}_{label}_comparison.png")
    fig.savefig(comp_path)
    plt.close(fig)

    # Plot % Increase
    fig2, ax2 = plt.subplots()
    ax2.plot(x, increase, 'g', label="Increase")
    mean_inc = np.mean(increase)
    std_inc = np.std(increase)
    ax2.axhline(mean_inc, color='orange', linestyle='--', label="Mean")
    ax2.fill_between(x, mean_inc - std_inc, mean_inc + std_inc, color='gold', alpha=0.3, label="±1 STD")
    ax2.set_title(f"{label} Increase = {mean_inc:.2f} ± {std_inc:.2f} %")
    ax2.set_xlabel("Slice position [%]")
    ax2.set_ylabel("Increase [%]")
    ax2.legend()
    inc_path = os.path.join(out_dir, f"Patient_{patient_id}_{label}_increase.png")
    fig2.savefig(inc_path)
    plt.close(fig2)

    # Save array
    np.save(os.path.join(out_dir, f"Patient_{patient_id}_{label}_increase.npy"), increase)
    return increase, inc_path


def shape_statistics(input_folder, save_folder, patient_id, interp_length=350):
    """
    Main entry point. Reads masks, computes shape features, interpolates,
    and generates figures.

    Returns:
        - interpolated length
        - path to area figure
        - path to perimeter figure
    """
    raw = read_nrrds_and_extract(input_folder)
    clean = remove_outliers(raw)
    interp = interpolate_series(clean, interp_length)

    perim_data = {k: v for k, v in interp.items() if "Perimeters" in k}
    area_data = {k: v for k, v in interp.items() if "Areas" in k}

    _, path_perim = plot_comparison_graph(perim_data, save_folder, patient_id, "Perimeters", "mm")
    _, path_area = plot_comparison_graph(area_data, save_folder, patient_id, "Areas", "mm²")

    return interp_length, path_area, path_perim
