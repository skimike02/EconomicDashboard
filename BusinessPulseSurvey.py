# -*- coding: utf-8 -*-
"""
@author: Michael Champ
"""

import pandas as pd
from bokeh.models import ColumnDataSource, NumeralTickFormatter, HoverTool,FactorRange
from bokeh.plotting import figure, show
from bokeh.transform import dodge
from bokeh.palettes import Category10, Category20
import math
import datetime
import config
import itertools
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

fileloc=config.fileloc
filename=fileloc+'smallBusiness.csv'


def naics_table():
    naics=(pd.read_excel('https://www.census.gov/eos/www/naics/2017NAICS/2017_NAICS_Structure.xlsx',skiprows=3,usecols="B:C",header=None,names=['NAICS','name'],dtype={'NAICS': str, 'name': str})).dropna()
    naics['name']=naics.name.str.rstrip(' ').str.rstrip('T')
    clean=naics[~naics.NAICS.str.contains('-')].reindex().reset_index(drop=True)
    multicodes=naics[naics.NAICS.str.contains('-')]
    for NAICS,name in zip(multicodes.NAICS, multicodes.name):
        start=int(NAICS[0:NAICS.find('-')])
        end=int(NAICS[len(NAICS)-NAICS.find('-'):len(NAICS)])
        for i in range(start,end+1):
            df_length = len(clean)
            clean.loc[df_length] = [str(i),name]
    clean.NAICS=clean.NAICS.astype(str)
    return clean

def merged_data(code_url,msa_data_url,state_data_url,date):
    codebook=pd.read_excel(code_url)
    msa_data=pd.read_excel(msa_data_url)
    state_data=pd.read_excel(state_data_url)
    merged_msa=msa_data.merge(codebook,how='left',left_on=['INSTRUMENT_ID','ANSWER_ID'],right_on=['QUESTION_ID','ANSWER_ID'])
    merged_msa.rename(columns={'MSA':'location'},inplace=True)
    merged_msa['NAICS']='-'
    merged_msa.drop(columns='CBSA_CODE',inplace=True)
    merged_state=state_data.merge(codebook,how='left',left_on=['INSTRUMENT_ID','ANSWER_ID'],right_on=['QUESTION_ID','ANSWER_ID'])
    merged_state.rename(columns={'ST':'location','NAICS_SECTOR':'NAICS'},inplace=True)
    merged=merged_msa.append(merged_state)
    merged['value']=merged.ESTIMATE_PERCENTAGE.str.strip('%').astype('float')/100
    merged.rename(columns={'QUESTION':'question',
                           'ANSWER_TEXT':'answer',
                           'QUESTION_ID':'questionID',
                           'ANSWER_ID':'answerID'},inplace=True)
    merged.drop(columns=['INSTRUMENT_ID','ESTIMATE_PERCENTAGE'],inplace=True)
    merged['date']=date
    merged['SE']=merged.SE.astype(str).str.strip('%').astype('float')/100
    merged.location.replace('-','National',inplace=True)
    merged.NAICS.replace('-','all',inplace=True)
    return merged

def compare_questions_locations(df,qa,locations):
    df=df.copy()
    NAICS=['all']
    measures=[qa[i] for i in qa]
    df['location'] = pd.Categorical(df['location'], locations)
    df['qa'] = pd.Categorical(df['qa'], list(qa))
    subset=df[(df.location.isin(locations))&(df.NAICS.isin(NAICS))&(df.qa.isin(list(qa)))]
    tmp=subset.sort_values(by=['qa','location',])[['qa','location','value']].replace(qa)
    tmp.location.replace('Sacramento-Roseville-Folsom, CA MSA','Sacramento MSA',inplace=True)
    locations=[sub.replace('Sacramento-Roseville-Folsom, CA MSA', 'Sacramento MSA') for sub in locations]
    tmp['location'] = pd.Categorical(tmp['location'], locations)
    
    data={'measures':measures}
    for location,i in zip(locations,range(0,len(locations))):
        data.update({location:tmp[tmp.location==locations[i]].value.tolist()})
    
    source = ColumnDataSource(data=data)
    
    p = figure(x_range=measures, plot_height=600, plot_width=800, title="Key Measures by Location: "+df.date.max(),
               toolbar_location='right', tools="save",
               y_range=(0, .25))
    
    colors=["#c9d9d3","#718dbf","#e84d60"]
    tooltips=[]
    for location,color,i in zip(locations,colors,range(0,len(locations))):
        p.vbar(x=dodge('measures', -0.25+i*.25, range=p.x_range), top=location, width=0.2, source=source,
           color=color, legend_label=location)
        tooltips.append((location,'@{'+location+'}{0.0%}'))
    hover = HoverTool(tooltips = tooltips)
    p.add_tools(hover)
    p.x_range.range_padding = 0.1
    p.xgrid.grid_line_color = None
    p.legend.location = "top_left"
    p.legend.orientation = "horizontal"
    p.xaxis.major_label_orientation=math.pi/2.8
    #p.xaxis.major_label_text_font_size = "12pt"
    p.yaxis.formatter=NumeralTickFormatter(format="0%")
    return p

#Build the data set
def business_pulse(weeks):
    df=pd.DataFrame()
    for i in range(0,weeks):
        print(i)
        dt=datetime.datetime.strptime('2020-08-15', '%Y-%m-%d')+datetime.timedelta(days=i*7)
        start=(dt-datetime.timedelta(days=6)).strftime("%d%b%y")
        end=dt.strftime("%d%b%y")
        if i==8:
            end=(dt+datetime.timedelta(days=2)).strftime("%d%b%y")
        if i==9:
            start=(dt-datetime.timedelta(days=4)).strftime("%d%b%y")
        msa_data_url=f"https://portal.census.gov/pulse/data/downloads/{10+i}/top_50_msa_{start}_{end}.xls"
        state_data_url=f"https://portal.census.gov/pulse/data/downloads/{10+i}/national_state_sector_{start}_{end}.xls"
        code_url='https://portal.census.gov/pulse/data/downloads/codebook_2020_08_10.xlsx'
        try:
            df=df.append(merged_data(code_url,msa_data_url,state_data_url,dt.strftime('%Y-%m-%d')))
        except:
            df=df
    df['qa']=df.questionID.astype('str')+'-'+df.answerID.astype('str')
    df.NAICS=df.NAICS.str.rstrip(' ')
    return df.merge(naics_table(),how='left',on='NAICS')
        
def qa_by_loc(df,qa:str,locations:list,**kwargs):
    df=df[(df.qa==qa)&(df.location.isin(locations))&(df.NAICS=='all')]
    p = figure(title=kwargs.get('title','Chart'), x_range=df.date.unique().tolist(), plot_width=200, plot_height=400,
           tools="pan,wheel_zoom,reset,save",
            active_scroll=None,
            sizing_mode='stretch_width'
            )
    if len(locations)>10:
        palette=Category20[20]
    else:
        palette=Category10[10]
    colors = itertools.cycle(palette)
    for location,color in zip(locations,colors):
        source = ColumnDataSource(df[df.location==location])
        p.line(x='date',
               y='value',
               source=source,
               legend_label=location,
               color=color,muted_color=color, muted_alpha=0.2
            )
    hover = HoverTool(tooltips =[
         ('Location','@location'),
         ('Question','@question'),
         ('Answer','@answer'),
         ('Value','@value{0.0%}'),
         ])
    p.legend.click_policy="mute"
    p.add_tools(hover)
    p.yaxis.formatter=NumeralTickFormatter(format="0%")
    p.legend.location = "bottom_left"
    return p

def qa_diff_by_loc(df,qa:str,qa2:str,locations:list,**kwargs):
    df=df[((df.qa==qa)|(df.qa==qa2))&(df.location.isin(locations))&(df.NAICS=='all')]
    piv=df.pivot(index=['location','date'], columns='qa', values='value').reset_index()
    piv['diff']=piv[qa]-piv[qa2]
    p = figure(title=kwargs.get('title','Chart'), x_range=piv.date.unique().tolist(), plot_width=200, plot_height=400,
           tools="pan,wheel_zoom,reset,save",
            active_scroll=None,
            sizing_mode='stretch_width'
            )
    if len(locations)>10:
        palette=Category20[20]
    else:
        palette=Category10[10]
    colors = itertools.cycle(palette)
    for location,color in zip(locations,colors):
        source = ColumnDataSource(piv[piv.location==location])
        p.line(x='date',
               y='diff',
               source=source,
               legend_label=location,
               color=color,muted_color=color, muted_alpha=0.2
            )
    hover = HoverTool(tooltips =[
         ('Location','@location'),
         ('Value','@diff{0.0%}'),
         ])
    p.legend.click_policy="mute"
    p.add_tools(hover)
    p.yaxis.formatter=NumeralTickFormatter(format="0%")
    p.legend.location = "bottom_left"
    return p

def qa_for_loc(df,qa:dict,location:str,**kwargs):
    df=df[(df.qa.isin(qa))&(df.location==location)&(df.NAICS=='all')].copy()
    df['desc']=df['qa'].map(qa)
    p = figure(title=kwargs.get('title','Chart'), x_range=df.date.unique().tolist(), plot_width=200, plot_height=400,
           tools="pan,wheel_zoom,reset,save",
            active_scroll=None,
            sizing_mode='stretch_width'
            )
    if len(qa)>10:
        palette=Category20[20]
    else:
        palette=Category10[10]
    colors = itertools.cycle(palette)
    for qai,color in zip(qa,colors):
        source = ColumnDataSource(df[df.qa==qai])
        p.line(x='date',
               y='value',
               source=source,
               legend_label=qa[qai],
               color=color,muted_color=color, muted_alpha=0.2
            )
    hover = HoverTool(tooltips =[
         ('Description','@desc'),
         ('Question','@question'),
         ('Answer','@answer'),
         ('Value','@value{0.0%}'),
         ])
    p.legend.click_policy="mute"
    p.add_tools(hover)
    p.yaxis.formatter=NumeralTickFormatter(format="0%")
    p.legend.location = "bottom_left"
    return p    

def stacked_by_loc(df,qa:dict,locations:list,**kwargs):
    desc=[qa[i] for i in qa]
    qa_codes=[i for i in qa]
    if len(qa)>10:
        palette=Category20[20]
    else:
        palette=Category10[10]
    dates=df.date.unique().tolist()
    df=df[(df.qa.isin(qa_codes))&(df.location.isin(locations))&(df.NAICS=='all')].copy()
    df['desc']=df['qa'].map(qa)
    df['factor']=list(zip(df.location, df.date))
    pivot=df.pivot(index='factor', columns='desc', values='value')
    factors=[(x,y) for x in locations for y in dates]
    source = ColumnDataSource(pivot)
    p = figure(title=kwargs.get('title','Chart'),
               x_range=FactorRange(*factors),
               plot_width=200, plot_height=400,
               sizing_mode='stretch_width',
               tools="pan,wheel_zoom,reset,save",
               tooltips="$name @$name{0.0%}",)
    p.vbar_stack(desc, x='factor', width=0.9, alpha=0.5, color=palette[:len(qa)], source=source,
                 legend_label=desc)
    p.vbar_stack(desc, x='factor', width=0.9, alpha=0.5, color=palette[:len(qa)], source=source,
             legend_label=desc)
    p.xaxis.major_label_orientation=math.pi/2.2
    p.legend.location = "top_left"
    p.yaxis.formatter=NumeralTickFormatter(format="0%")

    return p

    
    

#BusinessPulse=business_pulse(3)
#p=compare_questions_locations(BusinessPulse[BusinessPulse.date=='2020-08-22'],qa,locations)
