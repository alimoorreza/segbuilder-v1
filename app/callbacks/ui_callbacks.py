
from dash.dependencies import Input, Output, State, ALL, MATCH
from dash import Dash, html, dcc, ctx, no_update, callback_context
import dash_bootstrap_components as dbc
import base64
import simplejson as json
import io
from dash.exceptions import PreventUpdate
import re
import plotly.express as px
import numpy as np
import logging
import cv2
import plotly.graph_objs as go

from ..data import get_user_from_session
#from ..resources import get_dynamodb_resource
from ..project_models import SB_project_image
from ..utils import populate_files, create_mask_cards, hex_to_rgb, make_composite_image, create_mask_from_paths, add_meta_info_to_masks, contours_from_mask, plotly_shapes_from_contours, get_label_options, get_label_colors_dict,  generate_label_cards
from ..resources import get_db_item, put_db_item

CANVAS_WIDTH = 600

def register_ui_callbacks(app):

    @app.callback(
            Output({'type': 'file-item-checklist', 'index': ALL}, 'value'),
            Input('select-all-checklist','value'),
            State({'type': 'file-item-checklist', 'index': ALL}, 'options'),
            prevent_initial_call = True
    )
    def select_deselect_all_files(select_all,filename_options):
        """
        Callback to handle select-all (or to deselect-all) of the files check boxes in a project

        Outputs:
        - file-item-checklist: a list of check box values for each file.

        Inputs:
        - select-all-checklist (select_all): It's a list of size one representing the value of the "select all" check list.

        States:
        - file-item-checklist (filename_options): List of labels associated with the check boxes for each image - these are
            dummies with the "" value - we're showing the label separately
        """

        if select_all != []:
            # select the dummy option "" for each of the checklist items
            return [options for options in filename_options]
        else:
            # unselect each check list
            return [[] for options in filename_options]



    @app.callback(
            Output('create-project-modal','is_open'),
            Input('new-project-card','n_clicks'),
            Input('tabs','active_tab'),
            prevent_initial_call = True
    )
    def open_new_project_modal(n_clicks,active_tab):
        """
        Callback to handle showing the "create project" dialog (which is a modal component)

        Outputs:
        - create-project-modal: value of the is_open property of the modal

        Inputs:
        - new-project-card (n_clicks): Number of times the new project card (actually, its html div container) has been clicked
        - tabs (active_tab): the active tab - so we can close the modal if the user clicks another tab
        """
        if callback_context.triggered_id == 'new-project-card':
            if n_clicks:
                return True
        elif callback_context.triggered_id == 'tabs':
            return False
        return no_update



    @app.callback(
            Output("label-color-map-display","children"),
            Output("project-name-display-on-classes","children"),
            Output("project-name-display-on-files","children"),
            Input("selected-project","data"),
            Input("new-class-label-button","n_clicks"),
            Input("label-color-scheme-upload","contents"),
            State("class-label-input","value"),
            State("class-colorpicker","value"),
            prevent_initial_call = True
    )
    def populate_classes_tab(project_name,n_clicks,json_file_contents,new_label,new_color):
        """
        Callback to populate the classes tab with colors/labels.
        It also displasy the project name on both the classes and files tabs.

        Outputs:
        - label-color-map-display: Updated display of label color mapping cards.
        - project-name-display-on-classes: Display of the project name on the classes tab.
        - project-name-display-on-files: Display of the project name on the files tab.

        Inputs:
        - selected-project (project_name): The name of the selected project.
        - new-class-label-button (n_clicks): Number of clicks on the 'New Class Label' button.
        - label-color-scheme-upload (json_file_contents): Contents of the uploaded JSON file for label color schemes.

        States:
        - class-label-input (new_label): Value user has typed into the new class label input field.
        - class-colorpicker (new_color): Value of the color the user has picked for the new class label.
        """
        logging.debug("POPULATECLASSES: callback_context.triggered_id %s",callback_context.triggered_id)
        username = get_user_from_session()

        # handle when the user has uploaded JSON file with the label-color scheme
        if callback_context.triggered_id == "label-color-scheme-upload":
            if json is not None:
                content_type, content_string = json_file_contents.split(',')
                decoded = base64.b64decode(content_string)
                data = json.load(io.StringIO(decoded.decode('utf-8')))

                put_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project_name),item_name="classes",item_value=data)

                label_cards = generate_label_cards(username,project_name)
                return label_cards, no_update, no_update
            
        # handle when the user has selected a new project
        elif callback_context.triggered_id == "selected-project":
            if project_name:
                username = get_user_from_session()
                label_cards = generate_label_cards(username,project_name)
                return label_cards, project_name, project_name
            
        # handle when the user creates a new class (label and color) using the UI
        elif callback_context.triggered_id == "new-class-label-button":
            if n_clicks:

                # get the current label-color scheme from the database
                db_label_records = get_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project_name),default_return=[])
                label_records = db_label_records["classes"]

                # add the new label-color pair onto the list
                label_records.append({"name":new_label,"color":hex_to_rgb(new_color)})

                # put the updated list back in the database
                put_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+project_name),item_name="classes",item_value=label_records)

                label_cards = generate_label_cards(username,project_name)
                return label_cards, no_update, no_update

        return no_update, no_update, no_update

    @app.callback(
            Output('file-list-group','children'),
            Output('selected-project','data'),
            Output("selected-image","data"),
            Output("tabs","active_tab"),
            Output("filename-display","children"),
            Output("create-new-project-name-message","style"),
            Output('new-project-has-been-created','data'),
            
            Input({'type': 'file-item', 'index': ALL}, 'n_clicks'),
            Input({'type': 'project-card', 'index': ALL}, 'n_clicks'),
            Input("create-project-button","n_clicks"),
            Input("upload-notify","children"),
            Input("refresh-button","n_clicks"),


            #State('session','data'),
            State("create-project-name-input","value"),
            State('selected-project','data'),
            prevent_initial_call = True
    )
    def tab_navigation(files_n_clicks,project_cards_n_clicks,create_project_n_clicks,upload_notification,refresh_button_clicks,new_project_name,curr_selected_project):
        logging.debug("SBDEBUG: tab_navigation callback_context.triggered_id %s",callback_context.triggered_id)
        logging.debug(" SBDEBUG: create_project_n_clicks %s",create_project_n_clicks)
        logging.debug(" SBDEBUG: project_cards_n_clicks %s",project_cards_n_clicks)
        username = get_user_from_session()
        logging.debug(" SBDEBUG: got username from session %s",username)
        if username is None or not callback_context.triggered: # or selected_project is None:
            logging.debug(" SBDEBUG: username was none, we're preventing update")
            raise PreventUpdate
        elif callback_context.triggered_id == "create-project-button" and create_project_n_clicks:
            #!!TODO: check if project name already exists
            if new_project_name == "" or not re.match(r'^[A-Za-z][A-Za-z0-9_]*$',new_project_name):
                return no_update, no_update, no_update, no_update, no_update, {"display":"block"}, no_update
            else:
                #curr_projects = []

                # get the current list of projects from the databse
                projects_db_item = get_db_item(table_name="projects",key_name="username",key_value=username,default_return={"projects":[]})
                curr_projects = projects_db_item["projects"]
                
                # add this new project name to that list
                curr_projects.append(new_project_name)

                # update the projects list in the database with the newly embiggened list
                put_db_item(table_name="projects",key_name="username",key_value=username,item_name="projects",item_value=curr_projects)

                # initialize the class labels so there is one label called "unlabeled" assigned the color black
                # and then put it into the project-classes database for this project
                project_init_classes = [{"name": "unlabeled","color": [0,0,0]}]
                put_db_item(table_name="project-classes",key_name="username-projectname",key_value=(username+"-"+new_project_name),item_name="classes",item_value=project_init_classes)

                #!! old code - delete after testing
                #dynamodb = get_dynamodb_resource()
                #projects_table = dynamodb.Table("projects")
                #curr_projects_response = projects_table.get_item(Key={"username":username})
                #if "Item" in curr_projects_response:
                #    curr_projects = curr_projects_response["Item"]["projects"]
                #logging.debug("curr_projects %s",curr_projects)
                #curr_projects.append(new_project_name)
                #projects_table.put_item(Item={"username":username,"projects":curr_projects})
                #project_init_classes = [{"name": "unlabeled","color": [0,0,0]}]
                #classes_table = dynamodb.Table("project-classes")
                #classes_table.put_item(Item={"username-projectname":(username+"-"+new_project_name),"classes":project_init_classes})

                return populate_files(username,new_project_name), new_project_name, None, "classes_tab", no_update, {"display":"none"}, True
        elif "type" in callback_context.triggered_id and callback_context.triggered_id["type"] == 'project-card' and not all(n is None for n in project_cards_n_clicks):
            project_name = callback_context.triggered_id["index"]
            logging.debug("SBDEBUG: tab_navigation callback, project selected:"+str(project_name))
            return populate_files(username,project_name), project_name, None, "files_tab", no_update, no_update, no_update
        elif "type" in callback_context.triggered_id and callback_context.triggered_id["type"] == 'file-item':
            filename = callback_context.triggered_id["index"]
            logging.debug("filename %s",filename)
            return no_update, no_update, filename, "annotate_tab", filename, no_update, no_update
        elif callback_context.triggered_id == "upload-notify":
            return populate_files(username,curr_selected_project), no_update, no_update, no_update, no_update, no_update, no_update 
        elif callback_context.triggered_id == "refresh-button" and refresh_button_clicks:
            return populate_files(username,curr_selected_project), no_update, no_update, no_update, no_update, no_update, no_update
        elif callback_context.triggered[0]["value"] is None: #!! Do I still need this?
            raise PreventUpdate
        else:
            logging.debug("uncaught trigger in tab_navigation")
            raise PreventUpdate

            



    @app.callback(
        Output({'type': 'label-dropdown', 'index': MATCH}, 'value'),
        Output({'type': 'mask-card', 'index': MATCH}, 'style'),
        Input({'type': 'delete-button', 'index': MATCH}, 'n_clicks'),
        prevent_initial_call=True
    )
    def delete_mask_card(n_clicks):
        if not n_clicks is None:
            return "DELETE", {'display':'none'}
        return no_update, no_update

    @app.callback(
        Output({'type': 'new-label-dropdown', 'index': MATCH}, 'value'),
        Output({'type': 'new-mask-card', 'index': MATCH}, 'style'),
        Input({'type': 'new-delete-button', 'index': MATCH}, 'n_clicks'),
        prevent_initial_call=True
    )
    def delete_new_mask_card(n_clicks):
        if not n_clicks is None:
            #logging.debug("deleting mask card",callback_context.triggered_id)
            return "DELETE", {'display':'none'}
        return no_update, no_update

    @app.callback(
            Output({'type': 'delete-button', 'index': ALL}, 'n_clicks'),
            Output("mask-card-move-to-front","data"),
            Output("mask-move-to-front","data"),
            Input({'type': 'front-button', 'index': ALL}, 'n_clicks'),
            State('selected-project','data'),
            State('selected-image','data'),
            State({'type': 'label-dropdown', 'index': ALL}, 'value'),
            State('new-mask-display','children'),
            #State("session","data"),
            prevent_initial_call=True
    )
    def front_button_handle(n_clicks,selected_project,selected_image_name,curr_labels,current_new_masks_display):
        logging.debug("front_button_handle triggered with %s",callback_context.triggered_id)
        if not all(n is None for n in n_clicks):
            #logging.debug("something wasn't None")
            username = get_user_from_session()
            mask_num = callback_context.triggered_id["index"]
            image_obj = SB_project_image(username,selected_project,selected_image_name)
            image = image_obj.load_image()
            mask_to_move = image_obj.load_masks()[mask_num]
            label_options = get_label_options(username,selected_project)
            new_card = create_mask_cards(image,[mask_to_move],[curr_labels[mask_num]],label_options=label_options,new_masks=True,index_offset=len(current_new_masks_display))
            delete_clicks = [None]*len(n_clicks)
            delete_clicks[mask_num] = 1
            return delete_clicks, new_card, mask_to_move
        return [no_update]*len(n_clicks), no_update, no_update

    @app.callback(
            Output("edit-button-polygon-data","data"),
            Input({'type': 'edit-button', 'index': ALL}, 'n_clicks'),
            State('selected-project','data'),
            State('selected-image','data'),
            prevent_initial_call=True
    )
    def edit_button_handle(n_clicks,selected_project,selected_image_name):
        logging.debug("edit_button_handle triggered with %s",callback_context.triggered_id)
        if not all(n is None for n in n_clicks):
            #logging.debug("something wasn't None")
            username = get_user_from_session()
            mask_num = callback_context.triggered_id["index"]
            image_obj = SB_project_image(username,selected_project,selected_image_name)
            #image = image_obj.load_image()
            mask_to_edit = image_obj.load_masks()[mask_num]
            contours = contours_from_mask(mask_to_edit["segmentation"])
            shapes = plotly_shapes_from_contours(contours)

            logging.debug("SHAPES for editing: %s",shapes)
            return shapes
        return no_update

    @app.callback(
        Output('mask-display', 'children'),
        Output('graph-draw','figure'),
        Output('new-mask-display','children'),
        Output('new-mask-store','data'),
        Output("mask-composite-image","src"),
        Output("mask-image","src"),
        #Output({'type': 'new-delete-button', 'index': ALL}, 'n_clicks'),

        
        Input('selected-image','data'),
        Input('generate-manual-mask-button','n_clicks'),
        Input("generate-composite-image-button","n_clicks"),
        Input("mask-card-move-to-front","data"),
        Input({'type': 'new-front-button', 'index': ALL}, 'n_clicks'),
        Input("save-notify",'children'),
        Input("edit-button-polygon-data","data"),
        


        State('selected-project','data'),
        State('new-mask-store','data'),
        State('new-mask-display','children'),
        State('closed-paths-store','data'),
        State({'type': 'label-dropdown', 'index': ALL}, 'value'),
        State({'type': 'new-label-dropdown', 'index': ALL}, 'value'),
        State("mask-move-to-front","data"),
        State('graph-draw','figure'),
        #State("session","data"),
        prevent_initial_call=True
    )
    def update_annotation_page(selected_image_name,generate_manual_n_clicks,gen_composite_n_clicks,new_front_mask_card,nfb_n_clicks,save_notify,edit_button_polygon_data,selected_project,current_new_masks,current_new_display_cards,closed_paths,labels,new_labels,new_front_mask,curr_fig_image):
        username = get_user_from_session()
        no_update_ALL = [no_update]*len(nfb_n_clicks)
        logging.debug("update_annotation_page selected_image_name %s",selected_image_name)

        if callback_context.triggered_id == "edit-button-polygon-data":
            if isinstance(curr_fig_image, dict): #check if the image ends up getting saved as a dict in dcc.Store
                curr_fig_image = go.Figure(curr_fig_image)
            curr_fig_image.update_layout(shapes=edit_button_polygon_data,dragmode="drawclosedpath")
            #print(edit_button_polygon_data)
            #curr_fig_image.show()
            return no_update, curr_fig_image, no_update, no_update, no_update, no_update
        #load everything if they selected a new image or saved
        elif callback_context.triggered_id == "selected-image" or callback_context.triggered_id == "save-notify":
            if not selected_image_name:
                raise PreventUpdate
                #return None, None, None, None, None, None #, no_update_ALL
            else:
                pen_color = "white"
                image_obj = SB_project_image(username,selected_project,selected_image_name)
                if image_obj.has_masks():
                    
                    image = image_obj.load_image() 
                    masks = image_obj.load_masks()
                    labels = image_obj.load_labels()
                    label_options = get_label_options(username,selected_project)
                    display_cards = create_mask_cards(image,masks,labels,label_options=label_options)
                    fig_image = px.imshow(image)
                    fig_image.update_layout(dragmode="drawclosedpath",
                                            width=CANVAS_WIDTH,
                                            height=1000,
                                            #margin=dict(t=0, b=5, l=5, r=5),  # Set the top margin to 0
                                            #title=dict(text='', pad=dict(t=0, b=0, l=0, r=0)),
                                            newshape=dict(line=dict(color=pen_color)))
                    #logging.debug("fig_image",fig_image)
                    segmented_image = ""
                    composite_image = ""
                    if image_obj.has_segmented_image():
                        composite_image, segmented_image = make_composite_image(image,image_obj.load_segmented_image())
                    return display_cards, fig_image, [], None, composite_image, segmented_image #, no_update_ALL
                
                else:
                    
                    logging.debug("loading %s without pre-computed masks",selected_image_name)
                    image = image_obj.load_image() 
                    fig_image = px.imshow(image)
                    fig_image.update_layout(dragmode="drawclosedpath",
                                                #width=CANVAS_WIDTH,
                                                height=1000,
                                                #margin=dict(t=0, b=5, l=5, r=5),  # Set the top margin to 0
                                                #title=dict(text='', pad=dict(t=0, b=0, l=0, r=0)),
                                                newshape=dict(line=dict(color=pen_color)))
                    segmented_image = ""
                    composite_image = ""
                    if image_obj.has_segmented_image():
                        composite_image, segmented_image = make_composite_image(image,image_obj.load_segmented_image())

                    return [], fig_image, [], None, composite_image, segmented_image #, no_update_ALL
        
        elif callback_context.triggered_id == "generate-manual-mask-button":
            image_obj = SB_project_image(username,selected_project,selected_image_name)
            image = image_obj.load_image()
            logging.debug("closed_paths %s",closed_paths)
            new_mask = create_mask_from_paths(closed_paths,image.shape)
            masks_meta = add_meta_info_to_masks([new_mask])
            label_options = get_label_options(username,selected_project)
            #logging.debug("label_options",label_options)
            new_row = create_mask_cards(image,masks_meta,[label_options[0]],label_options=label_options,new_masks=True,index_offset=len(current_new_display_cards))
            new_display_cards = new_row
            if current_new_display_cards:
                new_display_cards += current_new_display_cards
            new_masks_store = masks_meta
            if current_new_masks:
                new_masks_store += current_new_masks
            return no_update, no_update, new_display_cards, new_masks_store, no_update, no_update #, no_update_ALL
        

        elif callback_context.triggered_id == "generate-composite-image-button":
            image_obj = SB_project_image(username,selected_project,selected_image_name)
            image = image_obj.load_image()
            masks = image_obj.load_masks()
            logging.debug("masks loaded")
            mask_image = np.zeros_like(image)
            label_colors_dict = get_label_colors_dict(username,selected_project)
            

            for i in range(len(masks)-1,-1,-1):
                #logging.debug("i",i)
                curr_label = labels[i]
                #logging.debug("curr_label",curr_label)
                if curr_label != "DELETE":
                    curr_mask = np.array(masks[i]["segmentation"])
                    
                    color = label_colors_dict[curr_label]
                    colored_mask = np.zeros_like(image)
                    colored_mask[curr_mask > 0] = color
                    mask_image = np.where(curr_mask[..., np.newaxis] > 0, colored_mask, mask_image)

            if current_new_masks:
                for i in range(len(current_new_masks)-1,-1,-1):
                    curr_label = new_labels[i]
                    if curr_label != "DELETE":
                        curr_mask = np.array(current_new_masks[i]["segmentation"])
                        color = label_colors_dict[curr_label]
                        colored_mask = np.zeros_like(image)
                        colored_mask[curr_mask > 0] = color
                        mask_image = np.where(curr_mask[..., np.newaxis] > 0, colored_mask, mask_image)

            composite_image, segmented_image = make_composite_image(image,mask_image)


            return no_update, no_update, no_update, no_update, composite_image, segmented_image #, no_update_ALL
        
        elif callback_context.triggered_id == "mask-card-move-to-front":
            new_display_cards = new_front_mask_card
            if current_new_display_cards:
                new_display_cards += current_new_display_cards
            new_masks_store = [new_front_mask]
            if current_new_masks:
                new_masks_store += current_new_masks
            return no_update, no_update, new_display_cards, new_masks_store, no_update, no_update #, no_update_ALL
        

        elif 'type' in callback_context.triggered_id and callback_context.triggered_id["type"] == "new-front-button" and not(all(n is None for n in nfb_n_clicks)):
            image_obj = SB_project_image(username,selected_project,selected_image_name)
            image = image_obj.load_image()
            mask_num = callback_context.triggered_id["index"]
            new_front_mask = current_new_masks[mask_num]
            current_new_display_cards.pop(mask_num)
            label_options = get_label_options(username,selected_project)
            new_display_cards = create_mask_cards(image,[new_front_mask],[new_labels[mask_num]],label_options=label_options,new_masks=True,index_offset=len(current_new_display_cards))
            if current_new_display_cards:
                new_display_cards += current_new_display_cards
            new_masks_store = [new_front_mask]
            if current_new_masks:
                new_masks_store += current_new_masks
            new_delete_clicks = [None]*len(nfb_n_clicks)
            new_delete_clicks[mask_num] = 1
            return no_update, no_update, new_display_cards, new_masks_store, no_update, no_update #, new_delete_clicks

        logging.debug("uncaught context:  %s",callback_context.triggered_id)
        return no_update, no_update, no_update, no_update, no_update, no_update #, no_update_ALL

    @app.callback(
        #Output('canvas-message', 'children'),
        Output('drawings-store','data'),
        Output('closed-paths-store','data'),
        Input('graph-draw', 'relayoutData'),
        #State('image-store','data'),
        #State('canvas','height'),
        #State('canvas','width'),
        prevent_initial_call=True
    )
    def update_click_coordinates(shape_data):
        #print("SHAPE DATA",shape_data)
        #image = np.array(image)
        #image = image.astype(np.uint8)
        #logging.debug(type(shape_data))
        logging.debug("shape data  %s",shape_data)
        #image_width = image.shape[0]
        #image_height = image.shape[1]

        #image_scale_factor = image_width/CANVAS_WIDTH
        
        #logging.debug("image:",image.shape)
        #logging.debug("canvas:",canvas_height,", ",canvas_width)
        coords = []
        closed_paths = []
        if "shapes" in shape_data:
            for shape in shape_data["shapes"]:
                if shape["type"] == "circle":
                    include = 1
                    if shape["line"]["color"] == "red":
                        include = 0 
                    x = (shape["x0"]+shape["x1"])/2
                    y = (shape["y0"]+shape["y1"])/2
                    coords.append([include,x,y])
                if shape["type"] == "path":
                    #closed path
                    if shape["path"][-1] == "Z":
                        indices_str = [el.replace("M", "").replace("Z", "").split(",") for el in shape["path"].split("L")]
                        closed_path_indices = [(float(p[0]),float(p[1])) for p in indices_str]
                        closed_paths.append(closed_path_indices)
                    else:
                        include = 1
                        if shape["line"]["color"] == "red":
                            include = 0 
                        indices_str = [el.replace("M", "").replace("Z", "").split(",") for el in shape["path"].split("L")]
                        indices_float = [[include,float(p[0]),float(p[1])] for p in indices_str]
                        #logging.debug(indices_float)
                        coords += indices_float
        for k in shape_data:
            if 'shapes[' in k and '].path' in k and shape_data[k][-1] == "Z":
                indices_str = [el.replace("M", "").replace("Z", "").split(",") for el in shape_data[k].split("L")]
                closed_path_indices = [(float(p[0]),float(p[1])) for p in indices_str]
                closed_paths.append(closed_path_indices)
        if len(coords) == 0:
            coords = no_update
        if len(closed_paths) == 0:
            closed_paths = no_update
        return coords, closed_paths
