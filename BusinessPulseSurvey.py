# -*- coding: utf-8 -*-
"""
Created on Wed Jul 15 14:51:42 2020

@author: Micha
"""

import pandas as pd
from bokeh.io import show
from bokeh.models import ColumnDataSource, NumeralTickFormatter, HoverTool
from bokeh.plotting import figure
from bokeh.transform import dodge
import math
import datetime

fileloc='C:\\Users\\Micha\\Documents\\GitHub\\EconomicDashboard\\'
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
    NAICS=['all']
    
    measures=[qa[i] for i in qa]
    df['qa']=df.questionID.astype('str')+'-'+df.answerID.astype('str')
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
    p.xaxis.major_label_text_font_size = "12pt"
    p.yaxis.formatter=NumeralTickFormatter(format="0%")
    return p

#Build the data set
def base_dataset(weeks):
    df=pd.DataFrame()
    for i in range(0,weeks):
        print(i)
        dt=datetime.datetime.strptime('2020-08-15', '%Y-%m-%d')+datetime.timedelta(days=i*7)
        start=(dt-datetime.timedelta(days=6)).strftime("%d%b%y")
        end=dt.strftime("%d%b%y")
        msa_data_url=f"https://portal.census.gov/pulse/data/downloads/{10+i}/top_50_msa_{start}_{end}.xls"
        state_data_url=f"https://portal.census.gov/pulse/data/downloads/{10+i}/national_state_sector_{start}_{end}.xls"
        code_url='https://portal.census.gov/pulse/data/downloads/codebook_2020_08_10.xlsx'
        df=df.append(merged_data(code_url,msa_data_url,state_data_url,dt.strftime('%Y-%m-%d')))
    df.NAICS=df.NAICS.str.rstrip(' ')
    return df.merge(naics_table(),how='left',on='NAICS')
        
df=base_dataset(3)
    
qa={'20-6':'business is closed',
    '19-7':'expect to close in the next 6 months',
    '6-1':'increased number of employees last week',
    '6-2':'decreased number of employees last week',
    '8-1':'increased hours paid last week',
    '8-2':'decreased hours paid last week',
    '7-1':'rehired employees last week'}

locations=['Sacramento-Roseville-Folsom, CA MSA','CA','National']
p=compare_questions_locations(df[df.date=='2020-08-22'],qa,locations)
show(p)

p=compare_questions_locations(df[df.date=='2020-08-15'],qa,locations)
show(p)
