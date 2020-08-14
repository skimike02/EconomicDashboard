# -*- coding: utf-8 -*-
"""
Created on Wed Jul 15 14:51:42 2020

@author: Micha
"""

import pandas as pd
from datetime import datetime, timedelta
import requests
import matplotlib.pyplot as plt


week=12

start='2020-05-05'
startdate=datetime.strptime(start, '%Y-%m-%d')

fileloc='C:\\Users\\Micha\\Documents\\GitHub\\EconomicDashboard\\'
filename=fileloc+'employ2_combined.csv'

#filename=fileloc+'Data\\employ2_week10.xlsx'
#week_ending='123'

def import_file(filename,week_ending):
    tmp=pd.read_excel(filename,sheet_name=None,header=[5])
    df=pd.DataFrame()
    for name, frame in tmp.items():
        frame['locality'] = name
        df = df.append(frame, ignore_index=False)
    orignames=df.columns.tolist()
    newnames=df.columns.to_frame(name="titles").titles.str.title().replace('[^A-Za-z0-9]','',regex=True).tolist()
    newnames=[x if (x[:7]=='Unnamed') | (x=='Locality') else 'Employed'+x for x in newnames]
    mapping = {} 
    for origname in orignames: 
        for new_name in newnames: 
            mapping[origname] = new_name 
            newnames.remove(new_name) 
            break  
    df.rename(columns=mapping,inplace=True)
    df.rename(columns={'Unnamed0':'Detail','Unnamed1':'Total','Unnamed8':'Unemployed','Unnamed9':'EmploymentUnknown'},inplace=True)
    df=df[(df.Detail.notnull())&(df.Detail!='* Totals may not sum to 100% as the question allowed for multiple categories to be marked.')]
    df['groupNum']=df.Total.isnull().cumsum()+(df.Detail=='Total').cumsum()
    groups = df[(df.Total.isnull())|(df.Detail=='Total')][['groupNum','Detail']]
    groups['groupName']=groups.Detail.str.title().str.replace('[^A-Za-z0-9]','',regex=True)
    groups.drop(columns='Detail',inplace=True)    
    df=df.merge(groups, left_on='groupNum',right_on='groupNum')
    df.dropna(inplace=True)
    df.replace('-',0,inplace=True)
    df['TotalEmployed']=df.Total-df.Unemployed-df.EmploymentUnknown
    df.drop(columns='groupNum',inplace=True)
    df['week_ending']=week_ending
    df['EmployedPct']=df.TotalEmployed/(df.TotalEmployed+df.Unemployed)
    df.set_index(['groupName'],inplace=True)
    return df  

def save_files(weeks):
    for i in range(weeks):
        url=f"https://www2.census.gov/programs-surveys/demo/tables/hhp/2020/wk{i+1}/employ2_week{i+1}.xlsx"
        save_as=f"employ2_week{i+1}.xlsx"
        print('fetching '+url+'...')
        r=requests.get(url).content
        print('saving')
        open(fileloc+'Data\\'+save_as, 'wb').write(r)

def consolidate(weeks):
    df=pd.DataFrame()
    for i in range(weeks):
        filename=fileloc+'Data\\'+f"employ2_week{i+1}.xlsx"
        print(filename)
        week_ending=startdate+timedelta(days=7*i)
        df=df.append(import_file(filename,week_ending))
    return df
   
def incremental_load(week):
    url=f"https://www2.census.gov/programs-surveys/demo/tables/hhp/2020/wk{week}/employ2_week{week}.xlsx"
    print('fetching '+url+'...')
    r=requests.get(url).content
    week_ending=startdate+timedelta(days=7*week)
    df=pd.read_csv(filename,header=[0],index_col=0)
    df.append(import_file(r,week_ending))
    df.to_csv(filename)
    return df
    
#save_files(12)
#df=consolidate(week)
#df=incremental_load(week)
#df.to_csv(filename)

df=pd.read_csv(filename,header=[0],index_col=0)

df[df.Locality=='CA'].loc['Total'].EmployedPct.plot()
df[df.Locality=='US'].loc['Total'].EmployedPct.plot()

