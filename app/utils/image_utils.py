import cv2
import numpy as np
import base64
from pathlib import Path

def create_mask_from_paths(path_coordinates, img_shape):
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

def apply_mask_to_image(image, mask):

    # Ensure the mask is a boolean array
    mask = mask.astype(bool)

    # Create an empty image with the same dimensions as the original image
    masked_image = np.zeros_like(image)

    # Apply the mask to the image
    masked_image[mask] = image[mask]

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


