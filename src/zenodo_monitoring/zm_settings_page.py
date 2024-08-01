import json
import base64
from dash import html, dcc, ALL, ctx
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

from .zm_settings_data import SettingsData


class ZenodoMonitoringSettings:
    def __init__(self, app):
        self.app = app
        self.settings_data = SettingsData()  
    
    def create_layout(self):
        return html.Div([
            dcc.Store(id='local-settings-data', storage_type='local'),

            html.H2("Combine multiple classes to create your own custom category"),

            dbc.FormFloating([
                dbc.Row([
                    # Input name.
                    dbc.Col([
                        html.H4(children="Custom category name"),
                        dbc.Input(id="group_name", type="text", maxlength=40, minlength=1),
                        dbc.FormFeedback("Please fill this input or change name.", type="invalid"),

                    ], width=3),

                    # Model picker.
                    dbc.Col([
                        html.H4(children="Choose your multilabel model."),
                        dbc.Select(
                            self.settings_data.model_dash_format,
                            self.settings_data.model_dash_format[0]["value"],
                            id='model_select_settings'
                        )
                    ], width=3),

                    # Model class picker.
                    dbc.Col([
                        html.H4(children="Select the classes you want to merge."),
                        dcc.Dropdown(
                            self.settings_data.classes_map_by_model_id[self.settings_data.model_dash_format[0]["value"]],
                            id='class_select_settings',
                            multi=True,
                            placeholder="If not filled, no class are selected."
                        ),
                    ]),
                ], class_name=["my-3 p-3"]),
                
                dbc.Stack([
                    # Button to create a group.
                    dbc.Button(html.Span(["Create custom category ", html.I(className="fa-solid fa-plus")]), id="btn-submit", color="info"),

                    # Button to import custom classes.
                    html.Div([
                        dcc.Upload(
                            id="upload_custom", 
                            children=[dbc.Button(html.Span(["Import ", html.I(className="fa-solid fa-file-import")]), id="btn-import", color="secondary")],
                            multiple=True,
                            max_size=100000000
                        ),
                    ], className="ms-auto"),

                    # Export custom classes.
                    dbc.Button(html.Span(["Export ", html.I(className="fa-solid fa-file-export")]), id="btn-export", color="secondary"),
                    dcc.Download(id="dl-export")

                ], direction="horizontal", gap=3)
            ]),

            dbc.Row(class_name=["mt-3 pt-3"], id="row_group_table"),
            
            dbc.Toast(
                "Please select some classes to create a category.",
                id="warning-toast-settings",
                header="No class to create custom category",
                is_open=False,
                dismissable=True,
                duration=10000,
                icon="danger",
                style={"position": "fixed", "bottom": 20, "right": 10, "width": 350},
            ),
        ])
    
    def register_callbacks(self):

        # Check if input name is valid.
        @self.app.callback(
            Output("group_name", "invalid"),
            [Input("group_name", "value"), Input("model_select_settings", "value")],
            prevent_initial_call=True,
        )
        def check_validity(text, model_id):
            return not text or (text, model_id) in self.settings_data.group_name_and_ids

        # Manage to add or delete a custom category.
        @self.app.callback(
            [
                Output("warning-toast-settings", "is_open"),
                Output("group_name", "value"),
                Output("class_select_settings", "value"),
                Output("local-settings-data", "data")
            ],
            [
                Input({'type':'delete-row','index':ALL}, 'n_clicks'),
                Input("btn-submit", "n_clicks"), 
            ],
            [
                State("group_name", "value"), 
                State("model_select_settings", "value"),
                State("class_select_settings", "value")
            ],
            prevent_initial_call=True,
        )
        def table_trigger_manager(n_1, n_2, group_name, model_id, class_ids):

            # Work with add button.
            if isinstance(ctx.triggered_id, str) and ctx.triggered_id == "btn-submit":

                # We don't have enough information to create a class.
                if not class_ids or not group_name or (group_name, model_id) in self.settings_data.group_name_and_ids:
                    return [True, group_name, class_ids, self.settings_data.serialize_data()]

                # Add new group and save into localstorage.
                group_name_formatted = group_name.replace(" ", "_")
                self.settings_data.add_group(group_name_formatted, model_id, class_ids)
                return [False, "", None, self.settings_data.serialize_data()]
            
            # Work with delete button.
            elif isinstance(ctx.triggered_id, dict) and set(n_1) != {None}:      # We will only click once a time on delete button, so we have always a list of None
                # Delete and save into local storage.
                gn_to_del, model_id_to_del = ctx.triggered_id['index'].split("_/\_")
                self.settings_data.delete_group(gn_to_del, int(model_id_to_del))
                return [False, group_name, class_ids, self.settings_data.serialize_data()]
            
            # Default work.
            return [False, group_name, class_ids, self.settings_data.serialize_data()]


        # Trigger when page load or when add data in localstorage.
        # Render table of custom category
        @self.app.callback(
            Output("row_group_table", "children"),
            Input("local-settings-data", "modified_timestamp"),
            State("local-settings-data", 'data')
        )
        def on_data(ts, data):
            # Get data from local storage and update settings-data object.
            data = data or {}
            self.settings_data.set_serialized_data(data)

            return self.generate_table()
        
        
        # Change class options with model.
        @self.app.callback(
            Output('class_select_settings', 'options'),
            Input('model_select_settings', 'value')
        )
        def update_classes_on_model_change(model_id):
            # Return on page load or model change.
            return self.settings_data.get_class_by_model(int(model_id))


        # Download a serialized_json
        @self.app.callback(
            Output("dl-export", "data"),
            Input("btn-export", "n_clicks"),
            prevent_initial_call=True,
        )
        def dl_export_custom_classes(n_clicks):
            return dict(content=json.dumps(self.settings_data.serialize_data()), filename="custom_class.json")


        # Parse a serialized file from user input.
        @self.app.callback(
            [
                Output("local-settings-data", "data", allow_duplicate=True),
                Output('upload_custom', 'contents'),
            ],
            Input('upload_custom', 'contents'),
            State('upload_custom', 'filename'),
            State('upload_custom', 'last_modified'),
            prevent_initial_call=True
        )
        def update_output(list_of_contents, list_of_names, list_of_dates):
            if list_of_contents is not None:
                for c, n, d in zip(list_of_contents, list_of_names, list_of_dates):
                    self.parse_json_custom_class(c, n, d) 

            return self.settings_data.serialize_data(), None


    def parse_json_custom_class(self, contents, filename, date):
        print(f"[INFO] Try to import {filename}")
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            custom_classes = json.loads(decoded.decode('utf-8'))
            self.settings_data.set_and_verify_serialize_data(custom_classes)
        except Exception as e:
            print(e)
        

    def generate_table(self):
        """ Generate a table with a delete button. """
        if self.settings_data.group_name_and_ids == {}:
            return []
        title = html.H2("Table of your group.")
        
        table_header = html.Thead(html.Tr([html.Th("Group name"), html.Th("Class name"), html.Th("Model"), html.Th("")]))
        rows = []
        for group_name, model_id in self.settings_data.group_name_and_ids:
            # Get class name.
            classes_ids = self.settings_data.group_name_and_ids.get((group_name, model_id), [])
            classes = [self.settings_data.ml_classes_manager.get_class_by_id(id) for id in classes_ids]
            
            # Model name.
            model_name = classes[0].ml_model.name if classes else ''

            # Create delete button.
            btn = dbc.Button(
                html.I(className="fa-solid fa-trash"),
                id={'type':"delete-row", "index": f"{group_name}_/\_{model_id}"}, # Custom id to get group_name and model_id
                color='danger',
            )
            
            # Append all to row.
            rows.append(html.Tr([
                html.Td(group_name),
                html.Td(', '.join([cls.name for cls in classes])),
                html.Td(model_name),
                html.Td(btn, style={'width': '1%'})
            ]))
        table = dbc.Table(id="group_table", children=[table_header, html.Tbody(rows)], bordered=True, striped=True)
        return title, table