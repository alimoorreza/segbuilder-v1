
import cv2
from dash import html, dcc
import dash_bootstrap_components as dbc
import datetime
import logging 

from .image_utils import encode_img_for_display, apply_mask_to_image
from ..project_models import SB_project, SB_project_image
from ..resources import get_db_item

IMG_WIDTH = 250
#IMG_HEIGHT = 400


def create_mask_cards(img, masks, labels, label_options = ["unlabeled"], new_masks=False, index_offset = 0):
    image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
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
    card_list = []
    #print("DEBUG: (create_mask_cards)")
    #print("\tlabels:",labels)
    #print("\tlen(labels), len(masks):",len(labels),len(masks))
    #if there aren't enough labels for all the masks,
    #we will just copy the last label and use it for the rest of the masks
    #only will work if there is at least one label
    if len(labels) < len(masks):
        labels = labels+([labels[-1]]*(len(masks)-len(labels)))
    for idx in range(len(masks)):
        label_idx = idx+index_offset
        curr_card = html.Div([
            html.Img(src='data:image/png;base64,{}'.format(encode_img_for_display(apply_mask_to_image(image,masks[idx]["segmentation"]))),width=IMG_WIDTH),
            dbc.Button(html.I(className="bi bi-box-arrow-in-up-left"),color="secondary",id={'type':front_button_id_type,'index':label_idx},style={"float":"left"}),
            dbc.Button(html.I(className="bi bi-pencil-fill"),color="info",id={'type':edit_button_id_type,'index':label_idx},style={"float":"left"}),
            dbc.Button(html.I(className="bi bi-backspace"),color="danger",id={'type':delete_button_id_type,'index':label_idx},style={"float":"left"}),
            dcc.Dropdown(options=label_options,value=labels[idx],id={'type':id_type,'index':label_idx},style={"float":"left","width":(IMG_WIDTH-91)})
        ],style={"width":(IMG_WIDTH+10)},id={'type':card_id_type,'index':label_idx},className="float-child")
        card_list.append(curr_card)
    
    
    return card_list






def populate_project_cards(username):
    logging.debug("SBDEBUG: inside populate_project_cards")
    project_cards = []
    curr_projects = []


    #!! moved this code to database.py - delete after testing
    #dynamodb = get_dynamodb_resource()
    #projects_table = dynamodb.Table("projects")
    #curr_projects_response = projects_table.get_item(Key={"username":username})
    #logging.debug("In populate_project_cards: curr_projects_response %s",curr_projects_response)
    #if "Item" in curr_projects_response:
    #    curr_projects = curr_projects_response["Item"]["projects"]

    db_results = get_db_item(table_name="projects",key_name="username",key_value=username,default_return={"projects":[]})
    curr_projects = db_results["projects"]
    print("CURR PROJECTS:",curr_projects)

    
    #for prefix in result.search('CommonPrefixes'):
    for proj in curr_projects:
        #logging.debug("prefix",prefix)
        #foldername = prefix.get('Prefix')[len(username)+1:-1]
        sb_project = SB_project(username,proj)
        logging.debug("SBDEBUG: about to create a project card")
        curr_card = html.Div(id={'type':"project-card",'index':proj},children=dbc.Card([
            dbc.CardImg(src=sb_project.get_cover_image_url(),style={"height":"14rem"}),
            dbc.CardBody(html.H4(proj,className="card-title"),style={"textAlign":"center"})
        ],style={"height":"18rem","width": "18rem"}),style={"float":"left","paddingLeft":"20px"})
        logging.debug("SBDEBUG: finished createing project card")
        project_cards.append(curr_card)

    return project_cards






def populate_files(username,project_name):
    image_list = []
    project_object = SB_project(username,project_name)
    filelist = project_object.get_image_names()
    
    for file_idx in range(len(filelist)):
        file = SB_project_image(username,project_name,filelist[file_idx])
        item_color = None
        if file.has_masks():
            item_color = "primary"
        if file.has_segmented_image():
            item_color = "success"
        image_list.append(dbc.ListGroupItem(dbc.Row([
                dbc.Col(dcc.Checklist(options=[""],value=[],id={'type':"file-item-checklist",'index':file.get_filename()}),width="auto"),
                dbc.Col(html.Div(file.get_filename(),id={'type':"file-item",'index':file.get_filename()})),
            ]),color=item_color)
        )
    
    
    return image_list



def get_label_options(username,project):

    classes_from_db = get_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project),default_return={"classes":[]})
    classes_list = classes_from_db["classes"]
    label_options = [n['name'] for n in classes_list]
    return label_options


def get_label_colors_dict(username,project):
    label_colors_dict = {}
    classes_from_db = get_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project),default_return={"classes":[]})
    classes_list = classes_from_db["classes"]

    for entry in classes_list:
        label_colors_dict[entry["name"]] = tuple(entry["color"])
    return label_colors_dict

