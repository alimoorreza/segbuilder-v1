import cv2
import numpy as np
import base64
from matplotlib.path import Path
import plotly.express as px

def create_mask_from_paths(path_coordinates, img_shape):
    #print("path_coordinates",path_coordinates)
    #print("img_shape",img_shape)
    height, width, _ = img_shape
    #y, x = np.mgrid[:height, :width]
    #points = np.vstack((x.ravel(), y.ravel())).T
    x, y = np.meshgrid(np.arange(width),np.arange(height))

    x, y = x.flatten(), y.flatten()

    points = np.vstack((x,y)).T


    mask = np.zeros((height, width), dtype=bool)
    for path_coords in path_coordinates:
        path = Path(path_coords)
        mask |= path.contains_points(points).reshape(height, width)



    return mask

def encode_img_for_display(cv2rgbimg):
    _, buffer = cv2.imencode('.png', cv2rgbimg)
    #
    encoded_image = base64.b64encode(buffer).decode('utf-8')
    return encoded_image


def contours_from_mask(mask):
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours

def plotly_shapes_from_contours(contours,pen_color="purple"):
    shapes = []
    for contour in contours:
        # Each contour is a shape
        path = 'M ' + ' L '.join(f"{x[0][0]},{x[0][1]}" for x in contour) + ' Z'
        shape = dict(
            type="path",
            path=path,
            line_color=pen_color,
            fillcolor="rgba(255, 0, 0, 0.4)",  # Semi-transparent fill
            editable = True
        )
        shapes.append(shape)
    return shapes


def create_checkerboard(image_shape, square_size=50):
    rows, cols, _ = image_shape
    checkerboard = np.zeros((rows, cols), dtype=np.uint8)
    for i in range(rows):
        for j in range(cols):
            if (i // square_size) % 2 == (j // square_size) % 2:
                checkerboard[i, j] = 200
            else:
                checkerboard[i, j] = 100
    return checkerboard

def apply_mask_to_image(image, mask, square_size=50):
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
    img = cv2.imread(filename)
    #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img

def add_meta_info_to_masks(flat_masks):
    meta_masks = []
    for mask_num in range(len(flat_masks)):
        curr_meta_mask = {}
        curr_meta_mask["segmentation"] = flat_masks[mask_num]
        #!! TODO: add more meta info
        meta_masks.append(curr_meta_mask)
    return meta_masks

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2 ,4)]


def make_composite_image(image,mask_image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_image = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)
    gray_background_image = np.where(mask_image > 0, mask_image, gray_image)
    mask_composite_image = np.zeros_like(image)
    mask_composite_image = cv2.addWeighted(gray_background_image,0.95,mask_image,0.05,0)
    mask_composite_image = 'data:image/png;base64,{}'.format(encode_img_for_display(cv2.cvtColor(mask_composite_image, cv2.COLOR_BGR2RGB)))
    display_mask_image = 'data:image/png;base64,{}'.format(encode_img_for_display(cv2.cvtColor(mask_image, cv2.COLOR_BGR2RGB)))
    return mask_composite_image, display_mask_image


