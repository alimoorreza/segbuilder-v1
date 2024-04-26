from dash import html, dcc
import dash_bootstrap_components as dbc

IMG_HEIGHT = 400

def get_segbuilder_layout():
    return html.Div(children = [
        dbc.Tabs(id="tabs", active_tab="projects_tab", children = [
            dbc.Tab(tab_id="projects_tab",label="Projects",children=[
                dcc.Markdown("## Select project"),
                html.Div(id="new-project-card",
                        children=dbc.Card([
                            html.H1("+",style={"textAlign":"center","fontSize":"10rem","verticalAlign":"middle"}),
                ],style={"height":"18rem","width": "18rem"}),style={"float":"left","paddingLeft":"20px"}),
                html.Div(id="project-cards",children=[]),
                dbc.Modal(id="create-project-modal",is_open=False, children=[
                    dbc.ModalHeader(dbc.ModalTitle("Create new project")),
                    dbc.ModalBody([
                        dbc.Label("Project name (no spaces)"),
                        dbc.Input(type="text",id="create-project-name-input"),
                        html.Div(dbc.FormText("Project names must start with a letter and contain only letters, numbers, and underscores.",color="danger"),id="create-new-project-name-message",style={"display":"none"})
                    ]),
                    dbc.ModalFooter(
                        dbc.Button("Create",id="create-project-button",color="primary")
                    )
                ])
            ]),
            dbc.Tab(tab_id="classes_tab",label="Classes",children=[
                html.Br(),
                html.H3(id="project-name-display-on-classes"),
                html.Br(),
                dbc.Row([
                    dbc.Col([dbc.Button("Download Label Color Scheme",id="download-label-color-scheme-button"),
                        dcc.Download(id='label-color-scheme-download')
                ],align="start",width="auto"),
                    dbc.Col(dcc.Upload(id="label-color-scheme-upload",multiple=False,children=[
                            'Upload Label Color Scheme File',
                        ],
                        style={
                        'width': '33%',
                        'height': '36px',
                        # 'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'left-margin': '10px'
                        },
                    ),align="start"),
                ]),
                html.Br(),
                dbc.Form(dbc.Row([
                    dbc.Label("New Class label",width="auto"),
                    dbc.Col(
                        dbc.Input(id="class-label-input",placeholder="Enter label for a new class"),
                        className="me-3",
                        width=4
                    ),  
                    dbc.Label("Color",width="auto"),
                    dbc.Col(
                        dbc.Input(
                            type="color",
                            id="class-colorpicker",
                            value="#000000",
                            style={"width": 80, "height": 40},
                        ),width=2
                    ),
                    dbc.Col(dbc.Button("Submit", color="primary",id="new-class-label-button"), width="auto"),       
                ],className="g-2"),style={"marginLeft": "15px","width":"50rem"}),
                html.Br(),
                html.Div(id="label-color-map-display")
            ]),
            dbc.Tab(tab_id = "files_tab",label="Files",children=[
                dbc.Spinner(html.H3(id="project-name-display-on-files"),color="primary"),
                dcc.Upload(id="file-uploader",multiple=True,children=[
                    'Drag and Drop or Select Image File'
                ],
                style={
                'width': '50%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
                },
            ),
            dbc.Button(html.I(className="bi bi-arrow-repeat"),id="refresh-button",color="primary"),
            dbc.Button(dbc.Spinner("Download"),id="download-button",color="primary"),
            html.Div(dbc.Spinner(dcc.Download(id="download-zipfile"),color="primary")),

            dcc.Checklist(options=[" Select all"],value=[],id='select-all-checklist'),
            dbc.Toast(id="upload-notify",header="File uploaded",dismissable=True,is_open=False,style={"position": "fixed", "top": 66, "right": 10},),
            dbc.ListGroup(id="file-list-group",children=[]),
            ]),
            dbc.Tab(tab_id = "annotate_tab",label="Annotate",children=[
                html.H3(id="filename-display"),
                dbc.Row([
                    dbc.Col([
                            dcc.Graph(id="graph-draw",config={"modeBarButtonsToAdd": ["drawclosedpath","eraseshape"], "displaylogo":False},style={"width":"700px"}),],align="center"), #"drawcircle","drawopenpath",
                    dbc.Col(dbc.Spinner([
                        html.Img(src="",height=IMG_HEIGHT,id="mask-composite-image"),
                        html.Img(src="",height=IMG_HEIGHT,id="mask-image")
                    ],color="primary"),align="center"), 
                ]),
                html.Br(),
                html.Div([
                    dbc.Button("Generate Composite Mask Image",id="generate-composite-image-button",style={"marginLeft": "15px"}),
                    dbc.Button("Generate Manual Mask",id="generate-manual-mask-button",style={"marginLeft": "15px"}),
                    dbc.Button("Save",id="save-button",style={"marginLeft": "15px"}),
                    dbc.Toast(id="save-notify",header="File saved",dismissable=True,is_open=False,style={"position": "fixed", "top": 66, "right": 10},)
                ]),
                html.Br(),
                dbc.Spinner([html.Div(children=[],id="new-mask-display")],color="primary"),
                html.Div(children=[],id="mask-display",className="float-container")
            ]),
        ]),
        dcc.Store(id='mask-store'),
        dcc.Store(id="new-mask-store"),
        dcc.Store(id="drawings-store"),
        dcc.Store(id='closed-paths-store'),
        dcc.Store(id="selected-project"),
        dcc.Store(id="selected-image"),
        dcc.Store(id="mask-card-move-to-front"),
        dcc.Store(id="mask-move-to-front"),
        dcc.Store(id="new-project-has-been-created"),
    ])

