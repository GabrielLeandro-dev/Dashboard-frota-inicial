import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Carregar e preparar os dados
try:
    df = pd.read_excel('frota_formatada.xlsx')
    
    # Limpeza dos dados
    df['KM da Última Revisão'] = df['KM da Última Revisão'].str.replace(' km', '').astype(int)
    df['Vencimento da Licença'] = pd.to_datetime(df['Vencimento da Licença'], errors='coerce')
    
    # Adicionar colunas calculadas
    hoje = datetime.now()
    df['Dias para Vencer'] = (df['Vencimento da Licença'] - hoje).dt.days
    df['Status Licença'] = pd.cut(df['Dias para Vencer'],
                                bins=[-float('inf'), 0, 7, 30, float('inf')],
                                labels=['Vencida', 'Crítico (≤7 dias)', 'Atenção (≤30 dias)', 'OK'],
                                right=False)
    df['Marca'] = df['Nome do Carro'].str.split().str[0]

except Exception as e:
    print(f"Erro ao processar dados: {str(e)}")
    raise

# 2. Inicializar o app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# 3. Layout do dashboard
app.layout = dbc.Container([
    # Indicador de carregamento
    dcc.Loading(id="loading", type="default", children=[
        dbc.Row([
            dbc.Col(html.H1("Dashboard de Gestão de Frota", 
                           id='titulo-principal',
                           className="text-center mb-4"), width=12)
        ]),
        
        # Seção de cards
        dbc.Row(id='cards-resumo'),
        
        # Seção de filtros
        dbc.Row(id='filtros'),
        
        # Seção de gráficos
        dbc.Row([
            dbc.Col(dcc.Graph(id='status-chart'), width=6),
            dbc.Col(dcc.Graph(id='gastos-chart'), width=6),
        ], className="mb-4"),
        
        # Tabela de alertas
        dbc.Row([
            dbc.Col([
                html.H4("Veículos com Licenças Próximas do Vencimento"),
                dash_table.DataTable(
                    id='alerts-table',
                    page_size=10,
                    style_table={'overflowX': 'auto'}
                )
            ], width=12)
        ])
    ])
], fluid=True)

# 4. Callbacks para atualização dinâmica
@app.callback(
    [Output('cards-resumo', 'children'),
     Output('status-chart', 'figure'),
     Output('gastos-chart', 'figure'),
     Output('alerts-table', 'data'),
     Output('alerts-table', 'columns')],
    [Input('titulo-principal', 'children')]  # Dispara ao carregar
)
@app.callback(
    [Output('status-chart', 'figure'),
     Output('gastos-chart', 'figure'),
     Output('licencas-chart', 'figure'),
     Output('alerts-table', 'data'),
     Output('full-table', 'data'),
     Output('cards-resumo', 'children')],
    [Input('status-filter', 'value'),
     Input('marca-filter', 'value'),
     Input('obs-filter', 'value'),
     Input('km-slider', 'value')]
)
def update_dashboard(status_filter, marca_filter, obs_filter, km_max):
    # Aplicar filtros
    filtered_df = df.copy()
    
    if status_filter != 'Todos':
        filtered_df = filtered_df[filtered_df['Status Licença'] == status_filter]
    
    if marca_filter != 'Todas':
        filtered_df = filtered_df[filtered_df['Marca'] == marca_filter]
    
    if obs_filter != 'Todas':
        filtered_df = filtered_df[filtered_df['Observações do Veículo'] == obs_filter]
    
    filtered_df = filtered_df[filtered_df['KM da Última Revisão'] <= km_max]
    
    # Gráfico de status
    status_fig = px.pie(
        filtered_df, names='Status Licença', 
        title='Status das Licenças',
        color='Status Licença',
        color_discrete_map={
            'Vencida': 'red',
            'Crítico (≤7 dias)': 'orange',
            'Atenção (≤30 dias)': 'yellow',
            'OK': 'green'
        })
    
    # Gráfico de gastos
    gastos_fig = px.bar(
        filtered_df.groupby('Marca')['Gastos com o Veículo (R$)'].mean().reset_index(),
        x='Marca', y='Gastos com o Veículo (R$)',
        title='Gasto Médio por Marca')
    
    # Gráfico de licenças
    licencas_fig = px.scatter(
        filtered_df, 
        x='Vencimento da Licença', 
        y='Nome do Carro',
        color='Status Licença',
        title='Vencimento de Licenças por Veículo',
        color_discrete_map={
            'Vencida': 'red',
            'Crítico (≤7 dias)': 'orange',
            'Atenção (≤30 dias)': 'yellow',
            'OK': 'green'
        })
    
    # Tabela de alertas
    alerts_df = df[df['Status Licença'].isin(['Vencida', 'Crítico (≤7 dias)', 'Atenção (≤30 dias)'])]
    
    # Cards de resumo
    cards = [
        dbc.Col(dbc.Card([
            dbc.CardHeader("Total de Veículos"),
            dbc.CardBody(html.H4(len(filtered_df), className="card-title"))
        ], color="light"), width=3),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Licenças Vencidas/Críticas"),
            dbc.CardBody(html.H4(
                len(filtered_df[filtered_df['Status Licença'].isin(['Vencida', 'Crítico (≤7 dias)'])]), 
                className="card-title text-danger"))
        ], color="light"), width=3),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Licenças em Atenção"),
            dbc.CardBody(html.H4(
                len(filtered_df[filtered_df['Status Licença'] == 'Atenção (≤30 dias)']), 
                className="card-title text-warning"))
        ], color="light"), width=3),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Gasto Médio (R$)"),
            dbc.CardBody(html.H4(
                f"R$ {filtered_df['Gastos com o Veículo (R$)'].mean():.2f}",
                className="card-title"))
        ], color="light"), width=3)
    ]

    return (status_fig, gastos_fig, licencas_fig, 
            alerts_df.to_dict('records'), 
            filtered_df.to_dict('records'),
            cards)

# 5. Executar o app
if __name__ == '__main__':
    app.run(debug=True, port=8050)