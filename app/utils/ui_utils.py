
import cv2
from dash import html, dcc
import dash_bootstrap_components as dbc
import datetime
import logging 

from .image_utils import encode_img_for_display, apply_mask_to_image
from ..project_models import SB_project, SB_project_image
from ..resources import get_db_item

IMG_WIDTH = 300
#IMG_HEIGHT = 400

def generate_label_cards(username,project_name):
    """
    Generate label cards for a given project and user.

    This function retrieves label records from the database and generates Dash Bootstrap Components (dbc) cards
    for each label. The cards are styled with the label's color and name.

    :param username: The username of the user.
    :param project_name: The name of the project.
    :return: A list of dbc.Card objects representing the labels.
    """
    # Retrieve label records from the database
    db_label_records = get_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project_name),default_return={"classes":[]})
    label_records = db_label_records["classes"]

    # Iterate over each label record and create a dbc.Card for each label and append into a running list
    label_cards = []
    for r in label_records:
        label_card = dbc.Card([
            dbc.CardBody(style={"backgroundColor":"rgb({},{},{})".format(*r["color"])}), # Set background color to label color
            dbc.CardFooter(r["name"],style={"textAlign":"center"}) # Set label name as card footer
        ],style={"width":"8rem","height":"8rem","float":"left","marginLeft":"1rem"})
        label_cards.append(label_card)
    return label_cards

def create_mask_cards(img, masks, labels, label_options = ["unlabeled"], new_masks=False, index_offset = 0):
    """
    Create mask cards for displaying image masks with label options.

    This function generates Dash Bootstrap Components (dbc) cards for each mask, with dropdowns for selecting labels.
    It also includes buttons for moving, deleting, and editing masks.

    :param img: The original image as a NumPy array.
    :param masks: A list of masks as NumPy arrays.
    :param labels: A list of labels corresponding to each mask.
    :param label_options: A list of label options for the dropdowns (default is ["unlabeled"]).
    :param new_masks: A flag indicating whether the masks are new (default is False).
    :param index_offset: An offset for the mask indices (default is 0).
    :return: A list of dbc.Card objects representing the masks with label options.
    """
    # Convert the image from BGR to RGB color space
    image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Define ID types for the different components based on whether the masks are new
    id_type = "label-dropdown"
    front_button_id_type = "front-button"
    delete_button_id_type = "delete-button"
    edit_button_id_type = "edit-button"
    card_id_type = "mask-card"
    if new_masks:
        id_type = "new-label-dropdown"
        front_button_id_type = "new-front-button"
        delete_button_id_type = "new-delete-button"
        card_id_type = "new-mask-card"

    # a list to store the mask cards
    card_list = []
   
    #if there aren't enough labels for all the masks,
    #we will just copy the last label and use it for the rest of the masks
    #only will work if there is at least one label
    if len(labels) < len(masks):
        labels = labels+([labels[-1]]*(len(masks)-len(labels)))
    
    # Iterate over each mask and create a "card" for each one that contains a
    # dropdown with all of its class labels as well as front, edit, and delete buttons.
    # We're calling it a card, but it isn't actually a dbc.Card - just a <div> tag with appropriate styling
    for idx in range(len(masks)):
        label_idx = idx+index_offset
        curr_card = html.Div([
            html.Img(src='data:image/png;base64,{}'.format(encode_img_for_display(apply_mask_to_image(image,masks[idx]["segmentation"]))),width=IMG_WIDTH),
            dbc.Button(html.I(className="bi bi-box-arrow-in-up-left"),color="secondary",id={'type':front_button_id_type,'index':label_idx},style={"float":"left"}),
            dbc.Button(html.I(className="bi bi-pencil-fill"),color="info",id={'type':edit_button_id_type,'index':label_idx},style={"float":"left"}),
            dbc.Button(html.I(className="bi bi-backspace"),color="danger",id={'type':delete_button_id_type,'index':label_idx},style={"float":"left"}),
            dcc.Dropdown(options=label_options,value=labels[idx],id={'type':id_type,'index':label_idx},style={"float":"left","width":(IMG_WIDTH-136)})
        ],style={"width":(IMG_WIDTH+10)},id={'type':card_id_type,'index':label_idx},className="float-child")
        card_list.append(curr_card)
    
    container = html.Div(card_list, style={"display": "flex", "flex-wrap": "wrap", "gap":"10px"})
    
    return container






def populate_project_cards(username):
    """
    Populate project cards for a given user.

    This function retrieves the user's projects from the database and generates a list of Dash HTML 
    Div elements, each containing a project card. Each card displays the project's cover image 
    and project name.

    :param username: The username of the user.
    :return: A list of Dash HTML Div elements representing the project cards.
    """
    logging.debug("SBDEBUG: inside populate_project_cards")
    project_cards = []
    curr_projects = []

    # Retrieve the current projects for the user from the database
    db_results = get_db_item(table_name="projects",key_name="username",key_value=username,default_return={"projects":[]})
    curr_projects = db_results["projects"]
    #print("CURR PROJECTS:",curr_projects)

    # Iterate over each project
    for proj in curr_projects:
        
        sb_project = SB_project(username,proj)
        logging.debug("SBDEBUG: about to create a project card")
        cover_image_url = sb_project.get_cover_image_url()
        logging.debug("SBDEBUG: sb_project.get_cover_image_url() - %s",cover_image_url)

        # Create a Dash Bootstrap Card for the project
        curr_card = html.Div(id={'type':"project-card",'index':proj},
            children=dbc.Card([
                dbc.CardImg(src=cover_image_url,style={"height":"14rem"}),
                dbc.CardBody(html.H4(proj,className="card-title"),style={"textAlign":"center"})
            ],style={"height":"18rem","width": "18rem"}),style={"float":"left","paddingLeft":"20px"}
        )
        logging.debug("SBDEBUG: finished createing project card")
        project_cards.append(curr_card)

    return project_cards






def populate_files(username,project_name):
    """
    Populate the file list for a given project and user.

    This function retrieves the list of image files for the specified project and user.
    It generates a list of Dash Bootstrap Components (dbc) ListGroupItems for each file, 
    indicating whether the file has masks or segmented images.

    :param username: The username of the user.
    :param project_name: The name of the project.
    :return: A list of dbc.ListGroupItem objects representing the files.
    """
    image_list = []

    # Create an SB_project object for the specified project
    project_object = SB_project(username,project_name)

    # Get the list of image filenames for the project
    filelist = project_object.get_image_names()
    
    for file_idx in range(len(filelist)):
        file = SB_project_image(username,project_name,filelist[file_idx])
        item_color = None

        # Check if the file has masks (it's "ready") and set item color to primary if true
        if file.has_masks():
            item_color = "primary"

        # Check if the file has segmented images (it's "done") and set item color to success if true
        if file.has_segmented_image():
            item_color = "success"

        image_list.append(dbc.ListGroupItem(dbc.Row([
                dbc.Col(dcc.Checklist(options=[""],value=[],id={'type':"file-item-checklist",'index':file.get_filename()}),width="auto"),
                dbc.Col(html.Div(file.get_filename(),id={'type':"file-item",'index':file.get_filename()})),
            ]),color=item_color)
        )
    
    return image_list



def get_label_options(username,project):
    """
    Retrieve class label options for a given project.

    This function fetches the label classes from the database for the specified project.
    It extracts the names of the classes and returns them as a list of label options.

    :param username: The username of the user.
    :param project: The name of the project.
    :return: A list of label names.
    """
    classes_from_db = get_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project),default_return={"classes":[]})
    classes_list = classes_from_db["classes"]

    # they all have a name and a color, but we just need the names in this function
    label_options = [n['name'] for n in classes_list]
    return label_options


def get_label_colors_dict(username,project):
    """
    Retrieve a dictionary of class label colors for a given project.

    This function fetches the label classes from the database for the specified project and user.
    It creates a dictionary mapping label names to their corresponding RGB color tuples.

    :param username: The username of the user.
    :param project: The name of the project.
    :return: A dictionary mapping label names to RGB color tuples.
    """
    label_colors_dict = {}
    classes_from_db = get_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project),default_return={"classes":[]})
    classes_list = classes_from_db["classes"]

    # Populate the dictionary with label names and their corresponding color tuples
    for entry in classes_list:
        label_colors_dict[entry["name"]] = tuple(entry["color"])
    return label_colors_dict

