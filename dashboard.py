# -*- coding: utf-8 -*-
"""
@author: Michael Champ

To do:
    mouseovers to category compare
    TSA Data
    Opentable Data
    JOLTS
    Personal Income
"""

import pandas as pd
import math
import datetime
import requests
from bokeh.plotting import save,output_file
from bokeh.models import Panel,Tabs,Div
from bokeh.layouts import layout
import jinja2
import logging
import os

import config
from fred import (bls_compare, chart,fred_chart, bar_chart, historical_comparison, historical_data, adder_chart,
                 category_compare,padding)
from BusinessPulseSurvey import business_pulse,qa_for_loc,qa_by_loc,compare_questions_locations,stacked_by_loc,qa_diff_by_loc

dir_path = os.path.dirname(os.path.abspath(__file__))

if not os.path.exists(config.log_dir):
    os.makedirs(config.log_dir)
if not os.path.exists(config.log_dir+config.log_file):
    with open(config.log_dir+config.log_file,'w+'): pass
logging.basicConfig(filename=config.log_dir+config.log_file, level=logging.INFO)
logging.info('%s Economic Dashboard Started', datetime.datetime.now())

PUA_url='https://oui.doleta.gov/unemploy/docs/weekly_pandemic_claims.xlsx'
pua_data=pd.read_excel(PUA_url)
fileloc=config.fileloc

y2k='2000-01-01'
cy='2020-01-01'
rs='2020-02-01' #Recession start date

#%% Overall Trends
def overall_trends():
    logging.info('%s Overall Trends Started', datetime.datetime.now())
    series=['RSAFS','IPMAN','PAYEMS','DGORDER']
    national_trends=fred_chart(series,'2019-01-01',transformation='index',transform_date=rs,title='Employment, Manufacturing, and Sales')
    employment=fred_chart(['PAYEMS'],'2000-01-01',title='Employment')
    employment.legend.location='top_left'
    unemployment=fred_chart(['UNRATENSA','CAURN','CASACR5URN'],'2000-01-01',title='Unemployment')
    unemployment.legend.location='top_left'
    
    overall_trends=Panel(child=layout([
        [national_trends,employment,padding()],
        [unemployment,padding()]
        ],
        sizing_mode='stretch_width'),
        title='Overall Trends')
    logging.info('%s Overall Trends Completed', datetime.datetime.now())
    return overall_trends

#%% Weekly Claims
def weekly_claims():
    logging.info('%s Weekly Claims Started', datetime.datetime.now())
    recessions=5
    national_initial_claims=adder_chart('ICNSA',pua_data.groupby(by='Rptdate').sum()[['PUA IC']].rename(columns={'PUA IC':'value'}),recessions,years=3)
    ca_initial_claims=adder_chart('CAICLAIMS',pua_data[pua_data.State=='CA'][['Rptdate','PUA IC']].rename(columns={'PUA IC':'value'}),recessions,years=3)
    national_continuing_claims=adder_chart('CCNSA',pua_data.groupby(by='Rptdate').sum(min_count=1)[['PUA CC']].rename(columns={'PUA CC':'value'}),recessions,years=3)
    ca_continuing_claims=adder_chart('CACCLAIMS',pua_data[pua_data.State=='CA'][['Rptdate','PUA CC']].rename(columns={'PUA CC':'value'}),recessions,years=3)
    
    weekly_claims=Panel(child=layout([
        [national_initial_claims,ca_initial_claims,padding()],
        [national_continuing_claims,ca_continuing_claims,padding()]
        ],
        sizing_mode='stretch_width'),
        title="Weekly Claims")
    logging.info('%s Weekly Claims Completed', datetime.datetime.now())
    return weekly_claims

#%% ADP Charts
def adp_charts():
    logging.info('%s ADP Charts Started', datetime.datetime.now())
    adp_sectors=['NPPSPT','NPPGPT']
    adp_sectors=['NPPMNF','NPPCON','NPPTTU','NPPBUS','NPPFIN']
    adp_sizes=['NPPTS1','NPPTS2','NPPTM','NPPTL1','NPPTL2']
    
    sector_index=fred_chart(adp_sectors,cy,transformation='index',transform_date=rs,title='National Nonfarm Private Payroll for Select Sectors (ADP)',lstrip=16,rstrip=19)
    sector_index_bar=bar_chart(adp_sectors,cy,title='National Nonfarm Private Payroll for Select Sectors (ADP)',lstrip=16,rstrip=19)
    sector_difference_bar=bar_chart(adp_sectors,cy,transformation='difference',transform_date=rs,title='Change in Payroll for Select Sectors (ADP)',lstrip=16,rstrip=19)
    size_index=fred_chart(adp_sizes,cy,transformation='index',transform_date=rs,title='National Nonfarm Private Payroll by Business Size (ADP)',lstrip=16)
    size_index_bar=bar_chart(adp_sizes,cy,title='National Nonfarm Private Payroll by Business Size (ADP)',lstrip=16)
    size_difference_bar=bar_chart(adp_sizes,cy,transformation='difference',transform_date=rs,title='Change in Payroll by Business Size (ADP)',lstrip=16)
    copyright_note=Div(text="<p>Copyright Automatic Data Processing, Inc. Retrieved from FRED, Federal Reserve Bank of St. Louis</p>")
    
    adp_charts=Panel(child=layout([
        [sector_index,size_index,padding()],
        [sector_index_bar,size_index_bar,padding()],
        [sector_difference_bar,size_difference_bar,padding()],
        [copyright_note]
        ],
        sizing_mode='stretch_width'),
        title='ADP Monthly Data')
    logging.info('%s ADP Charts Completed', datetime.datetime.now())
    return adp_charts

#%% Jobs Report
def jobs_report():
    logging.info('%s Jobs Report Started', datetime.datetime.now())
    recessions=5
    national_jobs=historical_comparison(historical_data('UNRATENSA',recessions))
    state_jobs=historical_comparison(historical_data('CAURN',recessions))
    local_jobs=historical_comparison(historical_data('CASACR5URN',recessions))
    national_jobs.y_range=state_jobs.y_range
    local_jobs.y_range=state_jobs.y_range
    permanent_unemployment=historical_comparison(historical_data('LNU03025699',recessions))
    mid_term_unemployment=historical_comparison(historical_data('UEMP15T26',recessions))
    mid_term_unemployment.y_range=permanent_unemployment.y_range
    long_term_unemployment=historical_comparison(historical_data('UEMP27OV',recessions))
    long_term_unemployment.y_range=permanent_unemployment.y_range
    occupations=['LNU02032201','LNU02032204','LNU02032205','LNU02032208','LNU02032212']
    employment_by_occupation=category_compare(occupations,'Change in Employment by Occupation',nameoffset=19)
    employment_by_occupation.legend.location='bottom_left'
    industries=['LNU02034560','LNU02034561','LNU02034562','LNU02034563','LNU02034566','LNU02034570','LNU02034571',
               'LNU02034572','LNU02034573','LNU02034574','LNU02034575','LNU02034576','LNU02034579']
    industry_names=['Agriculture, forestry, fishing, and hunting','Mining, quarrying, and oil and gas extraction',
                    'Construction','Manufacturing','Wholesale and Retail Trade','Transportation and Utilities',
                    'Information','Financial Services','Professional and Business Services','Education and health services',
                    'Leisure and hospitality','Other services','Public administration']
    employment_by_industry=bls_compare(industries,industry_names,'Change in Employment by Industry')
    employment_by_industry.legend.location='bottom_right'
    labor_force_categories=['CLF16OV','LNS11000002','LNS11000001']
    labor_force=fred_chart(labor_force_categories,cy,transformation='index',transform_date=rs,title='Labor Force Level')
    industries=['CEU1000000001','CEU2000000001','CEU3000000001','CEU4000000001','CEU5000000001','CEU5500000001','CEU6000000001',
                'CEU6500000001','CEU7000000001','CEU8000000001','CEU9091000001','CEU9092000001','CEU9093000001']
    industry_compare=fred_chart(industries,'2019-01-01',transformation='index',transform_date=rs,title="Change in Employment",lstrip=14)
    industry_bar_difference=bar_chart(industries,cy,transformation='difference',transform_date=rs,title='Change in Employment',lstrip=14,rstrip=0,legend=False,net=True)
    national_change=historical_comparison(historical_data('PAYEMS',recessions,transform='index'),title='Change in Total Employment')
    state_change=historical_comparison(historical_data('CANA',recessions,transform='index'),title='Change in California Employment')
    state_change.y_range=national_change.y_range
    local_change=historical_comparison(historical_data('SACR906NA',recessions,transform='index'),title='Change in Sac Metro Employment')
    local_change.y_range=national_change.y_range
    jobs_report=Panel(child=layout([
        [national_change,state_change,local_change,padding()],
        [national_jobs,state_jobs,local_jobs,padding()],
        [permanent_unemployment,mid_term_unemployment,long_term_unemployment,padding()],
        [employment_by_occupation,employment_by_industry,labor_force,padding()],
        [industry_compare,industry_bar_difference,padding()]
        ],
        sizing_mode='stretch_width'),
        title='Jobs Report')
    logging.info('%s Jobs Report Completed', datetime.datetime.now())
    return jobs_report

#%% Retail sales percent recovery        
def retail_sales():
    logging.info('%s Retail Sales Started', datetime.datetime.now())
    retail_sales=['RSHPCS','RSGASS','RSCCAS','RSSGHBMS','RSGMS','RSMSR','RSNSR','RSFSDP','RSMVPD','RSFHFS','RSEAS','RSBMGESD','RSDBS']
    retail_sales_chart=fred_chart(retail_sales,'2019-01-01',transformation='index',transform_date=rs,title="Change in retail sales")
    for i in retail_sales_chart.legend[0]._property_values['items']:
        i._property_values['label']['value']=i._property_values['label']['value'][22:]
    
    retail_sales=['RSHPCS','RSGASS','RSCCAS','RSSGHBMS','RSGMS','RSMSR','RSNSR','RSFSDP','RSMVPD','RSFHFS','RSEAS','RSBMGESD','RSDBS']
    compare_industries=category_compare(retail_sales,'Retail Sales',nameoffset=22)
    retail_bar=bar_chart(retail_sales,cy,title='Retail Sales by Sector',lstrip=22,rstrip=0,legend=False)
    retail_bar_difference=bar_chart(retail_sales,cy,transformation='difference',transform_date=rs,title='Change in Retail Sales',lstrip=22,rstrip=0,legend=False,net=True)
    retail_sales=Panel(child=layout([
            [retail_sales_chart,compare_industries,padding()],
            [retail_bar,retail_bar_difference,padding()]
            ],sizing_mode='stretch_width'),
        title='Retail Sales')
    logging.info('%s Retail Sales Completed', datetime.datetime.now())
    return retail_sales

#%% Personal Income and Expenses
def personal_income():
    logging.info('%s Personal Income Started', datetime.datetime.now())
    income=['W209RC1','PCTR','PIROA','A048RC1','A041RC1']
    income_change=bar_chart(income,cy,transformation='difference',transform_date=rs,title='Change in Income',net=True,legend='top_left')
    income_change.legend[0].items[3].label['value']='Rental income'
    income_change.legend[0].items[4].label['value']='''Proprietors' income'''
    #contra_income=['A061RC1','W055RC1']
    expenses=['PCEDG','PCEND','PCES','B069RC1','W211RC1']
    expenses_change=bar_chart(expenses,cy,transformation='difference',transform_date=rs,title='Change in Expenses',net=True)
    for i in range(0,3):
        expenses_change.legend[0].items[i].label['value']=expenses_change.legend[0].items[i].label['value'][35:]
    for i in range(3,5):
        expenses_change.legend[0].items[i].label['value']=expenses_change.legend[0].items[i].label['value'][9:].title()
    high_level=['W209RC1','DSPI','A068RC1','PMSAVE']
    high_level_chart=fred_chart(high_level,cy,title='Income, Expenditure, and Saving')
    personal_income_charts=Panel(child=layout([
            [income_change,expenses_change,padding()],
            [high_level_chart,padding()]
            ],sizing_mode='stretch_width'),
        title='Personal Income and Expenses')
    logging.info('%s Personal Income Completed', datetime.datetime.now())
    return personal_income_charts


#%% Business Pulse
def bus_pul():
    logging.info('%s Business Pulse Started', datetime.datetime.now())
    bus_pul=business_pulse(math.floor((datetime.datetime.now()-datetime.datetime.strptime('2020-08-13', '%Y-%m-%d')).days/7))
    qa={'20-6':'Business is closed',
    '19-7':'Expect to close in the next 6 months',
    '6-1':'Increased number of employees last week',
    '6-2':'Decreased number of employees last week',
    '8-1':'Increased hours paid last week',
    '8-2':'Decreased hours paid last week',}
    locations=['Sacramento-Roseville-Folsom, CA MSA','CA','National']
    current_status=compare_questions_locations(bus_pul[bus_pul.date==bus_pul.date.max()],qa,locations)
    sacramento_status=qa_for_loc(bus_pul,qa,locations[0],title='Sacramento Responses')
    decreased_employment=qa_by_loc(bus_pul,'6-2',locations,title='Decreased Employment')
    decreased_hours=qa_by_loc(bus_pul,'8-2',locations,title='Decreased Hours')  
    change_in_employment=qa_diff_by_loc(bus_pul,'6-1','6-2',locations,title="Businesses increasing employment less businesses decreasing employment")
    change_in_hours=qa_diff_by_loc(bus_pul,'8-1','8-2',locations,title="Businesses increasing hours less businesses decreasing hours")
    closures=stacked_by_loc(bus_pul,dict(list(qa.items())[:2]),locations,title='Business Closures')
    business_pulse_panel=Panel(child=layout([
            [current_status,sacramento_status,padding()],
            [change_in_employment,change_in_hours,padding()],
            [decreased_employment,decreased_hours,padding()],
            [closures,padding()]
            ],sizing_mode='stretch_width'),
        title='Small Business Pulse')
    logging.info('%s Business Pulse Completed', datetime.datetime.now())
    return business_pulse_panel

#%% Miscellaneous
def miscellaneous():
    logging.info('%s Misc Started', datetime.datetime.now())
    business_applications=fred_chart(['BUSAPPWNSAUSYY','BUSAPPWNSACAYY','WBUSAPPWNSACAYY','HBUSAPPWNSACAYY'],'2020-01-01',title="Weekly Business Applications",legend="top_left")
    url='https://www.tsa.gov/coronavirus/passenger-throughput'
    tsa=pd.read_html(requests.get(url).text,header=0)[0]
    tsa['Date']=pd.to_datetime(tsa['Date'], format='%m/%d/%Y')
    #tsa['combined']=tsa['2021'].fillna(tsa['2020'])
    years=['2020','2021','2022']
    for year in years:
        tsa[year]=tsa[year]/tsa['2019']
    melted=pd.melt(tsa,id_vars=['Date'],value_vars=['2020','2021','2022'])
    melted['month']=pd.DatetimeIndex(melted.Date).month
    melted['day']=pd.DatetimeIndex(melted.Date).day
    melted['year']=melted.variable
    melted['date']=pd.to_datetime(melted[['year','month','day']])
    melted.sort_values(by='date',inplace=True)
    #tsa['YoY']=tsa['combined']/tsa['2019']
    tsa_chart=chart(melted[['date','value']],date='date',title='TSA Travelers vs 2019 levels',units='percent')
    housing_starts=fred_chart(['PERMIT','HOUST','SACR906BPPRIVSA'],'1990-01-01',title='Housing Starts')
    miscellaneous=Panel(child=layout([
        [business_applications,tsa_chart,padding()],
        [housing_starts,padding()],
        ],sizing_mode='stretch_width'),
    title='Misc')
    logging.info('%s Misc Completed', datetime.datetime.now())
    return miscellaneous

#%% About
def about():
    about_html="""
    <p><b>Data Sources and Documentation</b></p>
    <p>Data from <a href="https://fred.stlouisfed.org/docs/api/fred/">FRED® API</a> unless otherwise noted below. This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.</p>
    <p>PUA data pulled from the <a href="https://oui.doleta.gov/unemploy/docs/weekly_pandemic_claims.xlsx">US Department of Labor</a></p>
    <p>Business Pulse Survey Data pulled from <a href="https://www.census.gov/data/experimental-data-products/small-business-pulse-survey.html">US Census Bureau</a></p>
    <p>TSA Data pulled from <a href="https://www.tsa.gov/coronavirus/passenger-throughput">TSA website</a></p>
    <p><b>Other Resources:</b></p>
    <p><a href="https://tracktherecovery.org/">Track the Recovery</a></p>
    <p><a href="https://markets.jpmorgan.com/research/open/latest/publication/9002054">JP Morgan Credit Card Spending Tracker</a></p>
    """
    #    <p>Household Pulse Survey Data pulled from <a href="https://www.census.gov/programs-surveys/household-pulse-survey/data.html">US Census Bureau</a></p>

    about=Panel(child=Div(text=about_html),title='About')
    return about

page=Tabs(tabs=[
                overall_trends(),
                retail_sales(),
                personal_income(),
                weekly_claims(),
                adp_charts(),
                jobs_report(),
                #bus_pul(),
                miscellaneous(),
                about()
                ])

logging.info("%s saving file to "+fileloc+'Economy.html', datetime.datetime.now())

print("saving file to "+fileloc+'Economy.html')
output_file(fileloc+'Economy.html')
templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = os.path.join(dir_path,"template.html")
with open(TEMPLATE_FILE) as file_:
    template=jinja2.Template(file_.read())
save(page,title='Economic Data',template=template)
logging.info("%s Economic Dashboard Update Complete", datetime.datetime.now())


"""

#Compensation and UI change
compensation_and_ui=['W209RC1','W825RC1']
p=chart(compensation_and_ui,cy,transformation='difference',transform_date=rs)
p.renderers[0].data_source.data['difference']=p.renderers[0].data_source.data['difference']*-1
p.legend[0]._property_values['items'][0]._property_values['label']['value']='Loss in Compensation since Feb 2020'
p.legend[0]._property_values['items'][1]._property_values['label']['value']='Increase in Unemployment Insurance since Feb 2020'
p.legend.location = "top_left"
show(p)

#Personal Income and Spending
personal_income=['PI','PCE','A063RC1']
p=chart(personal_income,cy,transformation='difference',transform_date=rs)

pi=observations('PI',cy)
transfers=observations('A063RC1',cy)
tmp=pi.join(transfers,rsuffix='transfers')
tmp['value']=tmp['value']-tmp['valuetransfers']
df=transform(tmp,date=rs)
df['name']='Personal Income excluding transfers'
df['datestring']=df.date.dt.strftime("%Y-%m-%d")


p.line(x='date',y='difference', source=ColumnDataSource(df),
               legend_label='Personal Income excluding transfers',
               color='purple')
show(p)

"""