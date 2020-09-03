# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 10:25:59 2020
only pull data once. keep master data
@author: Micha
"""

import json
import requests as r
import pandas as pd
import itertools
from bokeh.plotting import figure, show
from bokeh.models import NumeralTickFormatter,ColumnDataSource,HoverTool, Range1d,Panel,Tabs,Div,LinearAxis
from bokeh.layouts import layout,Spacer
from bokeh.palettes import Category10, Category20
import datetime
import numpy as np
import config
import math
import time
import datetime

delay=2


api_key=config.api_key

recession_starts=['2020-02-01','2007-12-01','2001-03-01','1990-07-01','1981-07-01','1980-01-01','1973-11-01','1969-12-01',]

sticky_master=pd.DataFrame()
sticky_observations=pd.DataFrame(columns=['date','value','series'])
sticky_observations.set_index('series',inplace=True)

def master_data(seriess:list):
    global sticky_master
    series_dict={}
    release_dict={}
    for series in seriess:
        if series in sticky_master.index:
            if (datetime.datetime.now()-sticky_master.loc[series].timestamp).days<1:
                print("master data for "+series+" is already current")
                continue
            else:             
                url_series=f'https://api.stlouisfed.org/fred/series?series_id={series}&api_key={api_key}&file_type=json'
                payload=r.get(url_series)
                if payload.status_code==429:
                    time.sleep(60)
                    payload=r.get(url_series)
                if payload.status_code!=200:
                    print("error retrieving "+url_series)
                    print("response: "+payload.content)
                series_dict[series]=json.loads(payload.content)['seriess'][0]
                series_dict[series]['timestamp']=datetime.datetime.now()
                url_series_release=f'https://api.stlouisfed.org/fred/series/release?series_id={series}&api_key={api_key}&file_type=json'
                payload=r.get(url_series_release)
                if payload.status_code==429:
                    time.sleep(60)
                    payload=r.get(url_series)
                if payload.status_code!=200:
                    print("error retrieving "+url_series)
                    print("response: "+payload.content)
                release_dict[series]=json.loads(payload.content)['releases'][0]
                print("updated master data for "+series)
        else:             
            url_series=f'https://api.stlouisfed.org/fred/series?series_id={series}&api_key={api_key}&file_type=json'
            payload=r.get(url_series)
            if payload.status_code==429:
                time.sleep(60)
                payload=r.get(url_series)
            if payload.status_code!=200:
                print("error retrieving"+url_series)
                print("response: "+payload.content)
            series_dict[series]=json.loads(payload.content)['seriess'][0]
            series_dict[series]['timestamp']=datetime.datetime.now()
            url_series_release=f'https://api.stlouisfed.org/fred/series/release?series_id={series}&api_key={api_key}&file_type=json'
            payload=r.get(url_series_release)
            if payload.status_code==429:
                time.sleep(60)
                payload=r.get(url_series)
            if payload.status_code!=200:
                print("error retrieving"+url_series)
                print("response: "+payload.content)
            release_dict[series]=json.loads(payload.content)['releases'][0]
            print("loaded master data for "+series)
    sticky_master.drop(labels=series_dict.keys(), inplace=True,errors='ignore')
    if len(series_dict)>=1:
        df=pd.DataFrame.from_dict(series_dict,orient='index')
        df.drop(columns=['id','realtime_start','realtime_end'],inplace=True)
        df.rename(columns={'title':'series_name'},inplace=True)
        df2=pd.DataFrame.from_dict(release_dict,orient='index')
        df2.drop(columns=['realtime_start','realtime_end'],inplace=True)
        df2.rename(columns={'id':'release_id','name':'release_name'},inplace=True)
        df=df.join(df2, rsuffix='_release')
        sticky_master=sticky_master.append(df)
    return sticky_master

def observations(series:str,start:str,**kwargs):
    mdata=master_data([series])
    dateoffset=kwargs.get('dateoffset', 0)
    global sticky_observations
    if series in sticky_observations.index:
        if ((sticky_observations.loc[series].date.max()==datetime.datetime.strptime(mdata.loc[series].observation_end, '%Y-%m-%d')) &
        (sticky_observations.loc[series].date.min()<=datetime.datetime.strptime(start, '%Y-%m-%d'))):
            print("observations for "+series+" are already current")
            return sticky_observations[sticky_observations.date>=start].loc[series]
        else:
            print('refreshing data for '+series)
            sticky_observations.drop(labels=[series], inplace=True,errors='ignore')
            obs_url=f'https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={api_key}&file_type=json&observation_start={start}'
            try:
                payload=r.get(obs_url)
                status=payload.status_code
                if status==429:
                    time.sleep(60)
                    payload=r.get(obs_url)
            except:
                print("failure to reach website")          
    else:
        print('getting data for new series '+series)
        obs_url=f'https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={api_key}&file_type=json&observation_start={start}'
        try:
            payload=r.get(obs_url)
            status=payload.status_code
            if status==429:
                time.sleep(60)
                payload=r.get(obs_url)
        except:
            print("failure to reach website")
    try:
        dict=json.loads(payload.content).get('observations')
        df=pd.DataFrame.from_dict(dict).astype({'date':'datetime64[ns]','realtime_end':'datetime64[ns]','realtime_start':'datetime64[ns]','value':'float'},errors='ignore')
    except:
        print("Data did not match expected schema. Payload received:")
        print (payload)
    df['value'] = pd.to_numeric(df['value'],errors='coerce')
    df.drop(columns=['realtime_start','realtime_end'],inplace=True)
    df.date=df.date+np.timedelta64(dateoffset,'D')
    df['series']=series
    df.set_index('series',inplace=True)
    sticky_observations=sticky_observations.append(df)
    return sticky_observations[sticky_observations.date>=start].loc[series]

def transform(df,*args, **kwargs):
    date = kwargs.get('date', '1900-01-01')
    reference_value=df[df.date>=date].value.iloc[0]
    df['difference']=df['value']-reference_value
    df['index']=df['value']/reference_value
    return df

def chart(series:list,start:str,**kwargs):
    mdata=master_data(series)
    offsets=kwargs.get('offsets',[0 for x in range(len(series))])
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
    for series,color,offset in zip(series,colors,offsets):
        df=transform(observations(series,start),date=transform_date)
        df['date']=df.date+datetime.timedelta(days=offset)
        df['name']=mdata.loc[series].series_name[kwargs.get('lstrip', 0):len(mdata.loc[series].series_name)-kwargs.get('rstrip', 0)]
        df['datestring']=df.date.dt.strftime("%Y-%m-%d")
        source = ColumnDataSource(df)
        p.line(x='date',
               y=transformation,
               source=source,
               legend_label=mdata.loc[series].series_name[kwargs.get('lstrip', 0):len(mdata.loc[series].series_name)-kwargs.get('rstrip', 0)],
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

def bar_chart(series:list,start:str,**kwargs):
    mdata=master_data(series)
    offsets=kwargs.get('offsets',[0 for x in range(len(series))])
    transformation=kwargs.get('transformation','value')
    transform_date=kwargs.get('transform_date',start)
    if len(series)>10:
        palette=Category20[20]
    else:
        palette=Category10[10]
    units=[]
    chart_data=pd.DataFrame(columns=['datestring'])
    for series_item,offset in zip(series,offsets):
        df=transform(observations(series_item,start),date=transform_date)
        df['date']=df.date+datetime.timedelta(days=offset)
        name=mdata.loc[series_item].series_name[kwargs.get('lstrip', 0):len(mdata.loc[series_item].series_name)-kwargs.get('rstrip', 0)]
        df['datestring']=df.date.dt.strftime("%b-%y")
        df.rename(columns={transformation:name},inplace=True)
        df=df[['datestring',name]].copy()
        chart_data=chart_data.merge(df,how='outer',on='datestring',copy=True)
        units.append(mdata.loc[series_item].units)
    source = ColumnDataSource(chart_data)    
    p = figure(title=kwargs.get('title','Chart'),x_range=chart_data.datestring.tolist(),plot_width=200, plot_height=400,
       tools="pan,wheel_zoom,reset,save,hover",
       tooltips="$name @datestring: @$name{0,}",
       active_scroll=None,
       sizing_mode='stretch_width',
        )
    names=chart_data.drop(columns='datestring').columns.tolist()
    p.vbar_stack(names,
                 x='datestring', 
                 width=0.9,
                 color=palette[0:len(names)],
                 source=source,
                 legend_label=names)

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


def datecompare(source,start,end,**kwargs):
    start_date=datetime.datetime.strptime(start, '%Y-%m-%d')
    source['start_date']=start_date
    source['month']=(source['date']-source['start_date'])/np.timedelta64(1,'M')
    source['week']=(source['date']-source['start_date'])/np.timedelta64(1,'W')
    source['recession']=start
    source['recession_year']=start[:4]
    df=source[(source['date']>=start)&(source['date']<end)&(source['date']<=start_date.replace(year = start_date.year + kwargs.get('years', 8)))]
    return df

def historical_data(series,recessions:int,**kwargs):
    mdata=master_data([series]).loc[series]
    data=observations(series,'1900-01-01')
    df=pd.DataFrame()
    for start,end in zip(recession_starts[:recessions],[datetime.datetime.now()]+recession_starts[:recessions-1]):
        df=df.append(datecompare(data,start,end,years=kwargs.get('years', 8)))
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
    frequency=mdata.frequency
    df=data['data']
    formatter=data['formatter']
    p = figure(title=mdata.series_name+' in past recessions ('+mdata.seasonal_adjustment_short+')',
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
    p.yaxis.axis_label=mdata.units
    p.yaxis.formatter=NumeralTickFormatter(format=tickformat)
    p.xaxis.axis_label='Months since Recession Start'
    return p

def adder_chart(base:str,adder,recessions,**kwargs):
    tmp=historical_data(base,recessions,years=kwargs.get('years', 8))
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

def category_compare(series:list,title:str,**kwargs):
    metric=kwargs.get('metric', 'pct')
    categories, pct_change, change, month_change, month_pct_change=[],[],[],[],[]
    masterdata=master_data(series).loc[series]
    for item in series:
        data=transform(observations(item,'2020-02-01'),date='2020-02-01')
        change.append(data.tail(1).iloc[0]['difference'])
        pct_change.append(data.tail(1).iloc[0]['index']-1)
        month_change.append(data.value.tail(1).iloc[0]-data.value.tail(2).head(1).iloc[0])
        month_pct_change.append(data.value.tail(1).iloc[0]/data.value.tail(2).head(1).iloc[0]-1)
        categories.append(masterdata.loc[item].series_name[kwargs.get('nameoffset', 0):])
    if metric=='pct':
        sort_field = sorted(categories, key=lambda x: pct_change[categories.index(x)])
        bar_field=pct_change
        scatter_field=month_pct_change
        tickformat="0%"
    else:
        sort_field = sorted(categories, key=lambda x: change[categories.index(x)])
        bar_field=change
        scatter_field=month_change
        tickformat="0.0"
    p = figure(x_range=sort_field, plot_height=700, title=title,
               toolbar_location='right', tools="save")
    p.vbar(x=categories, top=bar_field, width=0.9, legend_label='since Feb')
    p.scatter(x=categories, y=scatter_field, color='red', legend_label=masterdata.observation_end.max())
    p.xaxis.major_label_orientation=math.pi/2.2
    p.yaxis.formatter=NumeralTickFormatter(format=tickformat)
    p.legend.location = "top_left"
    return(p)

def padding():
    padding=Spacer(width=30, height=10, sizing_mode='fixed')
    return padding