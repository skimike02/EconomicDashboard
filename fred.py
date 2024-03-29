# -*- coding: utf-8 -*-
"""
@author: Michael Champ
To do:
    rewrite functions to pass dataframes
    add integration directly to BLS API
"""

import json
import requests as r
import pandas as pd
import itertools
from bokeh.plotting import figure
from bokeh.models import NumeralTickFormatter,ColumnDataSource,HoverTool
from bokeh.layouts import Spacer
from bokeh.palettes import Category10, Category20
import datetime
import numpy as np
import config
import math
import time
import pickle
import logging

api_key=config.api_key

recession_starts=['2020-02-01','2007-12-01','2001-03-01','1990-07-01','1981-07-01','1980-01-01','1973-11-01','1969-12-01',]

try:
    sticky_master=pickle.load(open('master.p','rb'))
except:
    sticky_master=pd.DataFrame()

try:
    sticky_observations=pickle.load(open('observations.p','rb'))
except:
    sticky_observations=pd.DataFrame(columns=['date','value','series'])
    sticky_observations.set_index('series',inplace=True)

def get_data(url,attempts,delay):
    i=0
    while i<attempts:
        print("attempt "+str(i+1)+f" on url {url}")
        payload=r.get(url)
        code=payload.status_code
        if code!=200:
            logging.info(f" error {code} while retrieving {url}",datetime.datetime.now())
            print(f"Error {code} while retrieving {url}. Retrying in {delay} seconds")
            time.sleep(delay)
            i += 1
        else:
            return payload
    print("attempt unsuccessful")

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
                payload=get_data(url_series,3,60)
                series_dict[series]=json.loads(payload.content)['seriess'][0]
                series_dict[series]['timestamp']=datetime.datetime.now()
                url_series_release=f'https://api.stlouisfed.org/fred/series/release?series_id={series}&api_key={api_key}&file_type=json'
                payload=get_data(url_series_release,3,60)
                try:
                    release_dict[series]=json.loads(payload.content)['releases'][0]
                except:
                    print("no releases in data: "+json.loads(payload.content))
                    logging.warn("no releases in data: "+json.loads(payload.content))
                print("updated master data for "+series)
        else:             
            url_series=f'https://api.stlouisfed.org/fred/series?series_id={series}&api_key={api_key}&file_type=json'
            payload=get_data(url_series,3,60)
            series_dict[series]=json.loads(payload.content)['seriess'][0]
            series_dict[series]['timestamp']=datetime.datetime.now()
            url_series_release=f'https://api.stlouisfed.org/fred/series/release?series_id={series}&api_key={api_key}&file_type=json'
            payload=get_data(url_series_release,3,10)
            try:
                release_dict[series]=json.loads(payload.content)['releases'][0]
                print("loaded master data for "+series)
            except:
                print("error reading json")
                print(json.loads(payload.content))
    sticky_master.drop(labels=series_dict.keys(), inplace=True,errors='ignore')
    if len(series_dict)>=1:
        df=pd.DataFrame.from_dict(series_dict,orient='index')
        df.drop(columns=['id','realtime_start','realtime_end'],inplace=True)
        df.rename(columns={'title':'series_name'},inplace=True)
        df2=pd.DataFrame.from_dict(release_dict,orient='index')
        df2.drop(columns=['realtime_start','realtime_end'],inplace=True)
        df2.rename(columns={'id':'release_id','name':'release_name'},inplace=True)
        df=df.join(df2, rsuffix='_release')
        #sticky_master=sticky_master.append(df)
        sticky_master=pd.concat([sticky_master,df])
    pickle.dump(sticky_master,open('master.p','wb'))
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
            payload=get_data(obs_url,3,60)
      
    else:
        print('getting data for new series '+series)
        obs_url=f'https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={api_key}&file_type=json&observation_start={start}'
        payload=get_data(obs_url,3,60)
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
    sticky_observations=pd.concat([sticky_observations,df])
    pickle.dump(sticky_observations,open('observations.p','wb'))
    return sticky_observations[sticky_observations.date>=start].loc[series]

def bls_api(series:list,start,end):
    global sticky_observations
    sticky_observations.drop(labels=series, inplace=True,errors='ignore')
    headers = {'Content-type': 'application/json'}
    data = json.dumps({"seriesid": series,"startyear":start, "endyear":end})
    print("fetching data from bls api...")
    p = r.post('https://api.bls.gov/publicAPI/v1/timeseries/data/', data=data, headers=headers)
    json_data = json.loads(p.text)
    df=pd.DataFrame()
    for i in json_data['Results']['series']:
        tmp=pd.DataFrame()
        tmp=pd.DataFrame.from_dict(i['data'])
        tmp['series']=i['seriesID']
        tmp['date']=pd.to_datetime(tmp.year+tmp.period.str[-2:]+'01',format='%Y%m%d')
        tmp.set_index('series',inplace=True)
        #df=df.append(tmp)
        df=pd.concat([df,tmp])
        df.drop(columns=['periodName','footnotes','year','period'],inplace=True)
        df['value'] = pd.to_numeric(df['value'],errors='coerce')
    #sticky_observations=sticky_observations.append(df)
    sticky_observations=pd.concat([sticky_observations,df])    
    return df

def transform(df,*args, **kwargs):
    data=df.sort_values(by=['series','date']).copy()
    date = kwargs.get('date', '1900-01-01')
    if len(data[data.date>=date])>0:
        reference_value=data[data.date>=date].value.iloc[0]
        data['difference']=data['value']-reference_value
        data['index']=data['value']/reference_value
    return data

def fred_chart(series:list,start:str,**kwargs):
    mdata=master_data(series)
    offsets=kwargs.get('offsets',[0 for x in range(len(series))])
    transformation=kwargs.get('transformation','value')
    transform_date=kwargs.get('transform_date',start)
    legend_loc=kwargs.get('legend',"bottom_left")
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
            #active_scroll='Auto',
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
               color=color,muted_color=color, muted_alpha=0.2
            )
        units.append(mdata.loc[series].units)
        if ((df.value.max()<100) & (transformation!='index')):
            hover_formatter='@'+transformation+'{0.0}'
    hover = HoverTool(tooltips =[
         ('Measure','@name'),
         ('Date','@datestring'),
         ('Value',hover_formatter),
         ])
    p.legend.click_policy="mute"
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
    p.legend.location = legend_loc
    return p

def chart(df,**kwargs):
    units=kwargs.get('units','number')
    date=kwargs.get('date','date')
    hover_formatter='{0,}'
    yaxis_formatter="0,"
    if units=='percent':
        hover_formatter='{0.0%}'
        yaxis_formatter="0%"
    if (len(df.columns)-1)>10:
        palette=Category20[20]
    else:
        palette=Category10[10]
    colors = itertools.cycle(palette)
    p = figure(title=kwargs.get('title','Chart'), x_axis_type='datetime', plot_width=200, plot_height=400,
           tools="pan,wheel_zoom,reset,save",
            #active_scroll='Auto',
            sizing_mode='stretch_width'
            )
    for series,color in zip(df.columns.drop(date).tolist(),colors):
        df2=df[[date,series]].rename(columns={series:'value'})
        df2['series']=series
        df2['datestring']=df[date].dt.strftime('%m/%d/%Y')
        source = ColumnDataSource(df2)
        p.line(x=date,
               y='value',
               source=source,
               legend_label=series,
               color=color,muted_color=color, muted_alpha=0.2
            )
        if ((df2.value.max()<100)&(units!='percent')):
            hover_formatter='{0.0}'
    hover = HoverTool(tooltips =[
         ('Measure','@series'),
         ('Date','@datestring'),
         ('Value','@{value}'+hover_formatter),
         ])
    p.legend.click_policy="mute"
    p.add_tools(hover)
    p.yaxis.formatter=NumeralTickFormatter(format=yaxis_formatter)
    p.yaxis.axis_label=units
    p.legend.location = "bottom_left"
    return p

def bar_chart(series:list,start:str,**kwargs):
    mdata=master_data(series)
    offsets=kwargs.get('offsets',[0 for x in range(len(series))])
    transformation=kwargs.get('transformation','value')
    transform_date=kwargs.get('transform_date',start)
    date_format=kwargs.get('date_format',"%b-%y")
    legend_loc=kwargs.get('legend',"bottom_left")
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
        df['datestring']=df.date.dt.strftime(date_format)
        df.rename(columns={transformation:name},inplace=True)
        df=df[['datestring',name]].copy()
        chart_data=chart_data.merge(df,how='outer',on='datestring',copy=True)
        units.append(mdata.loc[series_item].units)
    names=chart_data.drop(columns='datestring').columns.tolist()
    chart_data['net']=chart_data.drop(columns='datestring', axis=1).sum(axis=1).rename('sum')
    chart_data.set_index('datestring',inplace=True)
    p = figure(title=kwargs.get('title','Chart'),x_range=chart_data.reset_index().datestring.tolist(),plot_width=200, plot_height=400,
       tools="pan,wheel_zoom,reset,save",
       #active_scroll='Auto',
       sizing_mode='stretch_width',
        )
    positive=p.vbar_stack(names,
            x='datestring', 
            width=0.9,
            color=palette[0:len(names)],
            source=ColumnDataSource(chart_data.clip(lower=0).reset_index()),
            legend_label=names
            )
    negative=p.vbar_stack(names,
            x='datestring', 
            width=0.9,
            color=palette[0:len(names)],
            source=ColumnDataSource(chart_data.clip(upper=0).reset_index()) 
            )
    hover = HoverTool(tooltips ="$name @datestring: @$name{0,}",renderers=positive)
    p.add_tools(hover)
    hover = HoverTool(tooltips ="$name @datestring: @$name{0,}",renderers=negative)
    p.add_tools(hover)
    if kwargs.get('net',False)==True:
        line_r=p.line(x='datestring',
               y='net',
               source=ColumnDataSource(chart_data),
               color='black',
               width=2,
               legend_label='Net'
               )
        hover2 = HoverTool(tooltips ="Net @datestring @net{0,}",renderers=[line_r])
        p.add_tools(hover2)
    p.yaxis.formatter=NumeralTickFormatter(format="0,")
    if transformation=='index':
        ylabel='Percent of '+transform_date+' value'
        p.yaxis.formatter=NumeralTickFormatter(format="0%")
    if transformation=='difference':
        ylabel=repr(set(units)).replace('\'','').replace('{','').replace('}','')+', Difference from '+transform_date
    if transformation=='value':
        ylabel=repr(set(units)).replace('\'','').replace('{','').replace('}','')
    p.yaxis.axis_label=ylabel
    if legend_loc!=False:
        p.legend.location = legend_loc
    else:
        p.legend.items=[]
    return p


def datecompare(source,start,end,**kwargs):
    start_date=datetime.datetime.strptime(start, '%Y-%m-%d')
    source['start_date']=start_date
    source['month']=(source['date']-source['start_date'])/np.timedelta64(1,'M')
    source['week']=(source['date']-source['start_date'])/np.timedelta64(1,'W')
    source['recession']=start
    source['recession_year']=start[:4]
    df=source[(source['date']>=start)&(source['date']<end)&(source['date']<=start_date.replace(year = start_date.year + kwargs.get('years', 8)))]
    df=transform(df)
    return df

def historical_data(series,recessions:int,**kwargs):
    mdata=master_data([series]).loc[series]
    data=observations(series,'1900-01-01')
    df=pd.DataFrame()
    transform=kwargs.get('transform','none')
    for start,end in zip(recession_starts[:recessions],[datetime.datetime.now()]+recession_starts[:recessions-1]):
        #df=df.append(datecompare(data,start,end,years=kwargs.get('years', 8)))
        df=pd.concat([df,datecompare(data,start,end,years=kwargs.get('years', 8))])
    if transform=='difference':
        df.value=df.difference
    if transform=='index':
        df.value=df['index']*100
        mdata.units='Percent'
    high=df.value.max()
    if mdata.units=='Percent':
        formatter='{0.0%}'
    elif high>100:
        formatter='{0,}'
    else:
        formatter='{0.0}'
    return {'master_data':mdata,'data':df,'formatter':formatter}

def historical_comparison(data,**kwargs):
    mdata=data['master_data']
    df=data['data']
    formatter=data['formatter']
    p = figure(title=kwargs.get('title',mdata.series_name+' in past recessions ('+mdata.seasonal_adjustment_short+')'),
               plot_width=200, plot_height=400,
               tools="pan,wheel_zoom,reset,save",
               #active_scroll='Auto',
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
               line_width=0.5,
               muted_color=color, muted_alpha=0.2)
        hover = HoverTool(tooltips =[
         ('Recession','@recession_year'),
         ('Month','@month{0}'),
         ('Date','@date{%F}'),
         ('Value','@value'+formatter),
         ],
            formatters={'@date': 'datetime'})
    p.add_tools(hover)
    p.legend.click_policy="mute"
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
    #tmp['data']=tmp2.append(tmp['data'])
    tmp['data']=pd.concat([tmp2,tmp['data']])
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
    source=ColumnDataSource(data=dict(
        titles=categories,
        bar=bar_field,
        scatter=scatter_field
        ))
    p = figure(x_range=sort_field, plot_height=700, title=title,
               toolbar_location='right', tools="save")
    p.vbar(x='titles', top='bar', width=0.9, legend_label='since Feb',source=source)
    data_through=datetime.datetime.strptime(masterdata.observation_end.max(), '%Y-%m-%d').strftime('%b-%Y')
    p.scatter(x='titles', y='scatter', color='red', legend_label=data_through,source=source)
    hover = HoverTool(tooltips =[
        ('Recession','@titles'),
        ('Since February','@bar{0.0%}'),
        (data_through,'@scatter{0.0%}'),
        ],
        formatters={'@date': 'datetime'})
    p.add_tools(hover)
    p.xaxis.major_label_orientation=math.pi/2.2
    p.yaxis.formatter=NumeralTickFormatter(format=tickformat)
    p.legend.location = "top_left"
    return(p)

def bls_compare(series,categories,title,**kwargs):
    metric=kwargs.get('metric', 'pct')
    df=bls_api(series,2020,2021)
    pct_change, change, month_change, month_pct_change=[],[],[],[]
    for item in series:
        data=transform(observations(item,'2020-02-01'),date='2020-02-01')
        change.append(data.tail(1).iloc[0]['difference'])
        pct_change.append(data.tail(1).iloc[0]['index']-1)
        month_change.append(data.value.tail(1).iloc[0]-data.value.tail(2).head(1).iloc[0])
        month_pct_change.append(data.value.tail(1).iloc[0]/data.value.tail(2).head(1).iloc[0]-1)
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
    p.scatter(x=categories, y=scatter_field, color='red', legend_label=df.date.max().strftime("%b-%y"))
    p.xaxis.major_label_orientation=math.pi/2.2
    p.yaxis.formatter=NumeralTickFormatter(format=tickformat)
    p.legend.location = "top_left"
    return(p)

   


def padding():
    padding=Spacer(width=30, height=10, sizing_mode='fixed')
    return padding

