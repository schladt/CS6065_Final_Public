
from dash import Dash, html, dcc, dash_table
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import State
from dash_extensions.enrich import Output, DashProxy, Input, MultiplexerTransform
from sqlalchemy import Table, create_engine
from sqlalchemy.sql import select
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import warnings
import os
from flask_login import login_user, logout_user, current_user, LoginManager, UserMixin
import configparser
import plotly.express as px
import pandas as pd

import base64
import io

warnings.filterwarnings("ignore")

####################################
# DATABASE Setup
####################################

username = '<database username>'
password = '<database password>'
database = '<database name>'
hostname = '<database host / address>'
root_ca = '<database ssl ca cert>'

db_uri = f"mysql+pymysql://{username}:{password}@{hostname}/{database}"

engine = create_engine(
   f"mysql+pymysql://{username}:{password}@{hostname}/{database}",
   connect_args = {
    "ssl": {
            "ssl_ca": root_ca
        }
   }
)

db = SQLAlchemy()
config = configparser.ConfigParser()

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True, nullable = False)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))
Users_tbl = Table('users', Users.metadata)

####################################
# Application Setup
####################################

external_stylesheets = [
    dbc.themes.FLATLY,
    'https://codepen.io/chriddyp/pen/bWLwgP.css'
]


app = DashProxy(__name__, external_stylesheets=external_stylesheets, transforms=[MultiplexerTransform()])
app.title = 'CS 5165/6065 Final'


server = app.server
app.config.suppress_callback_exceptions = True
# config
server.config.update(
    SECRET_KEY=os.urandom(12),
    SQLALCHEMY_DATABASE_URI=db_uri,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MYSQL_SSL_CA = root_ca
)
db.init_app(server)
# Setup the LoginManager for the server
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = '/login'
#User as base
# Create User class with UserMixin
class Users(UserMixin, Users):
    pass


######################
# Figures
######################

figs = {} # container to hold all figures
households_df = None
transactions_df = None
products_df = None
transactions_combined_household_df = None
all_three_combined_df = None

def get_figures():
    global figs
    global households_df
    global transactions_df
    global products_df
    global transactions_combined_household_df
    global all_three_combined_df

    if all_three_combined_df is None:

        # debug_engine = create_engine('sqlite:///db.sql', echo=False)
        conn = engine

        # read data from database
        households_df = pd.read_sql('SELECT * FROM households', conn)
        transactions_df = pd.read_sql('SELECT * FROM transactions', conn)
        products_df = pd.read_sql('SELECT * FROM products', conn)

        # combine data frames
        transactions_combined_household_df = transactions_df.merge(households_df, on='HSHD_NUM', how='left')
        all_three_combined_df = transactions_combined_household_df.merge(products_df, on='PRODUCT_NUM', how='left')


    # units by year
    units_year_df = pd.DataFrame({
    'YEAR': ['2018', '2019', '2020', '2021'],
    'UNITS': [all_three_combined_df.loc[all_three_combined_df['YEAR'] == 2018, 'UNITS'].sum(),
                all_three_combined_df.loc[all_three_combined_df['YEAR'] == 2019, 'UNITS'].sum(),
                all_three_combined_df.loc[all_three_combined_df['YEAR'] == 2020, 'UNITS'].sum(),
                all_three_combined_df.loc[all_three_combined_df['YEAR'] == 2021, 'UNITS'].sum()]  
    })

    figs['fig_units_by_year'] = px.bar(units_year_df, x="YEAR", y="UNITS", title='Units by Year')

    # units by month
    units_month_df = pd.DataFrame({
    'PURCHASE_MONTH': [month for month in range(1, 13)],
    'UNITS': [
                all_three_combined_df.loc[all_three_combined_df['PURCHASE_MONTH'] == month, 'UNITS'].sum() for month in range(1, 13)
            ]  
    })
    figs['fig_units_by_month'] = px.line(units_month_df, x="PURCHASE_MONTH", y="UNITS", title="Units by Month", markers=True)

    # units by week
    units_week_df = pd.DataFrame({
    'WEEK_NUM': [week for week in range(1, 53)],
    'UNITS': [
                all_three_combined_df.loc[all_three_combined_df['WEEK_NUM'] == week, 'UNITS'].sum() for week in range(1, 53)
            ]  
    })
    figs['fig_units_by_week'] = px.line(units_week_df, x="WEEK_NUM", y="UNITS", title="Units by Week", markers=True)


    # units by store region
    units_region_df = pd.DataFrame({
    'STORE_REGION': list(all_three_combined_df['STORE_R'].unique()),
    'UNITS': [
                all_three_combined_df.loc[all_three_combined_df['STORE_R'] == store_region, 'UNITS'].sum() for store_region in list(all_three_combined_df['STORE_R'].unique())
            ]  
    })
    figs['fig_units_by_region'] = px.pie(units_region_df, values='UNITS', names='STORE_REGION', title='Units by Store Region')

    # spend by year
    spend_year_df = pd.DataFrame({
    'YEAR': ['2018', '2019', '2020', '2021'],
    'SPEND': [all_three_combined_df.loc[all_three_combined_df['YEAR'] == 2018, 'SPEND'].sum(),
                all_three_combined_df.loc[all_three_combined_df['YEAR'] == 2019, 'SPEND'].sum(),
                all_three_combined_df.loc[all_three_combined_df['YEAR'] == 2020, 'SPEND'].sum(),
                all_three_combined_df.loc[all_three_combined_df['YEAR'] == 2021, 'SPEND'].sum()]  
    })
    figs['fig_spend_by_year'] = px.bar(spend_year_df, x="YEAR", y="SPEND", title='Spend by Year')

    # spend by month
    spend_month_df = pd.DataFrame({
    'PURCHASE_MONTH': [month for month in range(1, 13)],
    'SPEND': [
                all_three_combined_df.loc[all_three_combined_df['PURCHASE_MONTH'] == month, 'SPEND'].sum() for month in range(1, 13)
            ]  
    })
    figs['fig_spend_by_month'] = px.line(spend_month_df, x="PURCHASE_MONTH", y="SPEND", title="Spend by Month", markers=True)

    # spend by week
    spend_week_df = pd.DataFrame({
    'WEEK_NUM': [week for week in range(1, 53)],
    'SPEND': [
                all_three_combined_df.loc[all_three_combined_df['WEEK_NUM'] == week, 'SPEND'].sum() for week in range(1, 53)
            ]  
    })
    figs['fig_spend_by_week'] = px.line(spend_week_df, x="WEEK_NUM", y="SPEND", title="Spend by Week", markers=True)

    # spend by region
    spend_region_df = pd.DataFrame({
    'STORE_REGION': list(all_three_combined_df['STORE_R'].unique()),
    'SPEND': [
                all_three_combined_df.loc[all_three_combined_df['STORE_R'] == store_region, 'SPEND'].sum() for store_region in list(all_three_combined_df['STORE_R'].unique())
            ]  
    })
    figs['fig_spend_by_region'] = px.pie(spend_region_df, values='SPEND', names='STORE_REGION', title='Spend by Store Region')


    # spend by martial status
    spend_marital_df = pd.DataFrame({
    'MARITAL': list(all_three_combined_df['MARITAL'].unique()),
    'SPEND': [
                all_three_combined_df.loc[all_three_combined_df['MARITAL'] == marital_status, 'SPEND'].sum() for marital_status in list(all_three_combined_df['MARITAL'].unique())
            ]  
    })
    figs['fig_spend_by_marital'] = px.pie(spend_marital_df, values='SPEND', names='MARITAL', title='Spend by Martial Status')

    # spend by number of children
    spend_children_df = pd.DataFrame({
    'CHILDREN': [children for children in list(all_three_combined_df['CHILDREN'].unique())],
    'SPEND': [
                all_three_combined_df.loc[all_three_combined_df['CHILDREN'] == children, 'SPEND'].sum() for children in list(all_three_combined_df['CHILDREN'].unique())
            ]  
    })
    figs['fig_spend_by_children'] = px.pie(spend_children_df, values='SPEND', names='CHILDREN', title='Spend by Number of Children')

    # spend by household composition
    spend_hshdcomposition_df = pd.DataFrame({
    'HSHD_COMPOSITION': [hshd_composition for hshd_composition in list(all_three_combined_df['HSHD_COMPOSITION'].unique())],
    'SPEND': [
                all_three_combined_df.loc[all_three_combined_df['HSHD_COMPOSITION'] == hshd_composition, 'SPEND'].sum() for hshd_composition in list(all_three_combined_df['HSHD_COMPOSITION'].unique())
            ]  
    })

    figs['fig_spend_by_hshdcomposition'] = px.pie(spend_hshdcomposition_df, values='SPEND', names='HSHD_COMPOSITION', title='Spend by Household Composition')


    # units by region over year
    units_by_region_over_year_df = all_three_combined_df.groupby(['STORE_R', 'YEAR']).sum()
    units_by_region_over_year_df.reset_index(inplace=True)
    figs['fig_units_by_region_over_year'] = px.sunburst(units_by_region_over_year_df, path=['YEAR', 'STORE_R'], values='UNITS', title="Units by Region")

    # spend by region over year
    figs['fig_spend_by_region_over_year'] = px.sunburst(units_by_region_over_year_df, path=['YEAR', 'STORE_R'], values='SPEND', title="Spend By Region")

    # unit / spend department 
    units_by_dept_over_year_df = all_three_combined_df.groupby(['DEPARTMENT', 'YEAR']).sum()
    units_by_dept_over_year_df.reset_index(inplace=True)
    units_by_dept_over_year_df['YEAR'] = units_by_dept_over_year_df['YEAR'].astype(str) 
    figs['fig_units_by_dept_over_year_df'] = px.sunburst(units_by_dept_over_year_df, path=['YEAR', 'DEPARTMENT'], values='UNITS', title="Units By Department")
    figs['fig_spend_by_dept_over_year_df'] = px.sunburst(units_by_dept_over_year_df, path=['YEAR', 'DEPARTMENT'], values='SPEND', title="Spend By Department")

    # units / spend by incomerange over a year
    units_by_incomerange_over_year_df = all_three_combined_df.groupby(['INCOME_RANGE', 'YEAR']).sum()
    units_by_incomerange_over_year_df.reset_index(inplace=True)
    units_by_incomerange_over_year_df['YEAR'] = units_by_incomerange_over_year_df['YEAR'].astype(str)

    # units by agerange over a year
    units_by_agerange_over_year_df = all_three_combined_df.groupby(['AGE_RANGE', 'YEAR']).sum()
    units_by_agerange_over_year_df.reset_index(inplace=True)
    units_by_agerange_over_year_df['YEAR'] = units_by_agerange_over_year_df['YEAR'].astype(str)

    figs['fig_units_by_agerange_over_year'] = px.bar(units_by_agerange_over_year_df,
            x="AGE_RANGE", y="UNITS", color="YEAR", barmode="group", title="Units by Age Range")

    # spend by agerange over a year
    figs['fig_spend_by_agerange_over_year'] = px.bar(units_by_agerange_over_year_df, 
        x="AGE_RANGE", y="SPEND", color="YEAR", barmode="group", title="Spend By Age Range")

    # spend by agerange over a year
    figs['fig_units_by_incomerange_over_year_df'] = px.bar(units_by_incomerange_over_year_df, 
        x="INCOME_RANGE", y="UNITS", color="YEAR", barmode="group", title="Units by Income Level")

    figs['fig_spend_by_incomerange_over_year_df'] = px.bar(units_by_incomerange_over_year_df, 
        x="INCOME_RANGE", y="SPEND", color="YEAR", barmode="group", title="Spend by Income Level")


######################
# Dashboard Layout
######################

def serve_layout():
    get_figures()
    dashboard_layout = html.Div(children=[

        html.H1(children=['CS 5165/6065 Final']),
        html.P(['Mike Schladt', html.Br(),'Nishil Faldu']),
        html.Hr(),
        html.H4("Retail KPI Dashboard"),

        html.P(['The below table combines retail data for transactions, households, and products. Each column is searchable and sortable using the second row as search input.']),
        dash_table.DataTable(
            id='table-sorting-filtering',
            columns=[
                {'name': i, 'id': i, 'deletable': True} for i in sorted(all_three_combined_df.columns)
            ],
            page_current= 0,
            page_size= 15,
            page_action='custom',

            filter_action='custom',
            filter_query='',

            sort_action='custom',
            sort_mode='multi',
            sort_by=[],

            style_table= {
                'overflow' : 'auto'
            }
        ),


        html.P("Use the input below to update tables. Each uploaded file must be a CSV. If the filename contains 'household', 'transaction' or 'product', the corresponding table will be updated"),
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Files')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=False
        ),
        html.Div(id='output-data-upload'),


        html.P([html.B('Answers to project questions at bottom of page')], style={'padding': '10px'}),

        dbc.Row([


            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_units_by_year'])]), width=3),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_year'])]), width=3),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_units_by_region_over_year'])]), width=3),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_region_over_year'])]), width=3)    


        ]),

        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_units_by_month'])]), width=6),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_units_by_week'])]), width=6),
        ]),

        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_month'])]), width=6),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_week'])]), width=6),
        ]),

        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_marital'])]), width=4),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_children'])]), width=4),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_hshdcomposition'])]), width=4)
        ]),

        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_units_by_dept_over_year_df'])]), width=6),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_dept_over_year_df'])]), width=6)    
        ]),
        
        

        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_units_by_agerange_over_year'])]), width=6),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_agerange_over_year'])]), width=6), 
        ]),

        

        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_units_by_incomerange_over_year_df'])]), width=6),
            dbc.Col(html.Div([dcc.Graph(figure=figs['fig_spend_by_incomerange_over_year_df'])]), width=6), 
        ]),


        html.P([
            html.B('Key Questions:'),html.Br(),
            "1. How does customer engagement change over time?",html.Br(),
            html.Li("Do households spend less or more?"),
            html.Li("What categories are growing or shrinking with changing customer engagement?"),
            "2. Which demographic factors (e.g. household size, presence of children, income) appear to affect customer engagement?",html.Br(),
            html.Li("How do they affect customer engagement with certain categories?"),
            html.Li("How might we re-engage customers within the store? Or within a specific category?"),
        ], style={'padding': '10px'}),

        html.Pre('''
            Customer Engagement can be affected by: (Department, Commodity, Spend, Units, Store_region, 
            Week_num, Loyalty_flag, Age_range, Income_range, Homeowner_desc, Household_size, Children)

            Customer Engagement can be shown by: (units bought, money spent)

            Department, -> Spend, Week_num, Year, Purchase_Month, Units
            Commodity, -> Spend, Week_num, Year, Purchase_Month, Units
            Brand Type -> Spend, Units, Age_range, Income_range
            Purchase_month -> Spend, Units, Age_range, Marital, Income_range, 
            Spend -> Year, Month, Week_num, Age_range, Marital, Income_range, Homeowner, HouseHold_size, Children
            Store_R -> Spend, Week_num, Year, Purchase_Month, Units
            '''
        ),


        html.P([ 
            html.B('Provide a short write-up on which Data Science Predictive modeling techniques would be most suitable to reasonably answer the questions below.  Please see The Top 10 Machine Learning Algorithms Links to an external site. for model section. (No more than 200 words) (3 points)'),
            html.Br(),
            html.A(href='https://colab.research.google.com/drive/1AZ-o4M57UeZ0a2DAndHy7FdJ7xHYIvQh?usp=sharing', children='Link to ML Model'),
            html.Pre(
            '''
                The retail dataset given to us has a lot of columns. The dashboard charts and data exploration done by us
                clearly indicated that spending (SPEND) and amount of units (UNITS) sold were the factors that
                measure customer engagement as a customer is usually directly related to spending money and amount
                purchased as well. Hence, we decided to train a model that could predict spending and the amount of
                units sold based on other feature columns like region, week number, year, purchase month, department, and
                other columns.

                A small neural network trained to learn the amount of money spent and the amount of units sold 
                from a retail dataset can provide a valuable insight into the behavior of customers and the 
                effectiveness of an organizations marketing strategies. Such a network can be used to predict 
                customer spending patterns, identify trends in sales, and help optimize pricing.

                The neural network consists of 3 layers, including an input layer, an output layer, 
                and hidden layers. The input layer takes in data from the retail dataset, such as
                time of purchase, household size, region, department and other features. The hidden layers are then used to process the 
                data, extracting features and patterns, and then the output layer is used to make predictions 
                based on the learned patterns.

                The neural network can be trained using various algorithms. For example, a backpropagation 
                algorithm can be used to adjust the weights of the network in order to reduce the error rate 
                of the predictions. We usd Adam optimizer to optimize the weights of the network.

                Once the network is trained, it can be used to make predictions about the amount of money 
                spent and the amount of units sold. This can be used to inform marketing strategies, 
                optimize pricing, and focus on products or services that are in demand. The insights 
                provided by the neural network can also be used to gain a better understanding of 
                customer behavior and the effectiveness of an organizations marketing efforts.
            '''
            )], style={'padding': '10px'}),
           
       
], style={'margin' : 'auto', 'width' : '100%', 'padding' : '10px'})
    return dashboard_layout


# operators for dash table filtering
operators = [['ge ', '>='],
             ['le ', '<='],
             ['lt ', '<'],
             ['gt ', '>'],
             ['ne ', '!='],
             ['eq ', '='],
             ['contains '],
             ['datestartswith ']]

def split_filter_part(filter_part):
    for operator_type in operators:
        for operator in operator_type:
            if operator in filter_part:
                name_part, value_part = filter_part.split(operator, 1)
                name = name_part[name_part.find('{') + 1: name_part.rfind('}')]

                value_part = value_part.strip()
                v0 = value_part[0]
                if (v0 == value_part[-1] and v0 in ("'", '"', '`')):
                    value = value_part[1: -1].replace('\\' + v0, v0)
                else:
                    try:
                        value = float(value_part)
                    except ValueError:
                        value = value_part

                # word operators need spaces after them in the filter string,
                # but we don't want these later
                return name, operator_type[0].strip(), value

    return [None] * 3

# call back to update dash table
@app.callback(
    Output('table-sorting-filtering', 'data'),
    Input('table-sorting-filtering', "page_current"),
    Input('table-sorting-filtering', "page_size"),
    Input('table-sorting-filtering', 'sort_by'),
    Input('table-sorting-filtering', 'filter_query'))
def update_table(page_current, page_size, sort_by, filter):
    filtering_expressions = filter.split(' && ')
    dff = all_three_combined_df
    for filter_part in filtering_expressions:
        col_name, operator, filter_value = split_filter_part(filter_part)
        
        # # let's change the default operator for ints and floats
        # if dff[col_name].dtype in ['int64', 'float64'] and operator == 'contains':
        #     operator = 'eq'

        if operator in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
            # these operators match pandas series operator method names
            dff = dff.loc[getattr(dff[col_name], operator)(filter_value)]
        elif operator == 'contains':
            if dff[col_name].dtype in ['int64', 'float64']:
                dff = dff.loc[getattr(dff[col_name], 'eq')(filter_value)]
            else:
                dff = dff.loc[dff[col_name].str.contains(filter_value, case=False)]
        elif operator == 'datestartswith':
            # this is a simplification of the front-end filtering logic,
            # only works with complete fields in standard format
            dff = dff.loc[dff[col_name].str.startswith(filter_value, case=False)]

    if len(sort_by):
        dff = dff.sort_values(
            [col['column_id'] for col in sort_by],
            ascending=[
                col['direction'] == 'asc'
                for col in sort_by
            ],
            inplace=False
        )

    page = page_current
    size = page_size
    return dff.iloc[page * size: (page + 1) * size].to_dict('records')








####################################
# USER LOGIN AND PAGE ROUTING
####################################








# create user layout
create = html.Div([ 
        html.H1('CS 5165/6065 Final'),
        html.P('Use the form below to create a user account'),
        dcc.Location(id='create_user', refresh=True),
        dcc.Input(id="username"
            , type="text"
            , placeholder="user name"
            , maxLength =15),
        html.Br(),
        dcc.Input(id="password"
            , type="password"
            , placeholder="password"),
        html.Br(),
        dcc.Input(id="email"
            , type="email"
            , placeholder="email"
            , maxLength = 50),
        html.Br(), html.Br(),
        html.Button('Create User', id='submit-val', n_clicks=0),
        html.Br(),html.Br(),
        html.Div(id='container-button-basic')
    ], style={'margin' : 'auto', 'width' : '50%', 'text-align' : 'center'})#end div

# login layout
login =  html.Div([dcc.Location(id='url_login', refresh=True)
            , html.H2('''Please log in to continue:''', id='h1')
            , dcc.Input(placeholder='Enter your username',
                    type='text',
                    id='uname-box'), html.Br()
            , dcc.Input(placeholder='Enter your password',
                    type='password',
                    id='pwd-box'), html.Br(), html.Br()
            , html.Button(children='Login',
                    n_clicks=0,
                    type='submit',
                    id='login-button')
            , html.Div(children='', id='output-state')
        ] , style={'margin' : 'auto', 'width' : '50%', 'text-align' : 'center'}) #end div

success = serve_layout()

data = html.Div([dcc.Dropdown(
                    id='dropdown',
                    options=[{'label': i, 'value': i} for i in ['Day 1', 'Day 2']],
                    value='Day 1')
                , html.Br()
                , html.Div([dcc.Graph(id='graph')])
            ]) #end div

failed = html.Div([ dcc.Location(id='url_login_df', refresh=True)
            , html.Div([html.H2('Log in Failed. Please try again.')
                    , html.Button(id='back-button', children='Go back', n_clicks=0)
                ]) #end div
        ], style={'margin' : 'auto', 'width' : '50%', 'text-align' : 'center'}) #end div
logout = html.Div([dcc.Location(id='logout', refresh=True)
        , html.Br()
        , html.Div(html.H2('You have been logged out - Please login'))
        , html.Br()
        , html.Button(id='back-button', children='Go back', n_clicks=0)
    ], style={'margin' : 'auto', 'width' : '50%', 'text-align' : 'center'})#end div
    
app.layout= html.Div([
            html.Div(id='page-content', className='content')
            ,  dcc.Location(id='url', refresh=False)
        ])
# callback to reload the user object
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))
@app.callback(
    Output('page-content', 'children')
    , [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/':
        return create
    elif pathname == '/login':
        return login
    elif pathname == '/success':
        if current_user.is_authenticated:
            return success
        else:
            return failed
    elif pathname =='/data':
        if current_user.is_authenticated:
            return data
    elif pathname == '/logout':
        if current_user.is_authenticated:
            logout_user()
            return logout
        else:
            return logout
    else:
        return '404'
#set the callback for the dropdown interactivity
@app.callback(
    [Output('graph', 'figure')]
    , [Input('dropdown', 'value')])
def update_graph(dropdown_value):
    if dropdown_value == 'Day 1':
        return [{'layout': {'title': 'Graph of Day 1'}
                , 'data': [{'x': [1, 2, 3, 4]
                    , 'y': [4, 1, 2, 1]}]}]
    else:
        return [{'layout': {'title': 'Graph of Day 2'}
                ,'data': [{'x': [1, 2, 3, 4]
                    , 'y': [2, 3, 2, 4]}]}]
@app.callback(
   [Output('container-button-basic', "children")]
    , [Input('submit-val', 'n_clicks')]
    , [State('username', 'value'), State('password', 'value'), State('email', 'value')])
def insert_users(n_clicks, un, pw, em):
    if un is not None and pw is not None and em is not None:
        hashed_password = generate_password_hash(pw, method='sha256')
        ins = Users_tbl.insert().values(username=un,  password=hashed_password, email=em,)
        conn = engine.connect()
        conn.execute(ins)
        conn.close()
        return [login]
    else:
        return [html.Div([html.P('Already have a user account?'), dcc.Link('Click here to Log In', href='/login')])]
@app.callback(
    Output('url_login', 'pathname')
    , [Input('login-button', 'n_clicks')]
    , [State('uname-box', 'value'), State('pwd-box', 'value')])
def successful(n_clicks, input1, input2):
    user = Users.query.filter_by(username=input1).first()
    if user:
        if check_password_hash(user.password, input2):
            login_user(user)
            return '/success'
        else:
            pass
    else:
        pass
@app.callback(
    Output('output-state', 'children')
    , [Input('login-button', 'n_clicks')]
    , [State('uname-box', 'value'), State('pwd-box', 'value')])
def update_output(n_clicks, input1, input2):
    if n_clicks > 0:
        user = Users.query.filter_by(username=input1).first()
        if user:
            if check_password_hash(user.password, input2):
                return ''
            else:
                return 'Incorrect username or password'
        else:
            return 'Incorrect username or password'
    else:
        return ''
@app.callback(
    Output('url_login_success', 'pathname')
    , [Input('back-button', 'n_clicks')])
def logout_dashboard(n_clicks):
    if n_clicks > 0:
        return '/'
@app.callback(
    Output('url_login_df', 'pathname')
    , [Input('back-button', 'n_clicks')])
def logout_dashboard(n_clicks):
    if n_clicks > 0:
        return '/'
# Create callbacks
@app.callback(
    Output('url_logout', 'pathname')
    , [Input('back-button', 'n_clicks')])
def logout_dashboard(n_clicks):
    if n_clicks > 0:
        return '/'

###############
# Upload data callback
###############

def parse_contents(contents, filename, date):
    global transactions_df
    global households_df
    global products_df
    global all_three_combined_df

    content_type, content_string = contents.split(',')


    filename = filename.lower()

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            upload_df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            upload_df = pd.read_excel(io.BytesIO(decoded))
    
        if 'transaction' in filename:
            transactions_df = pd.concat([transactions_df, upload_df], axis=0).drop_duplicates()
            all_three_combined_df = None
            return serve_layout()
        elif 'household' in filename:
            households_df = pd.concat([households_df, upload_df], axis=0).drop_duplicates()
            all_three_combined_df = None
            return serve_layout()
        elif 'product' in filename:
            products_df = pd.concat([products_df, upload_df], axis=0).drop_duplicates()
            all_three_combined_df = None
            return serve_layout()
        else:
            return serve_layout()

    except Exception as e:
        print(e)
        return html.Div([
            f'There was an error processing {filename}.'
        ])

@app.callback(Output('page-content', 'children'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'),
              State('upload-data', 'last_modified'))
def upload_data(contents, filename, file_date):
    if contents is not None:
        children = parse_contents(contents, filename, file_date)
        return children




if __name__ == '__main__':
    app.run(host='0.0.0.0', port='80', debug=True)