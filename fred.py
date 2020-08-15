"""
To do:
    Rework normal chart behavior to accept a dataframe as the input, so manipulation can be done before charting
    Select items to monitor on dashboard
"""

import json
import requests as r
import pandas as pd
import itertools
from bokeh.plotting import figure, show, save
from bokeh.models import NumeralTickFormatter,ColumnDataSource,HoverTool, Range1d,Panel,Tabs,Div,LinearAxis
from bokeh.layouts import layout,Spacer
from bokeh.palettes import Category10, Category20
import datetime
import numpy as np
import config

api_key=config.api_key

y2k='2000-01-01'
cy='2020-01-01'
series=['LNU03023653','LNU03025699','ICSA','ICNSA','CAICLAIMS','UNRATE','UNRATENSA']
recession_starts=['2020-02-01','2007-12-01','2001-03-01','1990-07-01','1981-07-01','1980-01-01','1973-11-01','1969-12-01',]
PUA_url='https://oui.doleta.gov/unemploy/docs/weekly_pandemic_claims.xlsx'

pua_data=pd.read_excel(PUA_url)


def master_data(series):
    series_dict={}
    release_dict={}
    for series in series:
        url_series=f'https://api.stlouisfed.org/fred/series?series_id={series}&api_key={api_key}&file_type=json'
        series_dict[series]=json.loads(r.get(url_series).content)['seriess'][0]
        url_series_release=f'https://api.stlouisfed.org/fred/series/release?series_id={series}&api_key={api_key}&file_type=json'
        release_dict[series]=json.loads(r.get(url_series_release).content)['releases'][0]
        print(series)
    df=pd.DataFrame.from_dict(series_dict,orient='index')
    df.drop(columns=['id','realtime_start','realtime_end'],inplace=True)
    df.rename(columns={'title':'series_name'},inplace=True)
    df2=pd.DataFrame.from_dict(release_dict,orient='index')
    df2.drop(columns=['realtime_start','realtime_end'],inplace=True)
    df2.rename(columns={'id':'release_id','name':'release_name'},inplace=True)
    df=df.join(df2, rsuffix='_release')
    return df

def observations(series:str,start:str):
    obs_url=f'https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={api_key}&file_type=json&observation_start={start}'
    dict=json.loads(r.get(obs_url).content).get('observations')
    df=pd.DataFrame.from_dict(dict).astype({'date':'datetime64[ns]','realtime_end':'datetime64[ns]','realtime_start':'datetime64[ns]','value':'float'},errors='ignore')
    df['value'] = pd.to_numeric(df['value'],errors='coerce')
    df.drop(columns=['realtime_start','realtime_end'],inplace=True)
    return df

def transform(df,*args, **kwargs):
    date = kwargs.get('date', '1900-01-01')
    reference_value=df[df.date>=date].value.iloc[0]
    df['difference']=df['value']-reference_value
    df['index']=df['value']/reference_value
    return df

def chart(series:list,start:str,**kwargs):
    mdata=master_data(series)
    transformation=kwargs.get('transformation','value')
    transform_date=kwargs.get('transform_date',start)
    hover_formatter='@'+transformation+'{0,}'
    if transformation=='index':
        hover_formatter='@'+transformation+'{0.0%}'
    if len(series)>10:
        palette=Category20[20]
    else:
        palette=Category10[10]
    colors = itertools.cycle(palette)
    p = figure(title=kwargs.get('title','Chart'), x_axis_type='datetime', plot_width=200, plot_height=400,
           tools="pan,wheel_zoom,reset,save",
            active_scroll=None,
            sizing_mode='stretch_width'
            )
    units=[]
    for series,color in zip(series,colors):
        df=transform(observations(series,start),date=transform_date)
        df['name']=mdata.loc[series].series_name
        df['datestring']=df.date.dt.strftime("%Y-%m-%d")
        source = ColumnDataSource(df)
        p.line(x='date',
               y=transformation,
               source=source,
               legend_label=mdata.loc[series].series_name,
               color=color
            )
        units.append(mdata.loc[series].units)
    hover = HoverTool(tooltips =[
         ('Measure','@name'),
         ('Date','@datestring'),
         ('Value',hover_formatter),
         ])
    p.add_tools(hover)
    p.yaxis.formatter=NumeralTickFormatter(format="0,")
    if transformation=='index':
        ylabel='Percent of '+transform_date+' value'
        p.yaxis.formatter=NumeralTickFormatter(format="0%")
    if transformation=='difference':
        ylabel=repr(set(units)).replace('\'','').replace('{','').replace('}','')+', Difference from '+transform_date
    if transformation=='value':
        ylabel=repr(set(units)).replace('\'','').replace('{','').replace('}','')
    p.yaxis.axis_label=ylabel
    p.legend.location = "bottom_left"
    return p

def datecompare(source,start,end):
    start_date=datetime.datetime.strptime(start, '%Y-%m-%d')
    source['start_date']=start_date
    source['month']=(source['date']-source['start_date'])/np.timedelta64(1,'M')
    source['week']=(source['date']-source['start_date'])/np.timedelta64(1,'W')
    source['recession']=start
    source['recession_year']=start[:4]
    df=source[(source['date']>=start)&(source['date']<end)&(source['date']<=start_date.replace(year = start_date.year + 8))]
    return df

def historical_data(series,recessions):
    mdata=master_data([series])
    data=observations(series,'1900-01-01')
    df=pd.DataFrame()
    for start,end in zip(recession_starts[:recessions],[datetime.datetime.now()]+recession_starts[:recessions-1]):
        df=df.append(datecompare(data,start,end))
    high=df.value.max()
    if high>100:
        formatter='{0,}'
    elif mdata.iloc[0].units=='Percent':
        formatter='{0.0%}'
    else:
        formatter='{0.0}'
    return {'master_data':mdata,'data':df,'formatter':formatter}

def historical_comparison(data):
    mdata=data['master_data']
    frequency=mdata.iloc[0].frequency
    df=data['data']
    formatter=data['formatter']
    p = figure(title=mdata.iloc[0]['series_name']+' in past recessions ('+mdata.iloc[0]['seasonal_adjustment_short']+')',
               plot_width=200, plot_height=400,
               tools="pan,wheel_zoom,reset,save",
               active_scroll=None,
               sizing_mode='stretch_width'
            )
    if formatter=='{0.0%}':
        tickformat="0%"
        conversion=100
    else:
        tickformat="0,"
        conversion=1
    if len(df.columns)-1>10:
        palette=Category20[20]
    else:
        palette=Category10[10]
    colors = itertools.cycle(palette)
    for recession, color in zip(df.recession.unique(),colors):
        source=ColumnDataSource(
            data={'month':df.loc[df.recession == recession].month,
                   'value':df.loc[df.recession == recession].value/conversion,
                   'recession':df.loc[df.recession == recession].recession,
                   'recession_year':df.loc[df.recession == recession].recession_year,
                   'date':df.loc[df.recession == recession].date})
        p.line(x='month',
               y='value',
               source=source,
               legend_label=recession,
               color=color,
               line_width=0.5)
        hover = HoverTool(tooltips =[
         ('Recession','@recession_year'),
         ('Month','@month{0}'),
         ('Date','@date{%F}'),
         ('Value','@value'+formatter),
         ],
            formatters={'@date': 'datetime'})
    p.add_tools(hover)
    p.renderers[0]._property_values['glyph'].line_width=3
    p.yaxis.axis_label=mdata.iloc[0].units
    p.yaxis.formatter=NumeralTickFormatter(format=tickformat)
    p.xaxis.axis_label='Months since Recession Start'
    return p

def adder_chart(base:str,adder,recessions):
    tmp=historical_data(base,recessions)
    tmp2=tmp['data'].merge(adder,how='inner',left_on='date',right_on='Rptdate')
    tmp2['value']=tmp2['value_x']+tmp2['value_y']
    tmp2['recession']='2020-02-01 (incl PUA)'
    tmp2['recession_year']='2020 (incl PUA)'    
    tmp['data']=tmp2.append(tmp['data'])
    p=historical_comparison(tmp)
    p.renderers[1]._property_values['glyph'].line_width=3
    p.renderers[0]._property_values['glyph'].line_color='blue'
    p.renderers[1]._property_values['glyph'].line_color='blue'
    p.renderers[0]._property_values['glyph'].line_dash='dashed'
    return(p)

#Retail sales percent recovery        
retail_sales=['RSHPCS','RSGASS','RSCCAS','RSSGHBMS','RSGMS','RSMSR','RSNSR','RSFSDP','RSMVPD','RSFHFS','RSEAS','RSBMGESD','RSDBS']
p=chart(retail_sales,'2019-01-01',transformation='index',transform_date='2020-02-01')
for i in p.legend[0]._property_values['items']:
    i._property_values['label']['value']=i._property_values['label']['value'][22:]
show(p)

#Compensation and UI change
compensation_and_ui=['W209RC1','W825RC1']
p=chart(compensation_and_ui,cy,transformation='difference',transform_date='2020-02-01')
p.renderers[0].data_source.data['difference']=p.renderers[0].data_source.data['difference']*-1
p.legend[0]._property_values['items'][0]._property_values['label']['value']='Loss in Compensation since Feb 2020'
p.legend[0]._property_values['items'][1]._property_values['label']['value']='Increase in Unemployment Insurance since Feb 2020'
p.legend.location = "top_left"
show(p)

#Personal Income and Spending
personal_income=['PI','PCE','A063RC1']
p=chart(personal_income,cy,transformation='difference',transform_date='2020-02-01')

pi=observations('PI',cy)
transfers=observations('A063RC1',cy)
tmp=pi.join(transfers,rsuffix='transfers')
tmp['value']=tmp['value']-tmp['valuetransfers']
df=transform(tmp,date='2020-02-01')
df['name']='Personal Income excluding transfers'
df['datestring']=df.date.dt.strftime("%Y-%m-%d")


p.line(x='date',y='difference', source=ColumnDataSource(df),
               legend_label='Personal Income excluding transfers',
               color='purple')
show(p)

#Manufacturing, employment, retail sales
series=['RSAFS','IPMAN','PAYEMS']
p=chart(series,'2019-01-01',transformation='index',transform_date='2020-02-01',title='Employment, Manufacturing, and Sales')
show(p)

#Local vs National employment
show(chart(['UNRATENSA','CASACR5URN','IURNSA','CAINSUREDUR'],'2019-01-01',title='National and Local Employment'))


#Employment Charts
paired_series={'UNRATENSA':'CASACR5URN',
                 'IURNSA':'CAINSUREDUR',}
charts=[]
recessions=5
for i in paired_series:
    charts.append([historical_comparison(historical_data(i,recessions)),
                   historical_comparison(historical_data(paired_series[i],recessions))
                   ,Spacer(width=30, height=10, sizing_mode='fixed')])
charts[0][0].y_range=charts[0][1].y_range
charts[1][0].y_range=charts[1][1].y_range
charts.append([
                adder_chart('ICNSA',pua_data.groupby(by='Rptdate').sum()[['PUA IC']].rename(columns={'PUA IC':'value'}),recessions),
                adder_chart('CAICLAIMS',pua_data[pua_data.State=='CA'][['Rptdate','PUA IC']].rename(columns={'PUA IC':'value'}),recessions),
                Spacer(width=30, height=10, sizing_mode='fixed')
                ])
charts.append([historical_comparison(historical_data('LNU03025699',recessions)),
              historical_comparison(historical_data('UEMP15T26',recessions)),
              Spacer(width=30, height=10, sizing_mode='fixed')
    ])
show(layout(charts,sizing_mode='stretch_width'))