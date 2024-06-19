import cv2
import numpy as np
import base64
from matplotlib.path import Path
import plotly.express as px

def create_mask_from_paths(path_coordinates, img_shape):
    """
    Create a binary mask from path coordinates.

    This function generates a binary mask of the specified image shape, with True values
    inside the paths defined by the path coordinates.

    :param path_coordinates: A list of path coordinates, where each path is defined by a list of (x, y) tuples.
    :param img_shape: The shape of the image (height, width, channels).
    :return: A binary mask with True values inside the paths.
    """
    height, width, _ = img_shape

    # Create a meshgrid of (x, y) coordinates
    x, y = np.meshgrid(np.arange(width),np.arange(height))
    x, y = x.flatten(), y.flatten()

    # Stack the flattened x and y coordinates into a single array of points
    # Each point is represented as a (x, y) tuple
    points = np.vstack((x,y)).T

    # Initialize an empty binary mask of the same height and width as the image
    mask = np.zeros((height, width), dtype=bool)

    # Iterate over each set of path coordinates
    for path_coords in path_coordinates:
        # Create a Path object from the path coordinates
        path = Path(path_coords)
        # Use the Path object to determine which points are inside the path
        # Update the mask with True values where points are inside the path
        mask |= path.contains_points(points).reshape(height, width)

    return mask

def encode_img_for_display(cv2rgbimg):
    """
    Encode an image for display in the application.

    This function encodes a CV2 RGB image as a PNG and then base64 encodes the PNG for display.

    :param cv2rgbimg: The CV2 RGB image to encode.
    :return: The base64 encoded PNG image as a string.
    """
    _, buffer = cv2.imencode('.png', cv2rgbimg)
    encoded_image = base64.b64encode(buffer).decode('utf-8')
    return encoded_image


def contours_from_mask(mask):
    """
    Extract contours from a binary mask.

    This function finds and returns the contours in a binary mask using OpenCV.

    :param mask: The binary mask from which to extract contours.
    :return: A list of contours found in the mask.
    """
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours

def plotly_shapes_from_contours(contours,pen_color="purple"):
    """
    Convert contours into Plotly shape dictionaries.

    This function takes a list of contours and converts each contour into a Plotly shape dictionary
    with a specified pen color. The shapes can be used to overlay contours on Plotly figures.

    :param contours: A list of contours, where each contour is an array of (x, y) coordinates.
    :param pen_color: The color of the contour lines (default is "purple").
    :return: A list of Plotly shape dictionaries representing the contours.
    """
    shapes = []
    for contour in contours:
        # Construct the path string for the contour
        path = 'M ' + ' L '.join(f"{x[0][0]},{x[0][1]}" for x in contour) + ' Z'

        # Create a dictionary representing the shape
        shape = dict(
            type="path",
            path=path,
            line_color=pen_color,
            fillcolor="rgba(255, 0, 0, 0.4)",  # Semi-transparent fill
            editable = True
        )

        # Append the shape dictionary to the list
        shapes.append(shape)
    return shapes


def create_checkerboard(image_shape, square_size=50):
    """
    Create a checkerboard pattern image to indicate transparent background areas of masks.

    This function generates a checkerboard pattern image of the specified shape and square size.

    :param image_shape: The shape of the image (rows, cols, channels).
    :param square_size: The size of each square in the checkerboard pattern (default is 50).
    :return: A checkerboard pattern image as a NumPy array.
    """
    rows, cols, _ = image_shape
    checkerboard = np.zeros((rows, cols), dtype=np.uint8)
    for i in range(rows):
        for j in range(cols):
            if (i // square_size) % 2 == (j // square_size) % 2:
                checkerboard[i, j] = 150
            else:
                checkerboard[i, j] = 50
    return checkerboard

def apply_mask_to_image(image, mask, square_size=50):
    """
    Apply a mask to an image and overlay a checkerboard pattern where the mask is False.

    This function overlays a checkerboard pattern on the regions of the image where the mask is False.
    It ensures that the mask is a boolean array and creates a 3-channel checkerboard pattern.

    :param image: The original image as a NumPy array.
    :param mask: The binary mask as a NumPy array.
    :param square_size: The size of each square in the checkerboard pattern (default is 50).
    :return: The image with the checkerboard pattern applied where the mask is False.
    """
    # Ensure the mask is a boolean array
    mask = mask.astype(bool)
    
    # Create a checkerboard pattern
    checkerboard = create_checkerboard(image.shape, square_size)
    
    # Create a 3-channel version of the checkerboard pattern
    checkerboard_rgb = np.stack([checkerboard] * 3, axis=-1)
    
    # Overlay the checkerboard pattern on the image where the mask is False
    masked_image = np.where(mask[..., None], image, checkerboard_rgb)

    return masked_image


def get_cv2_image(filename):
    """
    Read an image using OpenCV.

    This function reads an image from the specified file using OpenCV. The image is returned
    in its original color space (BGR).

    :param filename: The path to the image file.
    :return: The image as a NumPy array.
    """
    img = cv2.imread(filename)
    # The following line is needed if we have to convert the image to RGB - I don't think we need to, though
    #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img

def add_meta_info_to_masks(flat_masks):
    """
    Add metadata information to a list of masks.

    This function takes a list of masks and adds metadata information to each mask.
    Currently, it adds the segmentation data to each mask's metadata dictionary.
    Additional metadata could be added as needed.

    :param flat_masks: A list of masks (binary masks as NumPy arrays).
    :return: A list of metadata-enhanced masks (dictionaries containing segmentation data).
    """
    meta_masks = []
    for mask_num in range(len(flat_masks)):
        curr_meta_mask = {}
        curr_meta_mask["segmentation"] = flat_masks[mask_num]
        #!! TODO: add more meta info
        meta_masks.append(curr_meta_mask)
    return meta_masks

def hex_to_rgb(hex_color):
    """
    Convert a hex color string to an RGB list.

    This function converts a hex color string (e.g., "#RRGGBB") to a list of RGB values.
    The hex color string is stripped of its leading '#' character, and each pair of hex digits
    is converted to an integer representing the red, green, and blue color components.

    :param hex_color: The hex color string to convert (e.g., "#RRGGBB").
    :return: A list of RGB values [R, G, B].
    """
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2 ,4)]


def make_composite_image(image,mask_image):
    """
    Create a composite image by blending an original image with a mask image.

    This function converts the original image to grayscale and then blends it with the mask image.
    The masked areas are highlighted while the rest of the image remains in grayscale.
    The resulting composite and mask images are encoded as base64 strings for display in a web application.

    :param image: The original image as a NumPy array (BGR color space).
    :param mask_image: The mask image as a NumPy array.
    :return: A tuple containing the composite image and the display mask image, both encoded as base64 strings.
    """
    # Convert the original image to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_image = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)

    # Create a background image that is grayscale where the mask is not present
    gray_background_image = np.where(mask_image > 0, mask_image, gray_image)

    # Initialize the composite image with the same shape as the original image
    mask_composite_image = np.zeros_like(image)

    # Blend the grayscale background image with the mask image to create the composite image
    mask_composite_image = cv2.addWeighted(gray_background_image,0.95,mask_image,0.05,0)

    # Encode the composite image and segmented mask image for display
    mask_composite_image = 'data:image/png;base64,{}'.format(encode_img_for_display(cv2.cvtColor(mask_composite_image, cv2.COLOR_BGR2RGB)))
    display_mask_image = 'data:image/png;base64,{}'.format(encode_img_for_display(cv2.cvtColor(mask_image, cv2.COLOR_BGR2RGB)))
    
    return mask_composite_image, display_mask_image


