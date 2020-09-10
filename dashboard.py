# -*- coding: utf-8 -*-
"""
@author: Michael Champ

To do:
    JOLTS
    Personal Income
"""

import pandas as pd
import math
import datetime
from bokeh.plotting import save
from bokeh.models import Panel,Tabs,Div
from bokeh.layouts import layout
from bs4 import BeautifulSoup as Soup
import config
from fred import (bls_compare,chart, bar_chart, historical_comparison, historical_data, adder_chart,
                 category_compare,padding)
from BusinessPulseSurvey import business_pulse,qa_for_loc,qa_by_loc,compare_questions_locations,stacked_by_loc

PUA_url='https://oui.doleta.gov/unemploy/docs/weekly_pandemic_claims.xlsx'
pua_data=pd.read_excel(PUA_url)
fileloc=config.fileloc

y2k='2000-01-01'
cy='2020-01-01'

#%% Overall Trends
def overall_trends():
    series=['RSAFS','IPMAN','PAYEMS','DGORDER']
    national_trends=chart(series,'2019-01-01',transformation='index',transform_date='2020-02-01',title='Employment, Manufacturing, and Sales')
    employment=chart(['PAYEMS'],'2000-01-01',title='Employment')
    employment.legend.location='top_left'
    unemployment=chart(['UNRATENSA','CAURN','CASACR5URN'],'2000-01-01')
    unemployment.legend.location='top_left'
    
    overall_trends=Panel(child=layout([
        [national_trends,employment,padding()],
        [unemployment,padding()]
        ],
        sizing_mode='stretch_width'),
        title='Overall Trends')
    return overall_trends

#%% Weekly Claims
def weekly_claims():
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
    return weekly_claims


#%% ADP Charts
def adp_charts():
    adp_sectors=['NPPSPT','NPPGPT']
    adp_sectors=['NPPMNF','NPPCON','NPPTTU','NPPBUS','NPPFIN']
    adp_sizes=['NPPTS1','NPPTS2','NPPTM','NPPTL1','NPPTL2']
    
    sector_index=chart(adp_sectors,cy,transformation='index',transform_date='2020-02-01',title='National Nonfarm Private Payroll for Select Sectors (ADP)',lstrip=16,rstrip=19)
    sector_index_bar=bar_chart(adp_sectors,cy,title='National Nonfarm Private Payroll for Select Sectors (ADP)',lstrip=16,rstrip=19)
    sector_difference_bar=bar_chart(adp_sectors,cy,transformation='difference',transform_date='2020-02-01',title='Change in Payroll for Select Sectors (ADP)',lstrip=16,rstrip=19)
    size_index=chart(adp_sizes,cy,transformation='index',transform_date='2020-02-01',title='National Nonfarm Private Payroll by Business Size (ADP)',lstrip=16)
    size_index_bar=bar_chart(adp_sizes,cy,title='National Nonfarm Private Payroll by Business Size (ADP)',lstrip=16)
    size_difference_bar=bar_chart(adp_sizes,cy,transformation='difference',transform_date='2020-02-01',title='Change in Payroll by Business Size (ADP)',lstrip=16)
    copyright_note=Div(text="<p>Copyright Automatic Data Processing, Inc. Retrieved from FRED, Federal Reserve Bank of St. Louis</p>")
    
    adp_charts=Panel(child=layout([
        [sector_index,size_index,padding()],
        [sector_index_bar,size_index_bar,padding()],
        [sector_difference_bar,size_difference_bar,padding()],
        [copyright_note]
        ],
        sizing_mode='stretch_width'),
        title='ADP Monthly Data')
    return adp_charts

#%% Jobs Report
def jobs_report():
    recessions=5
    national_jobs=historical_comparison(historical_data('UNRATENSA',recessions))
    state_jobs=historical_comparison(historical_data('CAURN',recessions))
    local_jobs=historical_comparison(historical_data('CASACR5URN',recessions))
    national_jobs.y_range=state_jobs.y_range
    local_jobs.y_range=state_jobs.y_range
    permanent_unemployment=historical_comparison(historical_data('LNU03025699',recessions))
    long_term_unemployment=historical_comparison(historical_data('UEMP15T26',recessions))
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
    jobs_report=Panel(child=layout([
        [national_jobs,state_jobs,local_jobs,padding()],
        [permanent_unemployment,long_term_unemployment,padding()],
        [employment_by_occupation,
         employment_by_industry,
         padding()]
        ],
        sizing_mode='stretch_width'),
        title='Jobs Report')
    return jobs_report

#%% Retail sales percent recovery        
def retail_sales():
    retail_sales=['RSHPCS','RSGASS','RSCCAS','RSSGHBMS','RSGMS','RSMSR','RSNSR','RSFSDP','RSMVPD','RSFHFS','RSEAS','RSBMGESD','RSDBS']
    retail_sales_chart=chart(retail_sales,'2019-01-01',transformation='index',transform_date='2020-02-01',title="Change in retail sales")
    for i in retail_sales_chart.legend[0]._property_values['items']:
        i._property_values['label']['value']=i._property_values['label']['value'][22:]
    
    retail_sales=['RSHPCS','RSGASS','RSCCAS','RSSGHBMS','RSGMS','RSMSR','RSNSR','RSFSDP','RSMVPD','RSFHFS','RSEAS','RSBMGESD','RSDBS']
    compare_industries=category_compare(retail_sales,'Retail Sales',nameoffset=22)
    retail_bar=bar_chart(retail_sales,cy,title='National Nonfarm Private Payroll for Select Sectors (ADP)',lstrip=22,rstrip=0)
    retail_bar_difference=bar_chart(retail_sales,cy,transformation='difference',transform_date='2020-02-01',title='Change in Retail Sales',lstrip=22,rstrip=0)
    
    retail_sales=Panel(child=layout([
            [retail_sales_chart,compare_industries,padding()],
            [retail_bar,retail_bar_difference,padding()]
            ],sizing_mode='stretch_width'),
        title='Retail Sales')
    return retail_sales

#%% Business Pulse
def bus_pul():
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
    closures=stacked_by_loc(bus_pul,dict(list(qa.items())[:2]),locations,title='Business Closures')
    business_pulse_panel=Panel(child=layout([
            [current_status,sacramento_status,padding()],
            [decreased_employment,decreased_hours,padding()],
            [closures,padding()]
            ],sizing_mode='stretch_width'),
        title='Small Business Pulse')
    return business_pulse_panel

#%% Miscellaneous
def miscellaneous():
    business_applications=chart(['BUSAPPWNSAUSYY','BUSAPPWNSACAYY','WBUSAPPWNSACAYY','HBUSAPPWNSACAYY'],'2020-01-01',title="Weekly Business Applications")
    housing_starts=chart(['PERMIT','HOUST','SACR906BPPRIVSA'],'1990-01-01',title='Housing Starts')
    miscellaneous=Panel(child=layout([
        [business_applications,padding()],
        [housing_starts,padding()],
        ],sizing_mode='stretch_width'),
    title='Misc')
    return miscellaneous

#%% About
def about():
    about_html="""
    <p><b>Data Sources and Documentation</b></p>
    <p>Data from <a href="https://fred.stlouisfed.org/docs/api/fred/">FRED® API</a> unless otherwise noted below. This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.</p>
    <p>PUA data pulled from the <a href="https://oui.doleta.gov/unemploy/docs/weekly_pandemic_claims.xlsx">US Department of Labor</a></p>
    <p>Business Pulse Survey Data pulled from <a href="https://www.census.gov/data/experimental-data-products/small-business-pulse-survey.html">US Census Bureau</a></p>
    <p>Household Pulse Survey Data pulled from <a href="https://www.census.gov/programs-surveys/household-pulse-survey/data.html">US Census Bureau</a></p>
    """
    about=Panel(child=Div(text=about_html),title='About')
    return about

page=Tabs(tabs=[
                overall_trends(),
                retail_sales(),
                weekly_claims(),
                adp_charts(),
                jobs_report(),
                bus_pul(),
                miscellaneous(),
                about()
                ])
"""
page=Tabs(tabs=[bus_pul()])
show(page)
"""
save(page,resources=None,filename=fileloc+'Economy.html',title='Economic Data')


header=Soup("""
<div class="header">
  <h1 style: {width: 100%}>A selection of tools</h1> 
  <ul class="navigation"> 
    <li><a href="/index.html">Home</a></li> 
    <li><a href="/CAISOData.html">CAISO Data</a></li> 
    <li><a href="/CCAMap">CCA Service Territory</a></li>
    <li><a href="COVID19.html">COVID-19 Data</a></li>
    <li><a href="Economy.html">EconomicData</a></li>
    <li><a href="https://teslaconnect.michaelchamp.com">TeslaConnect</a></li>
  </ul> 
  <link rel="icon" 
      type="image/png" 
      href="https://michaelchamp.com/assets/logo.png">
 <link rel="stylesheet" href="styles.css">
 </div>
""",features='lxml')

footer=Soup("""<div class="footer"> 
  <p>&copy; 2020
    <script>new Date().getFullYear()>2010&&document.write("-"+new Date().getFullYear());</script>
    , Michael Champ</p>
</div>""",features='lxml')

tracker=Soup("""<div><!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=UA-134772498-1"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'UA-134772498-1');
</script></div>""",features='lxml')
    
#Insert script to add custom html header and footer
htmlfile = open(fileloc+'Economy.html', "r").read()
soup=Soup(htmlfile,"lxml")

soup.find('title').insert_after(header.body.div)
soup.find('body').insert_after(footer.body.div)
soup.find('title').insert_before(tracker.body.div)

f = open(fileloc+'Economy.html', "w")
f.write(str(soup).replace('©','&copy;'))
f.close()

"""

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

"""