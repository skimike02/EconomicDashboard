# -*- coding: utf-8 -*-
import plotly.graph_objects as go
import pandas as pd
from bs4 import BeautifulSoup
import requests
import config

fileloc=config.fileloc


#%% Get Data
url='https://www.bls.gov/news.release/cpi.t02.htm'
html=requests.get(url).text
soup = BeautifulSoup(html)
output_file="inflation.html"

#%% Process Data
#Define hierarchy
data=[]
for r in soup.select('table tr'):
   if r.find('p')!=None:
       try:
           lvl = int(r.find('p').get('class')[0][3:])
           name=r.find('p').text
           row=[lvl,name]
           data.append(row)
       except:
           print(f"skipping {r.find('p').text}")
           pass
       
prior_level=-1
curr_hier=['All items']

for i in range(1,len(data)):
    if data[i][0]>prior_level:
        curr_hier.append(data[i][1])
    elif data[i][0]<prior_level:
        curr_hier=curr_hier[:data[i][0]]
        curr_hier.append(data[i][1])
    elif data[i][0]==prior_level:
        curr_hier.pop()
        curr_hier.append(data[i][1])
    prior_level=data[i][0]
    parent=curr_hier[len(curr_hier)-2]
    data[i].append(parent)
    
hier = pd.DataFrame(data)
hier.columns=['lvl','name','parent']
hier.iloc[:, 1]=hier.iloc[:, 1].str.replace(r"\(.*\)","",regex=True)
hier.iloc[:, 2]=hier.iloc[:, 2].str.replace(r"\(.*\)","",regex=True)

#Merge and process
df=pd.read_html(html)[0]
df.iloc[:, 0]=df.iloc[:, 0].str.replace(r"\(.*\)","",regex=True)
df.columns=['_'.join(col) for col in df.columns.values]
df.rename(columns={df.columns[0]: 'name',
                   df.columns[1]: 'importance'},inplace=True)

for i in range (1,7):
    df.iloc[:, i]=pd.to_numeric(df.iloc[:, i],errors='coerce')/100

    
df=df.merge(hier, left_on='name', right_on='name', how='inner')
#address rounding issues with weightings. Iteratively calculate the weight of child nodes, and increase weight if needed.
for i in range (0,df['lvl'].max()):
    child_sums=df.groupby(by='parent').sum()['importance'].reset_index()
    child_sums.rename(columns={'importance':'sum_child_importance','parent':'sum_parent'},inplace=True)
    df=df.merge(child_sums, left_on='name',right_on='sum_parent',how='left')
    df['importance']=df[["importance", "sum_child_importance"]].max(axis=1)
    df.drop(columns=['sum_child_importance','sum_parent'],inplace=True)
    i=i+1

df['curr_mo_annualized']=((1+df.iloc[:, 6])**12)-1

time_period=df.columns[6][-8:]
       
#%% Make treemap
color_range=round(max(abs(df[df['lvl']<5].iloc[:,6].min()),df[df['lvl']<5].iloc[:,6].max()),2)

fig = go.Figure()

fig.add_trace(
    go.Treemap(
    customdata=df[[df.columns.tolist()[2],'curr_mo_annualized']],
    values=df['importance'].to_list(),
    branchvalues ='total',
    labels = df['name'].to_list(),
    parents = df['parent'].to_list(),
    root_color="lightgrey",
    maxdepth=4,
    marker=dict(
        colors=df.iloc[:, 6],
        colorscale='RdBu',
        reversescale=True,
        cmax=color_range,
        cmin=-color_range,
        #cmid=0,
        showscale=True,
        colorbar=dict(
            title="Inflation",
            tickformat='.2p'
            )
        ),
    hovertemplate="""<b>%{label} </b> <br>
                    Inflation: %{color:.2p} <br>
                    Annualized Rate: %{customdata[1]:.2p} <br>
                    Last 12 months:  %{customdata[0]:.2p}% 
                    <extra></extra>
                    """

    ))
fig.update_layout(
    title={
        'text': f"Inflation Drivers for {time_period}",
        'y':.98,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    )

sliders = [dict(
    active=10,
    currentvalue={"prefix": "Frequency: "},
    pad={"t": 50},
    steps=[]
)]

fig.update_layout(
    sliders=sliders
)

fig.write_html(output_file)
(fileloc+output_file)
